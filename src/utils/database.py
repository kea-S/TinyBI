import logging
import duckdb
from pathlib import Path
from src.config import DATA_PATH

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self._database: Path | None = None

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

    def _open_connection(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        if self._database is None:
            raise RuntimeError("Call setup_database() before query().")
        conn = duckdb.connect(database=str(self._database), read_only=read_only)
        conn.install_extension("sqlite")
        conn.load_extension("sqlite")
        return conn

    def setup_database(self, db_path: str, sqlite_database_dir: str, read_only: bool = False) -> None:
        """
        Resolve the DuckDB file path, creating it from SQLite if it doesn't exist.

        After this call, ``self._database`` is set. No persistent connection is held;
        ``query()`` opens a fresh connection per call.
        """
        database_path = self._get_database_path(db_path)
        self._database = database_path

        if database_path.exists():
            conn = self._open_connection(read_only=read_only)
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            return

        conn = duckdb.connect(database=str(database_path), read_only=False)
        conn.install_extension("sqlite")
        conn.load_extension("sqlite")
        try:
            self._register_sqlitedb_as_table(conn, sqlite_database_dir)
        finally:
            conn.close()

    def get_connection(self, db_path: str | None = None, read_only: bool = False):
        """Open a new connection. Kept for backward compatibility."""
        if db_path is not None:
            self._database = self._get_database_path(db_path)
        return self._open_connection(read_only=read_only)

    def _register_sqlitedb_as_table(self, conn, sqlite_database_path):
        if self._database is None:
            raise RuntimeError("Call setup_database() before register_sqlitedb_as_table().")

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

            conn.execute(
                f"""
                CREATE OR REPLACE TABLE {quoted_table_name} AS
                SELECT *
                FROM sqlite_scan({sqlite_literal}, {table_literal})
                """
            )

    def register_sqlitedb_as_table(self, sqlite_database_path):
        """Import all tables from SQLite. Kept for backward compatibility."""
        conn = self._open_connection(read_only=False)
        try:
            self._register_sqlitedb_as_table(conn, sqlite_database_path)
        finally:
            conn.close()

    def query(self, sql: str, read_only: bool = True):
        """Execute SQL using a fresh connection and return a pandas DataFrame."""
        conn = self._open_connection(read_only=read_only)
        try:
            return conn.execute(sql).fetchdf()
        finally:
            conn.close()

    def close_connection(self):
        """No-op. Kept for backward compatibility."""
        pass


global_database = Database()


