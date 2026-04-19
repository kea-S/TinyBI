from pathlib import Path

CLEANED_DATASET = Path(__file__).resolve().parents[1] / "data" / "intermediate" / "llm_test_dataset_20260206-172226_cleaned.csv"


DATA_PATH = Path(__file__).resolve().parents[1] / "data"

APP_DATA_PATH = DATA_PATH / "app_data"

TABLE_DATA_PATH = DATA_PATH / "minidev_raw" / "financial" / "financial.duckdb"
SQLITE_DATA_PATH = DATA_PATH / "minidev_raw" / "financial"
