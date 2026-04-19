import sqlite3

import duckdb
import pytest

from src.utils.database import Database


def test_setup_converts_sqlite_to_duckdb_when_not_exists(tmp_path):
    sqlite_database_dir = tmp_path / "db"
    sqlite_database_dir.mkdir()
    sqlite_path = sqlite_database_dir / "data.sqlite"
    duckdb_path = tmp_path / "data.duckdb"
    description_path = sqlite_database_dir / "database_description"
    description_path.mkdir()
    (description_path / "orders.csv").write_text(
        "original_column_name,column_name,column_description,data_format\n"
        "id,id,order identifier,integer\n"
        "provider,provider,logistics provider,text\n",
        encoding="utf-8",
    )

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, provider TEXT NOT NULL)"
    )
    sqlite_conn.executemany(
        "INSERT INTO orders (provider) VALUES (?)", [("DB Schenker",), ("SPX",)]
    )
    sqlite_conn.commit()
    sqlite_conn.close()

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    conn = database.setup_database("ignored.duckdb", sqlite_database_dir)

    rows = conn.execute("SELECT id, provider FROM orders ORDER BY id").fetchall()
    assert rows == [(1, "DB Schenker"), (2, "SPX")]
    assert duckdb_path.exists()

    database.close_connection()


def test_setup_connects_directly_when_duckdb_exists(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"

    existing_conn = duckdb.connect(database=str(duckdb_path))
    existing_conn.execute("CREATE TABLE orders (id INTEGER, provider TEXT)")
    existing_conn.execute("INSERT INTO orders VALUES (1, 'Existing')")
    existing_conn.close()

    sqlite_database_dir = tmp_path / "db"
    sqlite_database_dir.mkdir()

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    conn = database.setup_database("ignored.duckdb", sqlite_database_dir)

    rows = conn.execute("SELECT id, provider FROM orders").fetchall()
    assert rows == [(1, "Existing")]

    database.close_connection()


def test_setup_raises_when_neither_duckdb_nor_sqlite_exists(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    sqlite_database_dir = tmp_path / "db"
    sqlite_database_dir.mkdir()

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    with pytest.raises((FileNotFoundError, ValueError)):
        database.setup_database("ignored.duckdb", sqlite_database_dir)