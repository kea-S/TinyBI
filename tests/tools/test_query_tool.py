import os
import socket
from urllib.parse import urlparse
from unittest.mock import MagicMock
import pandas as pd
import pytest

from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FinalAttributes,
    FilterIntent,
    QuerySchema,
)
from src.tools.query_tool import query_tool
from src.utils.rag.vector_controller import VectorController


class FakeEmbeddingModel:
    def __init__(self):
        self.document_inputs = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_inputs.append(texts)
        dim = len(texts)
        return [[1.0 if i == j else 0.0 for j in range(dim)] for i in range(dim)]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


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


class TestQueryToolIntegration:
    @pytest.mark.integration
    def test_end_to_end_produces_valid_sql(self, monkeypatch, tmp_path):
        endpoint = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        hostname = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        try:
            with socket.create_connection((hostname, port), timeout=1):
                pass
        except OSError:
            pytest.skip("Ollama is not reachable")

        entries = [
            ColumnVectorIndexEntry(
                entry_id=0,
                table_name="orders",
                column_name="provider",
                source_key="orders.provider",
                payload={"is_categorical": True, "canonical_values": ["DB Schenker", "SPX"]},
            ),
            ColumnVectorIndexEntry(
                entry_id=1,
                table_name="orders",
                column_name="buyer_country",
                source_key="orders.buyer_country",
                payload={"is_categorical": True, "canonical_values": ["Singapore", "Malaysia"]},
            ),
            ColumnVectorIndexEntry(
                entry_id=2,
                table_name="orders",
                column_name="order_value",
                source_key="orders.order_value",
                payload={"is_categorical": False},
            ),
        ]

        controller = VectorController("nomic-embed-text", vector_index_path=tmp_path / "columns")
        controller.batch_insert_index_entries(entries)

        monkeypatch.setattr(
            "src.tools.query_tool.VectorController",
            lambda *a, **kw: controller,
        )
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())
        monkeypatch.setattr("src.tools.query_tool.global_database.get_connection", lambda _: None)
        monkeypatch.setattr("src.tools.query_tool.global_database.close_connection", lambda: None)

        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=("DB Schenker",),
        )
        query = QuerySchema(
            subject="provider",
            metric_hint="order value",
            aggregation="sum",
            filters=[fi],
            sort_on="metric_hint",
            ordering="desc",
            limit=5,
        )

        _, sql = query_tool(query, dataset_path=str(tmp_path / "test.csv"))

        print(sql)

        assert "SELECT" in sql
        assert "FROM" in sql
