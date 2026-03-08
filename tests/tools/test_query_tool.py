import re
from datetime import date
import pytest
from src.tools import query_tool as qt
from src.utils.pydantic_models import QuerySchema, DEFAULT_START, DEFAULT_END
from pathlib import Path
import pandas as pd

import src.utils.database as database


def _patch_db_and_resolver(monkeypatch):
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
        assert isinstance(sql, str) and sql.strip()
        captured["sql"] = sql
        return fake_df

    # Minimal resolver output to avoid coupling tests to its internal mapping
    def fake_resolve_locations_postvalidated(_):
        return {
            "buyer_countries": [],
            "seller_countries": [],
            "buyer_regions": [],
            "seller_regions": [],
            "candidates": {},
            "needs_review": False,
        }

    monkeypatch.setattr(qt, "get_connection", fake_get_connection)
    monkeypatch.setattr(qt, "register_csv_as_view", fake_register_csv_as_view)
    monkeypatch.setattr(qt, "query", fake_query)
    monkeypatch.setattr(qt, "resolve_locations_postvalidated", fake_resolve_locations_postvalidated)

    return captured, fake_df


def test_query_tool_returns_df_and_includes_order_by_and_limit(monkeypatch):
    captured, fake_df = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="logistics_provider",
        metric="total_parcel_qty",
        sort_on="metric",
        ordering="desc",
        limit=5,
        persona="Operational",
    )

    out = qt.query_tool(schema)
    assert out is fake_df

    sql = captured["sql"]
    assert "FROM mock_view" in sql
    assert "SELECT" in sql
    assert "logistics_provider" in sql  # subject present in SELECT
    assert "sum(parcel_qty) AS total_parcels" in sql  # metric present

    # WHERE with validity + dates (defaults from model)
    assert "WHERE is_valid_pdt = TRUE" in sql
    assert f"dt BETWEEN '{DEFAULT_START.isoformat()}' AND '{DEFAULT_END.isoformat()}'" in sql

    # GROUP BY subject
    assert re.search(r"GROUP BY\s+logistics_provider", sql) is not None

    # ORDER BY metric alias + direction
    assert re.search(r"ORDER BY\s+total_parcels\s+DESC", sql) is not None

    # LIMIT
    assert re.search(r"LIMIT\s+5\b", sql) is not None


def test_query_tool_orders_by_subject_alias_and_group_by(monkeypatch):
    captured, _ = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="country",
        metric="avg_bwt",
        sort_on="subject",
        ordering="asc",
        limit=10,
        persona="Operational",
    )

    _ = qt.query_tool(schema)
    sql = captured["sql"]

    # SELECT has aliased subject and metric
    assert "buyer_country AS country" in sql
    assert "round(sum(sum_bwt)/sum(parcel_qty), 3) AS avg_bwt" in sql

    # GROUP BY uses the subject sort target (alias for country)
    assert re.search(r"GROUP BY\s+country\b", sql) is not None

    # ORDER BY uses subject alias + ASC
    assert re.search(r"ORDER BY\s+country\s+ASC", sql) is not None

    # LIMIT
    assert re.search(r"LIMIT\s+10\b", sql) is not None


def test_query_tool_extra_filters_providers_only(monkeypatch):
    captured, fake_df = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="logistics_provider",
        metric="total_parcel_qty",
        sort_on="metric",
        ordering="desc",
        persona="Operational",
        logistics_providers=["SPX", "DB Schenker"],
    )

    out = qt.query_tool(schema)
    assert out is fake_df

    sql = captured["sql"]
    assert "AND logistics_provider IN ('SPX', 'DB Schenker')" in sql


def test_query_tool_extra_filters_multi_dimension(monkeypatch):
    captured, fake_df = _patch_db_and_resolver(monkeypatch)

    def resolver_override(_):
        return {
            "buyer_countries": ["MY", "SG"],
            "seller_countries": ["DE"],
            "buyer_regions": ["SEA"],
            "seller_regions": ["EU"],
            "candidates": {},
            "needs_review": False,
        }

    monkeypatch.setattr(qt, "resolve_locations_postvalidated", resolver_override)

    schema = QuerySchema(
        subject="logistics_provider",
        metric="avg_bwt",
        sort_on="subject",
        ordering="asc",
        persona="Operational",
        logistics_providers=["SPX"],  # providers come from schema, others from resolver
    )

    out = qt.query_tool(schema)
    assert out is fake_df

    sql = captured["sql"]
    # Providers
    assert "AND logistics_provider IN ('SPX')" in sql
    # Countries
    assert "AND buyer_country IN ('MY', 'SG')" in sql
    assert "AND seller_country IN ('DE')" in sql
    # Regions
    assert "AND buyer_region IN ('SEA')" in sql
    assert "AND seller_region IN ('EU')" in sql


def test_query_tool_extra_filters_escaping_providers(monkeypatch):
    captured, _ = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="logistics_provider",
        metric="total_parcel_qty",
        sort_on="metric",
        ordering="desc",
        persona="Operational",
        logistics_providers=["O'Reilly Logistics"],
    )

    _ = qt.query_tool(schema)
    sql = captured["sql"]
    assert "AND logistics_provider IN ('O''Reilly Logistics')" in sql


def test_query_tool_no_extra_filters_emits_no_in_blocks(monkeypatch):
    captured, _ = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="logistics_provider",
        metric="total_parcel_qty",
        sort_on="metric",
        ordering="desc",
        persona="Operational",
        # no providers/countries/regions
    )

    _ = qt.query_tool(schema)
    sql = captured["sql"]
    assert "logistics_provider IN (" not in sql
    assert "buyer_country IN (" not in sql
    assert "seller_country IN (" not in sql
    assert "buyer_region IN (" not in sql
    assert "seller_region IN (" not in sql


def test_query_tool_global_subject_fallback_orders_by_metric(monkeypatch):
    captured, _ = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="global",
        metric="avg_bwt",
        sort_on="subject",   # subject not sortable -> fallback to metric
        ordering="asc",
        persona="Operational",
        limit=7,
    )

    _ = qt.query_tool(schema)
    sql = captured["sql"]

    # No GROUP BY for global
    assert "GROUP BY" not in sql

    # ORDER BY falls back to metric alias
    assert re.search(r"ORDER BY\s+avg_bwt\s+ASC", sql) is not None

    # LIMIT honored
    assert re.search(r"LIMIT\s+7\b", sql) is not None


def test_query_tool_time_series_month(monkeypatch):
    captured, _ = _patch_db_and_resolver(monkeypatch)

    schema = QuerySchema(
        subject="time_series",
        time_granularity="month",
        metric="total_parcel_qty",
        sort_on="subject",
        ordering="asc",
        persona="Operational",
        limit=12,
    )

    _ = qt.query_tool(schema)
    sql = captured["sql"]

    # SELECT has time bucket and metric
    assert "month(dt)" in sql
    assert "sum(parcel_qty) AS total_parcels" in sql

    # GROUP BY and ORDER BY use the same time bucket
    assert re.search(r"GROUP BY\s+month\(dt\)", sql) is not None
    assert re.search(r"ORDER BY\s+month\(dt\)\s+ASC", sql) is not None

    # LIMIT honored
    assert re.search(r"LIMIT\s+12\b", sql) is not None


def _write_fixture_csv(path: Path):
    # Use real Python booleans for is_valid_pdt
    rows = [
        # dt, parcel_qty, sum_bwt, sum_apt, is_valid_pdt, logistics_provider,
        # buyer_country, seller_country, buyer_region, seller_region
        ["2025-01-05", 10, 100, 50, True,  "SPX",         "MY", "DE", "SEA", "EU"],
        ["2025-01-10", 5,  40,  20, False, "DB Schenker", "MY", "DE", "SEA", "EU"],
        ["2025-02-03", 7,  70,  35, True,  "SPX",         "SG", "DE", "SEA", "EU"],
        ["2024-12-25", 100,1000,500, True,  "SPX",         "MY", "DE", "SEA", "EU"],  # outside date range
    ]
    df = pd.DataFrame(
        rows,
        columns=[
            "dt",
            "parcel_qty",
            "sum_bwt",
            "sum_apt",
            "is_valid_pdt",
            "logistics_provider",
            "buyer_country",
            "seller_country",
            "buyer_region",
            "seller_region",
        ],
    )
    df.to_csv(path, index=False)


def test_global_avg_bwt_executes_and_computes_correctly(tmp_path, monkeypatch):
    csv_path = tmp_path / "clean.csv"
    _write_fixture_csv(csv_path)
    monkeypatch.setattr(qt, "CLEANED_DATASET", str(csv_path))

    schema = QuerySchema(
        subject="global",
        metric="avg_bwt",
        sort_on="subject",  # falls back to metric
        ordering="asc",
        persona="Operational",
    )

    df = qt.query_tool(schema)

    # One row, no GROUP BY for global
    assert len(df) == 1
    assert "avg_bwt" in df.columns

    # avg_bwt = round(sum(sum_bwt)/sum(parcel_qty), 3) over valid rows in range
    # Valid rows in range: (100 over 10) + (70 over 7) -> 170/17 = 10.0
    assert float(df["avg_bwt"].iloc[0]) == 10.0


def test_filters_providers_and_buyer_country_executes(tmp_path, monkeypatch):
    csv_path = tmp_path / "clean.csv"
    _write_fixture_csv(csv_path)
    monkeypatch.setattr(qt, "CLEANED_DATASET", str(csv_path))

    schema = QuerySchema(
        subject="logistics_provider",
        metric="total_parcel_qty",
        sort_on="metric",
        ordering="desc",
        persona="Operational",
        logistics_providers=["SPX"],
        buyer_countries=["Malaysia"],   # resolves to 'MY'
        seller_countries=["Germany"],   # prevents mirroring; resolver drops it -> no seller filter
    )

    df = qt.query_tool(schema)

    # Should aggregate only SPX + buyer_country MY, valid rows, within dates
    assert len(df) == 1
    assert "total_parcels" in df.columns
    assert int(df["total_parcels"].iloc[0]) == 10


@pytest.mark.integration
def test_full_real_db_end_to_end(monkeypatch):
    # Ensure the configured dataset exists; skip if not present on this machine.
    dataset_path = Path(qt.CLEANED_DATASET)
    if not dataset_path.exists():
        pytest.skip(f"CLEANED_DATASET not found at {dataset_path}")

    captured = {"sql": None}

    # Intercept SQL for assertions but run the real DB query
    def wrapped_query(sql, conn, **kwargs):
        captured["sql"] = sql
        return database.query(sql, conn=conn, **kwargs)

    monkeypatch.setattr(qt, "query", wrapped_query)

    # Build a schema that uses all features:
    # - validity filter
    # - time_series subject (with aliasing)
    # - aggregation metric
    # - start/end dates
    # - providers + buyer/seller countries + regions
    # - sort_on metric + ordering + limit
    schema = QuerySchema(
        validity_filter="Valid Only",
        subject="time_series",
        time_granularity="month",
        metric="avg_bwt",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
        logistics_providers=["SPX", "DB Schenker"],
        buyer_countries=["Malaysia"],   # resolves -> MY
        seller_countries=["Singapore"], # resolves -> SG
        buyer_regions=["Johor"],
        seller_regions=["Bali"],
        sort_on="metric",
        ordering="desc",
        limit=3,
        persona="Operational",
    )

    df = qt.query_tool(schema)

    # It executed against the real DB and returned a DataFrame-like object
    assert hasattr(df, "columns")
    assert "avg_bwt" in df.columns
    # time_series alias should expose the time bucket column as month(dt)
    assert "month(dt)" in list(df.columns)
    # Limit applied (may be fewer rows if filters eliminate data)
    assert len(df) <= 3

    # Validate key SQL parts for completeness
    sql = captured["sql"]
    assert "SELECT" in sql and "FROM" in sql

    # Subject + Metric
    assert 'month(dt) AS "month(dt)"' in sql
    assert "round(sum(sum_bwt)/sum(parcel_qty), 3) AS avg_bwt" in sql

    # Validity + Date range
    assert "WHERE is_valid_pdt = TRUE" in sql
    assert "dt BETWEEN '2025-01-01' AND '2025-06-30'" in sql

    # Extra filters (providers from schema; countries/regions from resolver)
    assert "AND logistics_provider IN ('SPX', 'DB Schenker')" in sql
    assert "AND buyer_country IN ('MY')" in sql
    assert "AND seller_country IN ('SG')" in sql
    assert "AND buyer_region IN ('Johor')" in sql
    assert "AND seller_region IN ('Bali')" in sql

    # GROUP BY, ORDER BY, LIMIT
    assert re.search(r"GROUP BY\s+month\(dt\)", sql) is not None
    assert re.search(r"ORDER BY\s+avg_bwt\s+DESC", sql) is not None
    assert re.search(r"LIMIT\s+3\b", sql) is not None
