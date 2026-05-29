import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import duckdb
import pytest

from src.utils.database import Database


def _create_sqlite_db(sqlite_database_dir, table_name="orders", rows=None):
    sqlite_database_dir.mkdir(parents=True, exist_ok=True)
    description_path = sqlite_database_dir / "database_description"
    description_path.mkdir(exist_ok=True)
    (description_path / f"{table_name}.csv").write_text(
        "original_column_name,column_name,column_description,data_format\n"
        "id,id,order identifier,integer\n"
        "provider,provider,logistics provider,text\n",
        encoding="utf-8",
    )
    sqlite_path = sqlite_database_dir / "data.sqlite"
    conn = sqlite3.connect(sqlite_path)
    conn.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, provider TEXT NOT NULL)")
    if rows:
        conn.executemany(f"INSERT INTO {table_name} (provider) VALUES (?)", rows)
    else:
        conn.executemany(
            f"INSERT INTO {table_name} (provider) VALUES (?)",
            [("DB Schenker",), ("SPX",)],
        )
    conn.commit()
    conn.close()
    return sqlite_path, description_path


def _create_duckdb_file(duckdb_path, table_name="orders", rows=None):
    existing_conn = duckdb.connect(database=str(duckdb_path))
    existing_conn.execute(f"CREATE TABLE {table_name} (id INTEGER, provider TEXT)")
    if rows:
        for row in rows:
            existing_conn.execute(f"INSERT INTO {table_name} VALUES (?, ?)", row)
    else:
        existing_conn.execute(f"INSERT INTO {table_name} VALUES (1, 'Existing')")
    existing_conn.close()


def test_setup_converts_sqlite_to_duckdb_when_not_exists(tmp_path):
    sqlite_database_dir = tmp_path / "db"
    duckdb_path = tmp_path / "data.duckdb"
    _create_sqlite_db(sqlite_database_dir)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    database.setup_database("ignored.duckdb", sqlite_database_dir)

    df = database.query("SELECT id, provider FROM orders ORDER BY id")
    rows = [tuple(x) for x in df.values]
    assert rows == [(1, "DB Schenker"), (2, "SPX")]
    assert duckdb_path.exists()


def test_setup_connects_directly_when_duckdb_exists(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    sqlite_database_dir = tmp_path / "db"
    sqlite_database_dir.mkdir(parents=True, exist_ok=True)
    _create_duckdb_file(duckdb_path)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    database.setup_database("ignored.duckdb", sqlite_database_dir)

    df = database.query("SELECT id, provider FROM orders")
    rows = [tuple(x) for x in df.values]
    assert rows == [(1, "Existing")]


def test_setup_raises_when_neither_duckdb_nor_sqlite_exists(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    sqlite_database_dir = tmp_path / "db"
    sqlite_database_dir.mkdir(parents=True, exist_ok=True)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()

    with pytest.raises((FileNotFoundError, ValueError)):
        database.setup_database("ignored.duckdb", sqlite_database_dir)


def test_query_opens_fresh_connection_each_time(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    _create_duckdb_file(duckdb_path)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()
    database.setup_database("ignored.duckdb", tmp_path / "db_missing")

    df1 = database.query("SELECT id FROM orders")
    df2 = database.query("SELECT id FROM orders")

    assert len(df1) == 1
    assert len(df2) == 1


def test_query_after_close_still_works(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    _create_duckdb_file(duckdb_path)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()
    database.setup_database("ignored.duckdb", tmp_path / "db_missing")

    database.close_connection()
    df = database.query("SELECT id FROM orders")
    assert len(df) == 1


def test_concurrent_queries_no_race_condition(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    _create_duckdb_file(duckdb_path, rows=[(i, f"provider_{i}") for i in range(1, 11)])

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()
    database.setup_database("ignored.duckdb", tmp_path / "db_missing")

    errors = []
    results = []

    def run_query(i):
        try:
            df = database.query("SELECT COUNT(*) AS cnt FROM orders")
            return ("ok", df["cnt"].iloc[0])
        except Exception as e:
            return ("error", str(e))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_query, i) for i in range(20)]
        for future in as_completed(futures):
            status, value = future.result()
            if status == "error":
                errors.append(value)
            else:
                results.append(value)

    assert errors == [], f"Concurrent queries failed with: {errors}"
    assert all(r == 10 for r in results)


def test_query_without_setup_raises(tmp_path):
    database = Database()
    with pytest.raises(RuntimeError, match="setup_database"):
        database.query("SELECT 1")


def test_multiple_closes_are_harmless(tmp_path):
    duckdb_path = tmp_path / "data.duckdb"
    _create_duckdb_file(duckdb_path)

    database = Database()
    database._get_database_path = lambda _: duckdb_path.resolve()
    database.setup_database("ignored.duckdb", tmp_path / "db_missing")

    database.close_connection()
    database.close_connection()
    database.close_connection()

    df = database.query("SELECT id FROM orders")
    assert len(df) == 1