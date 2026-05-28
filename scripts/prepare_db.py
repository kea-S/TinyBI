import logging
import argparse
from src.utils.database import global_database
from src.config import TABLE_DATA_PATH, SQLITE_DATA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def prepare_database(duckdb_path: str, sqlite_path: str):
    """
    Ensures the DuckDB database is fully initialized and healthy
    before starting concurrent benchmark workers.
    """
    logger.info(f"Preparing database at {duckdb_path}...")

    try:
        # 1. Initialize in Read-Write mode (idempotent)
        # This will create the .duckdb file and import tables if missing.
        global_database.setup_database(
            duckdb_path, 
            sqlite_path, 
            read_only=False
        )

        # 2. Agnostic health check
        # SELECT 1 confirms connectivity
        global_database.query("SELECT 1")

        # information_schema.tables confirms table registration
        df_tables = global_database.query("SELECT count(*) FROM information_schema.tables")
        table_count = df_tables.iloc[0, 0]

        logger.info(f"Database preparation successful. Found {table_count} registered tables.")

    except Exception as e:
        logger.error(f"Database preparation failed: {e}")
        exit(1)
    finally:
        global_database.close_connection()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare DuckDB from SQLite source.")
    parser.add_argument("--duckdb", default=str(TABLE_DATA_PATH), help="Path to output DuckDB file.")
    parser.add_argument("--sqlite", default=str(SQLITE_DATA_PATH), help="Directory containing SQLite file.")

    args = parser.parse_args()
    prepare_database(args.duckdb, args.sqlite)


