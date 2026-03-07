from pathlib import Path
from src.utils.database import get_connection, register_csv_as_view, query


def test_query_csv_via_inmemory_connection():
    csv_path = Path(__file__).resolve().parents[2] / "data" / "intermediate" / "llm_test_dataset_20260206-172226_cleaned.csv"
    conn = get_connection()  # shared in-memory connection for the test process
    view_name = register_csv_as_view(csv_path, view_name="test_csv", conn=conn)
    df = query(f"SELECT * FROM {view_name} LIMIT 5", conn=conn)
    # Expect 1..5 rows (adjust if empty file is possible)

    assert 0 < df.shape[0] <= 5
