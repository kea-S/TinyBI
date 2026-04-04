import sqlite3

from src.utils.database import Database


def test_register_sqlitedb_as_table_converts_sqlite_to_duckdb(tmp_path):
    sqlite_database_dir = tmp_path / "sample_database"
    sqlite_database_dir.mkdir()
    sqlite_path = sqlite_database_dir / "sample.sqlite"
    duckdb_path = tmp_path / "sample.duckdb"
    description_path = sqlite_database_dir / "database_description"
    description_path.mkdir()
    (description_path / "metrics.csv").write_text(
        "original_column_name,column_name,column_description,data_format\n"
        "id,id,metric identifier,integer\n"
        "name,name,metric name,text\n"
        "value,value,metric value,integer\n",
        encoding="utf-8",
    )

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.execute(
        """
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER NOT NULL
        )
        """
    )
    sqlite_conn.executemany(
        "INSERT INTO metrics (name, value) VALUES (?, ?)",
        [("alpha", 10), ("beta", 20)],
    )
    sqlite_conn.commit()
    sqlite_conn.close()

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()
    database.get_connection("ignored.duckdb")
    output_path = database.register_sqlitedb_as_table(sqlite_database_dir)

    rows = database._CONN.execute(
        "SELECT id, name, value FROM metrics ORDER BY id"
    ).fetchall()

    assert output_path == duckdb_path.resolve()
    assert duckdb_path.exists()
    assert rows == [(1, "alpha", 10), (2, "beta", 20)]

    database.close_connection()
