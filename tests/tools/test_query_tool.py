import os
import socket
from urllib.parse import urlparse
from unittest.mock import MagicMock
import pandas as pd
import pytest

from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FinalEntries,
    FinalJoins,
    FilterIntent,
    JoinStep,
    QuerySchema,
)
from src.tools.query_tool import make_query_tool, execute_query
from src.utils.rag.vector_controller import VectorController


def _invoke_query_tool(query: QuerySchema, llm=None):
    """Call execute_query directly (bypasses @tool wrapper)."""
    df, sql = execute_query(query, llm=llm)
    return df, sql


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
        statistical_type="nominal",
    )
    defaults.update(extra)
    return ColumnVectorIndexEntry(**defaults)


def _base_final_entries(
    subject_entries=None,
    metric_entry=None,
    filter_entries=None,
):
    if subject_entries is None:
        subject_entries = [_entry("orders", "provider")]
    return FinalEntries(
        subject_entries=subject_entries,
        metric_entry=metric_entry,
        filter_entries=filter_entries or {},
    )


class MockAIMessage:
    def __init__(self, content: str):
        self.content = content


class MockLLM:
    def __init__(self, response: str):
        self.response = response
        self.call_count = 0
        self.last_prompt = None

    def invoke(self, prompt):
        self.call_count += 1
        self.last_prompt = prompt
        return MockAIMessage(self.response)


class TestQueryToolBuildsValidSQL:
    def test_select_from_with_subject_and_metric(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum")
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") AS "order_value" '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "SELECT" in sql
        assert 'FROM "orders"' in sql
        assert 'SUM("orders"."order_value")' in sql
        assert '"orders"."provider"' in sql

    def test_includes_where_clause_from_filters(self, monkeypatch):
        fi = FilterIntent(attribute_hint="country", operator="=", raw_value_text=("Singapore",))
        entry = _entry("orders", "buyer_country")
        entries = _base_final_entries(
            filter_entries={fi: entry},
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum", filters=[fi])
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") AS "order_value" '
            'FROM "orders" WHERE "orders"."buyer_country" = \'Singapore\' '
            'GROUP BY "orders"."provider"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "WHERE" in sql
        assert '"orders"."buyer_country" = \'Singapore\'' in sql

    def test_no_where_clause_when_no_filters(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum")
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") AS "order_value" '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "WHERE" not in sql

    def test_group_by_with_aggregation(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum")
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "GROUP BY" in sql

    def test_no_group_by_without_aggregation(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value")
        llm = MockLLM(
            'SELECT "orders"."provider", "orders"."order_value" FROM "orders"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "GROUP BY" not in sql

    def test_raises_when_no_subject_or_metric_resolved(self, monkeypatch):
        entries = FinalEntries(
            subject_entries=[],
            metric_entry=None,
            filter_entries={},
        )
        joins = FinalJoins(from_table="orders", joins=[])
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a: joins)
        db_mock = MagicMock()
        monkeypatch.setattr("src.tools.query_tool.global_database", db_mock)

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value")
        llm = MockLLM("SELECT 1")
        with pytest.raises(ValueError, match="No columns could be resolved"):
            _invoke_query_tool(query, llm=llm)

        db_mock.query.assert_not_called()

    def test_select_with_count_distinct_aggregation(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "district_id"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="distinct districts", aggregation="count_distinct")
        llm = MockLLM(
            'SELECT "orders"."provider", COUNT(DISTINCT "orders"."district_id") '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert 'COUNT(DISTINCT "orders"."district_id")' in sql

    def test_limit_applied(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum", limit=5)
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") '
            'FROM "orders" GROUP BY "orders"."provider" LIMIT 5'
        )
        _, sql = _invoke_query_tool(query, llm=llm)

        assert "LIMIT 5" in sql


class TestExecuteQueryDirectCall:
    def test_accepts_query_schema_directly(self, monkeypatch):
        entries = _base_final_entries(
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum")
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        df, sql = execute_query(query, llm=llm)

        assert "SELECT" in sql


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
                statistical_type="nominal",
                categorical_values={"DB Schenker": [], "SPX": []},
            ),
            ColumnVectorIndexEntry(
                entry_id=1,
                table_name="orders",
                column_name="buyer_country",
                source_key="orders.buyer_country",
                statistical_type="nominal",
                categorical_values={"Singapore": [], "Malaysia": []},
            ),
            ColumnVectorIndexEntry(
                entry_id=2,
                table_name="orders",
                column_name="order_value",
                source_key="orders.order_value",
                statistical_type="quantitative",
            ),
        ]

        controller = VectorController("nomic-embed-text", vector_index_path=tmp_path / "columns")
        controller.batch_insert_index_entries(entries)

        monkeypatch.setattr(
            "src.tools.query_tool.VectorController",
            lambda *a, **kw: controller,
        )
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=("DB Schenker",),
        )
        query = QuerySchema(user_question="dummy question", 
            subject="provider",
            metric_hint="order value",
            aggregation="sum",
            filters=[fi],
            sort_on="metric_hint",
            ordering="desc",
            limit=5,
        )

        _, sql = _invoke_query_tool(query)

        assert "SELECT" in sql
        assert "FROM" in sql


class TestLLMGeneratedSQL:
    def test_pure_aggregate_no_subject(self, monkeypatch):
        fi = FilterIntent(
            attribute_hint="average salary",
            operator=">",
            raw_value_text=("8000",),
        )
        entries = _base_final_entries(
            subject_entries=[],
            metric_entry=None,
            filter_entries={fi: _entry("district", "A11")},
        )
        joins = FinalJoins(from_table="client", joins=[])

        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a: joins)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        llm = MockLLM(
            'SELECT COUNT(*) FROM "client" '
            'INNER JOIN "district" ON "client"."district_id" = "district"."district_id" '
            'WHERE "district"."A11" > 8000'
        )

        query = QuerySchema(user_question="dummy question", 
            subject=None,
            metric_hint="count",
            aggregation="count",
            filters=[fi],
        )
        df, sql = execute_query(query, llm=llm)

        assert llm.call_count == 1
        assert "COUNT(*)" in sql
        assert "GROUP BY" not in sql
        assert "WHERE" in sql
        assert '"district"."A11"' in sql
        assert "client" in sql

    def test_grouped_aggregate_with_subject(self, monkeypatch):
        entries = _base_final_entries(
            subject_entries=[_entry("orders", "provider")],
            metric_entry=_entry("orders", "order_value"),
        )
        joins = FinalJoins(from_table="orders", joins=[])

        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a: joins)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") AS total '
            'FROM "orders" GROUP BY "orders"."provider"'
        )

        query = QuerySchema(user_question="dummy question", 
            subject="provider",
            metric_hint="order value",
            aggregation="sum",
        )
        df, sql = execute_query(query, llm=llm)

        assert llm.call_count == 1
        assert '"orders"."provider"' in sql
        assert "GROUP BY" in sql
        assert "SUM(" in sql

    def test_simple_filter_no_aggregation(self, monkeypatch):
        fi = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=("M",),
        )
        entries = _base_final_entries(
            subject_entries=[_entry("client", "client_id")],
            metric_entry=_entry("client", "client_id"),
            filter_entries={fi: _entry("client", "gender")},
        )
        joins = FinalJoins(from_table="client", joins=[])

        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a: joins)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        llm = MockLLM(
            'SELECT "client"."client_id" FROM "client" WHERE "client"."gender" = \'M\''
        )

        query = QuerySchema(user_question="dummy question", 
            subject="client",
            metric_hint="client",
            filters=[fi],
        )
        df, sql = execute_query(query, llm=llm)

        assert llm.call_count == 1
        assert "SELECT" in sql
        assert "WHERE" in sql
        assert "COUNT(" not in sql
        assert "SUM(" not in sql
        assert "AVG(" not in sql
        assert "GROUP BY" not in sql

    def test_join_with_multiple_filters(self, monkeypatch):
        fi_gender = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=("M",),
        )
        fi_region = FilterIntent(
            attribute_hint="region",
            operator="=",
            raw_value_text=("north Bohemia",),
        )
        entries = _base_final_entries(
            subject_entries=[],
            metric_entry=None,
            filter_entries={
                fi_gender: _entry("client", "gender"),
                fi_region: _entry("district", "A3"),
            },
        )
        joins = FinalJoins(
            from_table="client",
            joins=[
                JoinStep(
                    table="district",
                    parent="client",
                    on_clause="client.district_id = district.district_id",
                ),
            ],
        )

        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a: joins)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        llm = MockLLM(
            'SELECT COUNT(*) FROM "client" '
            'INNER JOIN "district" ON "client"."district_id" = "district"."district_id" '
            'WHERE "client"."gender" = \'M\' AND "district"."A3" = \'north Bohemia\''
        )

        query = QuerySchema(user_question="dummy question", 
            subject=None,
            metric_hint="count",
            aggregation="count",
            filters=[fi_gender, fi_region],
        )
        df, sql = execute_query(query, llm=llm)

        assert llm.call_count == 1
        assert "JOIN" in sql
        assert "WHERE" in sql
        assert '"client"."gender"' in sql
        assert '"district"."A3"' in sql
        assert "COUNT(" in sql
        assert "GROUP BY" not in sql


class TestMakeQueryTool:
    def test_returns_tool_with_correct_name(self):
        llm = MockLLM("SELECT 1")
        tool = make_query_tool(llm)
        assert tool.name == "query_tool"

    def test_factory_creates_independent_tools(self, monkeypatch):
        llm1 = MockLLM('SELECT "orders"."provider" FROM "orders"')
        llm2 = MockLLM('SELECT "orders"."provider" FROM "orders"')
        tool1 = make_query_tool(llm1)
        tool2 = make_query_tool(llm2)

        entries = _base_final_entries(
            subject_entries=[_entry("orders", "provider")],
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="x", aggregation="sum")
        tool1.invoke(query.model_dump())
        tool2.invoke(query.model_dump())

        assert llm1.call_count == 1
        assert llm2.call_count == 1

    def test_tool_invocation_uses_factory_llm(self, monkeypatch):
        llm = MockLLM(
            'SELECT "orders"."provider", SUM("orders"."order_value") '
            'FROM "orders" GROUP BY "orders"."provider"'
        )
        tool = make_query_tool(llm)

        entries = _base_final_entries(
            subject_entries=[_entry("orders", "provider")],
            metric_entry=_entry("orders", "order_value"),
        )
        mock_vc = MagicMock()
        mock_vc.run.return_value = MagicMock()
        mock_vc.get_current_index_entries.return_value = []
        monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
        monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
        monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: pd.DataFrame())

        query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order value", aggregation="sum")
        result = tool.invoke(query.model_dump())

        assert llm.call_count == 1
        assert "SQL executed successfully" in result
        assert "SUM(" in result