import json
from pathlib import Path

import pytest

faiss = pytest.importorskip("faiss")

from src.config import APP_DATA_PATH
from src.utils.rag.vector_index import VectorIndex
from src.utils.pydantic_models import ColumnVectorIndexEntry


@pytest.fixture
def columns_entries():
    columns_path = Path(APP_DATA_PATH) / "columns.json"
    with open(columns_path) as fh:
        return json.load(fh)


def test_district_columns_a4_through_a16_exist_in_columns_json(columns_entries):
    """H3: district.A4 through A16 must be present in columns.json."""
    district_entries = [
        e for e in columns_entries if e.get("table_name") == "district"
    ]

    district_source_keys = {e["source_key"] for e in district_entries}

    expected = {
        "district.district_id",
        "district.A2",
        "district.A3",
        "district.A4",
        "district.A5",
        "district.A6",
        "district.A7",
        "district.A8",
        "district.A9",
        "district.A10",
        "district.A11",
        "district.A12",
        "district.A13",
        "district.A14",
        "district.A15",
        "district.A16",
    }

    missing = expected - district_source_keys
    assert not missing, (
        f"Missing district column entries in columns.json: {sorted(missing)}. "
        f"Found {len(district_entries)} district entries: {sorted(district_source_keys)}"
    )


def test_district_a11_has_correct_metadata(columns_entries):
    """H3: district.A11 (average salary) metadata is correct."""
    a11 = next(
        (e for e in columns_entries if e.get("source_key") == "district.A11"),
        None,
    )
    assert a11 is not None, "district.A11 not found in columns.json"

    assert a11["table_name"] == "district"
    assert a11["column_name"] == "A11"
    assert a11["statistical_type"] == "discrete"
    assert a11["data_format"] == "int64"
    assert "average salary" in (a11.get("description") or "").lower()
    assert "average salary" in [
        a.lower() for a in a11.get("aliases", [])
    ]


def test_district_numeric_columns_are_not_groupable(columns_entries):
    """A4-A16 are numeric columns and should not be groupable."""
    district_entries = [
        e for e in columns_entries if e.get("table_name") == "district"
    ]
    for entry in district_entries:
        col = entry["column_name"]
        if col in {"A4", "A5", "A6", "A7", "A8", "A9", "A10",
                   "A11", "A12", "A13", "A14", "A15", "A16"}:
            assert entry["payload"]["is_groupable"] is False, (
                f"{entry['source_key']} should not be groupable"
            )


def test_total_entry_count_is_54(columns_entries):
    """41 original entries + 13 new district entries = 54 total."""
    assert len(columns_entries) == 54, (
        f"Expected 54 entries, got {len(columns_entries)}"
    )


def test_existing_non_district_entries_unchanged(columns_entries):
    """Existing entries for other tables should not be modified."""
    # spot-check a few known entries
    loan_amount = next(
        e for e in columns_entries
        if e.get("source_key") == "loan.amount"
    )
    assert loan_amount is not None
    assert loan_amount["statistical_type"] == "discrete"
    assert loan_amount["data_format"] == "int64"
    assert loan_amount["table_name"] == "loan"

    trans_type = next(
        e for e in columns_entries
        if e.get("source_key") == "trans.type"
    )
    assert trans_type is not None
    assert trans_type["statistical_type"] == "nominal"
    assert trans_type["categorical_values"] == {
        "PRIJEM": ["credit"],
        "VYDAJ": ["withdrawal"],
        "VYBER": ["issuance"],
    }

    account_frequency = next(
        e for e in columns_entries
        if e.get("source_key") == "account.frequency"
    )
    assert account_frequency is not None
    assert "POPLATEK MESICNE" in account_frequency["categorical_values"]


def test_faiss_index_is_loadable():
    """The rebuilt FAISS index should be loadable and contain entries."""
    app_data = Path(APP_DATA_PATH)
    faiss_path = app_data / "columns.faiss"
    json_path = app_data / "columns.json"

    assert faiss_path.exists(), f"FAISS index not found at {faiss_path}"
    assert json_path.exists(), f"Metadata not found at {json_path}"

    import faiss
    idx = faiss.read_index(str(faiss_path))
    assert idx.ntotal >= 54, (
        f"FAISS index has {idx.ntotal} entries, expected at least 54"
    )


def test_index_list_entries_returns_all_entries():
    """VectorIndex.list_entries should return all 54 entries after loading."""
    index = VectorIndex()
    index.get_connection(APP_DATA_PATH)
    entries = index.list_entries()

    assert len(entries) == 54, (
        f"list_entries returned {len(entries)}, expected 54"
    )

    # verify district entries are loadable as Pydantic models
    district_entries = [e for e in entries if e.table_name == "district"]
    assert len(district_entries) == 16, (
        f"Expected 16 district entries, got {len(district_entries)}"
    )

    district_cols = {e.source_key for e in district_entries}
    assert "district.A11" in district_cols
    assert "district.A4" in district_cols
    assert "district.A16" in district_cols
