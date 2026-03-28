import re
from pathlib import Path

import pandas as pd

from src.tools import query_tool as qt
from src.utils.pydantic_models import QuerySchema


def _patch_db(monkeypatch):
    fake_conn = object()
    captured = {"sql": None}
    fake_df = object()

    def fake_get_connection():
        return fake_conn

    def fake_register_csv_as_view(path, view_name, conn):
        assert conn is fake_conn
        return "mock_view"

    def fake_query(sql, conn):
        assert conn is fake_conn
        captured["sql"] = sql
        return fake_df

    monkeypatch.setattr(qt, "get_connection", fake_get_connection)
    monkeypatch.setattr(qt, "register_csv_as_view", fake_register_csv_as_view)
    monkeypatch.setattr(qt, "query", fake_query)

    return captured, fake_df


def test_query_tool_builds_global_cheapest_query(monkeypatch):
    _, fake_df = _patch_db(monkeypatch)

    schema = QuerySchema()

    df, sql = qt.query_tool(schema)

    assert df is fake_df
    assert "SELECT name, price, original_price, on_sale, quantity_g, supermarket" in sql
    assert "FROM mock_view" in sql
    assert "WHERE price IS NOT NULL" in sql
    assert re.search(r"ORDER BY\s+price\s+ASC,\s+name\s+ASC,\s+supermarket\s+ASC", sql) is not None
    assert re.search(r"LIMIT\s+1\b", sql) is not None


def test_query_tool_filters_supermarket_sale_state_and_quantity(monkeypatch):
    _, fake_df = _patch_db(monkeypatch)

    schema = QuerySchema(
        supermarkets=["sheng siong"],
        on_sale_filter="not_on_sale_only",
        quantity_g_op="gt",
        quantity_g_value=1000,
    )

    df, sql = qt.query_tool(schema)

    assert df is fake_df
    assert "supermarket IN ('Sheng Siong')" in sql
    assert "on_sale = FALSE" in sql
    assert "quantity_g IS NOT NULL" in sql
    assert "quantity_g > 1000" in sql


def _write_fixture_csv(path: Path):
    rows = [
        ["Budget Noodles", 1.20, None, False, 800, "FairPrice"],
        ["Promo Noodles", 0.99, 1.50, True, 500, "Sheng Siong"],
        ["Bulk Noodles", 2.20, None, False, 1200, "Sheng Siong"],
        ["Cold Storage Saver", 1.10, None, False, 900, "Cold Storage"],
    ]
    df = pd.DataFrame(
        rows,
        columns=["name", "price", "original_price", "on_sale", "quantity_g", "supermarket"],
    )
    df.to_csv(path, index=False)


def test_query_tool_executes_cheapest_global_query(tmp_path, monkeypatch):
    csv_path = tmp_path / "noodles.csv"
    _write_fixture_csv(csv_path)
    monkeypatch.setattr(qt, "CLEANED_DATASET", str(csv_path))

    schema = QuerySchema()
    df, _ = qt.query_tool(schema)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "Promo Noodles"
    assert float(df.iloc[0]["price"]) == 0.99


def test_query_tool_executes_filtered_sheng_siong_query(tmp_path, monkeypatch):
    csv_path = tmp_path / "noodles.csv"
    _write_fixture_csv(csv_path)
    monkeypatch.setattr(qt, "CLEANED_DATASET", str(csv_path))

    schema = QuerySchema(
        supermarkets=["sheng siong"],
        on_sale_filter="not_on_sale_only",
        quantity_g_op="gt",
        quantity_g_value=1000,
    )
    df, _ = qt.query_tool(schema)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "Bulk Noodles"
    assert df.iloc[0]["supermarket"] == "Sheng Siong"
