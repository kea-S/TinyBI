import pytest
import concurrent.futures
from pathlib import Path
import unittest.mock as mock
from src.utils.database import Database

def run_health(db_path, sqlite_dir):
    """
    Simulates a concurrent process attempting a health check.
    """
    db = Database()
    try:
        # We try to connect in read-only mode (not yet implemented)
        # Note: We mock _get_database_path inside the test context, but 
        # since this runs in a separate process, we need to ensure the logic works.
        # For the sake of this RED test, we expect this call to fail either because
        # 'read_only' is unexpected or because of locking.
        db.setup_database(str(db_path), str(sqlite_dir), read_only=True)
        result = db.query("SELECT 1")
        db.close_connection()
        return True, result.iloc[0, 0]
    except Exception as e:
        return False, str(e)

def test_concurrent_read_only_access(tmp_path):
    # Setup a temporary DuckDB file
    db_name = "concurrency_test.duckdb"
    db_path = tmp_path / db_name
    
    # Setup a mock sqlite dir
    sqlite_dir = tmp_path / "sqlite_data"
    sqlite_dir.mkdir()
    (sqlite_dir / "database_description").mkdir()
    # Create a dummy .sqlite file to satisfy register_sqlitedb_as_table
    (sqlite_dir / "mock.sqlite").touch()
    (sqlite_dir / "database_description" / "dummy.csv").touch()
    
    # 1. Initialize the DB (Read-Write mode)
    db = Database()
    
    # Mock _get_database_path to return our absolute tmp path
    with mock.patch.object(Database, '_get_database_path', return_value=db_path):
        # Mock register_sqlitedb_as_table to avoid sqlite_scan errors with empty mock file
        with mock.patch.object(Database, 'register_sqlitedb_as_table', return_value=None):
            # Initial setup (this creates the file)
            # Note: We pass read_only=False explicitly here. 
            db.setup_database(str(db_path), str(sqlite_dir), read_only=False)
            db.close_connection()
            assert db_path.exists()

        # 2. Spawn 4 concurrent processes trying to read
        # In a real TDD cycle, we'd mock the path inside the subprocess too 
        # or use a different strategy. For now, this is designed to fail.
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_health, db_path, sqlite_dir) 
                for _ in range(4)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        # Verify all succeeded
        for success, val in results:
            assert success is True, f"Concurrent query failed: {val}"
            assert val == 1
