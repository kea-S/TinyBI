import duckdb
from pathlib import Path
from src.config import DATA_PATH


class Database:
    def __init__(self):
        self._CONN = None
        self._database = None

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _quote_sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _get_database_path(self, db_path: str):
        relative_path = Path(db_path)
        absolute_path = DATA_PATH / relative_path

        return absolute_path

    def setup_database(self, db_path: str, sqlite_database_dir: str) -> None:
        """
        Connect to a DuckDB file, creating it from SQLite if it doesn't exist.

        If ``db_path`` points to an existing DuckDB file, connects directly.
        Otherwise, finds the SQLite file in ``sqlite_database_dir``,
        converts it to DuckDB via ``register_sqlitedb_as_table``, then connects.
        """
        database_path = self._get_database_path(db_path)

        if database_path.exists():
            self._database = database_path
            self._CONN = duckdb.connect(database=str(database_path))
            self._CONN.install_extension("sqlite")
            self._CONN.load_extension("sqlite")
            return

        self._database = database_path
        self._CONN = duckdb.connect(database=str(database_path))
        self._CONN.install_extension("sqlite")
        self._CONN.load_extension("sqlite")

        self.register_sqlitedb_as_table(sqlite_database_dir)

    def get_connection(self, db_path: str | None = None):
        """Establish a singleton persistent DuckDB connection for this kernel."""
        _CONN = self._CONN

        if _CONN is None:
            if db_path is None:
                raise ValueError("db_path is required when opening a Database connection")
            database_path = self._get_database_path(db_path)
            database_str = str(database_path)
            self._database = database_path
            self._CONN = duckdb.connect(database=database_str)

            self._CONN.install_extension("sqlite")
            self._CONN.load_extension("sqlite")

        return self._CONN

    def register_sqlitedb_as_table(self, sqlite_database_path):
        """
        Import all tables from the SQLite database located in database_parent_dir
        into the current DuckDB database. Expects exactly one *.sqlite file and
        a database_description/ subdirectory in database_parent_dir.
        """
        if self._CONN is None:
            raise RuntimeError(
                "Call get_connection(db_path) before register_sqlitedb_as_table()."
            )

        database_parent_dir = Path(sqlite_database_path).expanduser().resolve()
        database_description_path = database_parent_dir / "database_description"

        if not database_parent_dir.exists():
            raise FileNotFoundError(database_parent_dir)
        if not database_parent_dir.is_dir():
            raise NotADirectoryError(database_parent_dir)

        if not database_description_path.exists():
            raise FileNotFoundError(database_description_path)
        if not database_description_path.is_dir():
            raise NotADirectoryError(database_description_path)

        sqlite_files = sorted(database_parent_dir.glob("*.sqlite"))

        if not sqlite_files:
            raise FileNotFoundError(
                f"No SQLite file found in {database_parent_dir}"
            )
        if len(sqlite_files) > 1:
            raise ValueError(
                f"Expected exactly one SQLite file in {database_parent_dir}, found {len(sqlite_files)}"
            )

        sqlite_file_path = sqlite_files[0]
        sqlite_literal = self._quote_sql_literal(sqlite_file_path.as_posix())
        description_files = sorted(database_description_path.glob("*.csv"))

        if not description_files:
            raise ValueError(
                f"No table description CSVs found in {database_description_path}"
            )

        for description_file in description_files:
            table_name = description_file.stem
            quoted_table_name = self._quote_identifier(table_name)
            table_literal = self._quote_sql_literal(table_name)

            self._CONN.execute(
                f"""
                CREATE OR REPLACE TABLE {quoted_table_name} AS
                SELECT *
                FROM sqlite_scan({sqlite_literal}, {table_literal})
                """
            )

        return self._database

    def query(self, sql):
        """Execute SQL on the shared connection and return a pandas DataFrame (requires pandas)."""
        if self._CONN is None:
            raise RuntimeError("Call setup_database() or get_connection(db_path) before query().")

        return self._CONN.execute(sql).fetchdf()

    def close_connection(self):
        """Close the shared connection (optional)."""
        _CONN = self._CONN

        if _CONN is not None:
            _CONN.close()
            self._CONN = None


global_database = Database()

