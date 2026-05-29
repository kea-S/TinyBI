import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import duckdb
import pytest

from src.utils.database import Database


def _create_sqlite_db(sqlite_dir, table_name="test_table"):
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    description_dir = sqlite_dir / "database_description"
    description_dir.mkdir(exist_ok=True)
    (description_dir / f"{table_name}.csv").write_text(
        "original_column_name,column_name,column_description,data_format\n"
        "id,id,identifier,integer\n"
        "value,value,numeric value,integer\n",
        encoding="utf-8",
    )
    sqlite_path = sqlite_dir / "data.sqlite"
    conn = sqlite3.connect(sqlite_path)
    conn.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, value INTEGER)")
    conn.executemany(f"INSERT INTO {table_name} (value) VALUES (?)", [(i,) for i in range(1, 11)])
    conn.commit()
    conn.close()


def test_concurrent_read_queries(tmp_path):
    sqlite_dir = tmp_path / "sqlite_data"
    _create_sqlite_db(sqlite_dir)

    db = Database()
    db.setup_database(str(tmp_path / "test.duckdb"), str(sqlite_dir))

    errors = []
    results = []

    def run_query(i):
        try:
            df = db.query("SELECT COUNT(*) AS cnt FROM test_table")
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

    db.close_connection()


def test_setup_then_concurrent_queries(tmp_path):
    sqlite_dir = tmp_path / "sqlite_data"
    _create_sqlite_db(sqlite_dir)

    db = Database()
    db.setup_database(str(tmp_path / "test2.duckdb"), str(sqlite_dir))

    errors = []
    results = []

    def run_query(i):
        try:
            df = db.query("SELECT COUNT(*) AS cnt FROM test_table")
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

    assert errors == [], f"Concurrent queries after setup failed with: {errors}"
    assert all(r == 10 for r in results)

    db.close_connection()