from src.utils.database import get_connection, register_csv_as_view, query
from src.config import CLEANED_DATASET


def test_query_csv_via_inmemory_connection():
    conn = get_connection()  # shared in-memory connection for the test process

    view_name = register_csv_as_view(CLEANED_DATASET, view_name="test_csv", conn=conn)

    df = query(f"SELECT * FROM {view_name} LIMIT 5", conn=conn)
    # Expect 1..5 rows (adjust if empty file is possible)

    assert 0 < df.shape[0] <= 5
