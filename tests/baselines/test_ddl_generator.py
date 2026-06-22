import json
import tempfile
from pathlib import Path

import pytest

from src.baselines.ddl_generator import generate_ddl
from src.config import APP_DATA_PATH

EXPECTED_TABLES = [
    "account", "card", "client", "disp",
    "district", "loan", "order", "trans",
]


def _write_columns_json(columns: list[dict]) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(columns, f)
        return f.name


def test_empty_input():
    path = _write_columns_json([])
    result = generate_ddl(path)
    Path(path).unlink()
    assert result == ""


def test_single_column_single_table():
    columns = [
        {
            "entry_id": 1,
            "table_name": "account",
            "column_name": "account_id",
            "source_key": "account.account_id",
            "description": "the id of the account.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["account id"],
            "sample_values": ["1", "2", "3"],
            "payload": {"is_groupable": True},
            "references": None,
        }
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert "CREATE TABLE account" in result
    assert "account_id BIGINT" in result
    assert "the id of the account." in result


def test_multiple_columns_single_table():
    columns = [
        {
            "entry_id": 1,
            "table_name": "account",
            "column_name": "account_id",
            "source_key": "account.account_id",
            "description": "the id of the account.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["account id"],
            "sample_values": ["1", "2"],
            "payload": {"is_groupable": True},
            "references": None,
        },
        {
            "entry_id": 2,
            "table_name": "account",
            "column_name": "district_id",
            "source_key": "account.district_id",
            "description": "location of branch.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["location of branch"],
            "sample_values": ["18", "1"],
            "payload": {"is_groupable": True},
            "references": "district.district_id",
        },
        {
            "entry_id": 3,
            "table_name": "account",
            "column_name": "date",
            "source_key": "account.date",
            "description": "the creation date of the account.",
            "data_format": "str",
            "statistical_type": "temporal",
            "categorical_values": {},
            "aliases": [],
            "sample_values": ["1995-03-24", "1993-02-26"],
            "payload": {"is_groupable": False},
            "references": None,
        },
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert result.count("CREATE TABLE") == 1
    assert "account_id BIGINT" in result
    assert "district_id BIGINT" in result
    assert "date VARCHAR" in result


def test_multiple_tables():
    columns = [
        {
            "entry_id": 1,
            "table_name": "account",
            "column_name": "account_id",
            "source_key": "account.account_id",
            "description": "the id of the account.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["account id"],
            "sample_values": [],
            "payload": {"is_groupable": True},
            "references": None,
        },
        {
            "entry_id": 2,
            "table_name": "loan",
            "column_name": "loan_id",
            "source_key": "loan.loan_id",
            "description": "the id number identifying the loan data",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["loan id"],
            "sample_values": [],
            "payload": {"is_groupable": True},
            "references": None,
        },
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert result.count("CREATE TABLE") == 2
    assert "CREATE TABLE account" in result
    assert "CREATE TABLE loan" in result
    assert result.index("CREATE TABLE account") < result.index("CREATE TABLE loan")


def test_type_mapping():
    columns = [
        {"entry_id": 1, "table_name": "t", "column_name": "col_int", "source_key": "t.col_int", "description": "int", "data_format": "int64", "statistical_type": "discrete", "categorical_values": {}, "aliases": [], "sample_values": [], "payload": {"is_groupable": False}, "references": None},
        {"entry_id": 2, "table_name": "t", "column_name": "col_float", "source_key": "t.col_float", "description": "float", "data_format": "float64", "statistical_type": "continuous", "categorical_values": {}, "aliases": [], "sample_values": [], "payload": {"is_groupable": False}, "references": None},
        {"entry_id": 3, "table_name": "t", "column_name": "col_str", "source_key": "t.col_str", "description": "str", "data_format": "str", "statistical_type": "nominal", "categorical_values": {}, "aliases": [], "sample_values": [], "payload": {"is_groupable": True}, "references": None},
        {"entry_id": 4, "table_name": "t", "column_name": "col_str64", "source_key": "t.col_str64", "description": "str64", "data_format": "str64", "statistical_type": "nominal", "categorical_values": {}, "aliases": [], "sample_values": [], "payload": {"is_groupable": True}, "references": None},
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert "col_int BIGINT" in result
    assert "col_float DOUBLE" in result
    assert "col_str VARCHAR" in result
    assert "col_str64 VARCHAR" in result


def test_foreign_key():
    columns = [
        {
            "entry_id": 1,
            "table_name": "account",
            "column_name": "district_id",
            "source_key": "account.district_id",
            "description": "location of branch.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": ["location of branch"],
            "sample_values": [],
            "payload": {"is_groupable": True},
            "references": "district.district_id",
        }
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert "REFERENCES district(district_id)" in result


def test_no_foreign_key_for_null_references():
    columns = [
        {
            "entry_id": 1,
            "table_name": "account",
            "column_name": "account_id",
            "source_key": "account.account_id",
            "description": "the id.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": [],
            "sample_values": [],
            "payload": {"is_groupable": True},
            "references": None,
        }
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert "REFERENCES" not in result


def test_comment_density():
    """Comment contains description, statistical_type, aliases,
    categorical_values, and sample_values."""
    columns = [
        {
            "entry_id": 3,
            "table_name": "account",
            "column_name": "frequency",
            "source_key": "account.frequency",
            "description": "frequency of the account. categorical.",
            "data_format": "str",
            "statistical_type": "nominal",
            "categorical_values": {
                "POPLATEK MESICNE": ["monthly issuance"],
                "POPLATEK TYDNE": ["weekly issuance"],
            },
            "aliases": ["frequency"],
            "sample_values": ["POPLATEK MESICNE", "POPLATEK TYDNE"],
            "payload": {"is_groupable": True},
            "references": None,
        }
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    # Find the comment for the frequency column
    assert "frequency VARCHAR" in result
    comment = result.split("frequency VARCHAR  -- ")[1].split("\n")[0]

    assert "frequency of the account. categorical." in comment
    assert "type: nominal" in comment
    assert "search_synonyms: frequency" in comment
    assert "POPLATEK MESICNE=monthly issuance" in comment
    assert "POPLATEK TYDNE=weekly issuance" in comment
    assert "sample: POPLATEK MESICNE, POPLATEK TYDNE" in comment


def test_comment_omits_empty_fields():
    """Empty aliases, categorical_values, sample_values should not
    appear as empty annotations in the comment."""
    columns = [
        {
            "entry_id": 1,
            "table_name": "t",
            "column_name": "c",
            "source_key": "t.c",
            "description": "just a column.",
            "data_format": "int64",
            "statistical_type": "identifier",
            "categorical_values": {},
            "aliases": [],
            "sample_values": [],
            "payload": {"is_groupable": False},
            "references": None,
        }
    ]
    path = _write_columns_json(columns)
    result = generate_ddl(path)
    Path(path).unlink()

    assert "just a column." in result
    assert "aliases:" not in result
    assert "values:" not in result
    assert "sample:" not in result


@pytest.mark.integration
def test_real_columns_json():
    path = str(Path(APP_DATA_PATH) / "columns.json")
    result = generate_ddl(path)

    assert result, "should produce non-empty output"
    for table in EXPECTED_TABLES:
        assert f"CREATE TABLE {table}" in result, f"missing table {table}"
