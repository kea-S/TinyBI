import pytest
from unittest.mock import patch, MagicMock

from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FinalAttributes,
    FilterIntent,
    QuerySchema,
)
from src.tools.query_tool import query_tool


def _entry(table_name: str, column_name: str, **extra) -> ColumnVectorIndexEntry:
    defaults = dict(
        entry_id=1,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
    )
    defaults.update(extra)
    return ColumnVectorIndexEntry(**defaults)


def _base_final_attrs(
    subject_entries=None,
    metric_entry=None,
    filter_entries=None,
    primary_table="orders",
):
    if subject_entries is None:
        subject_entries = [_entry("orders", "provider")]
    return (
        FinalAttributes(
            subject_entries=subject_entries,
            metric_entry=metric_entry,
            filter_entries=filter_entries or {},
        ),
        primary_table,
    )


class TestQueryToolBuildsValidSQL:
    def test_select_from_with_subject_and_metric(self, monkeypatch):
        attrs, table = _base_final_attrs(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value", aggregation="sum")
        _, sql = query_tool(query)

        assert "SELECT" in sql
        assert "FROM orders" in sql
        assert "SUM(orders.order_value)" in sql
        assert "orders.provider" in sql

    def test_includes_where_clause_from_filters(self, monkeypatch):
        fi = FilterIntent(attribute_hint="country", operator="=", raw_value_text=("Singapore",))
        entry = _entry("orders", "buyer_country")
        attrs, table = _base_final_attrs(
            filter_entries={fi: entry},
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value", aggregation="sum", filters=[fi])
        _, sql = query_tool(query)

        assert "WHERE" in sql
        assert "orders.buyer_country = 'Singapore'" in sql

    def test_no_where_clause_when_no_filters(self, monkeypatch):
        attrs, table = _base_final_attrs(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value", aggregation="sum")
        _, sql = query_tool(query)

        assert "WHERE" not in sql

    def test_group_by_with_aggregation(self, monkeypatch):
        attrs, table = _base_final_attrs(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value", aggregation="sum")
        _, sql = query_tool(query)

        assert "GROUP BY" in sql

    def test_no_group_by_without_aggregation(self, monkeypatch):
        attrs, table = _base_final_attrs(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value")
        _, sql = query_tool(query)

        assert "GROUP BY" not in sql

    def test_limit_applied(self, monkeypatch):
        attrs, table = _base_final_attrs(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda _: (attrs, table))
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: object())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda *a: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        query = QuerySchema(subject="provider", metric_hint="order value", aggregation="sum", limit=5)
        _, sql = query_tool(query)

        assert "LIMIT 5" in sql