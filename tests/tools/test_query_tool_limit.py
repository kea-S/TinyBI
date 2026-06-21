from unittest.mock import MagicMock
import pytest
from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FinalEntries,
    QuerySchema,
)
from src.tools.query_tool import execute_query, global_database
from tests.tools.test_query_tool import MockLLM

def _mock_setup_database(monkeypatch):
    mock_conn = MagicMock()
    def replacement(*a, **kw):
        global_database._CONN = mock_conn
    monkeypatch.setattr("src.tools.query_tool.global_database.setup_database", replacement)


def _invoke_query_tool(query: QuerySchema, llm=None):
    """Call execute_query directly (bypasses @tool wrapper)."""
    df, sql = execute_query(query, llm=llm)
    return df, sql


def _entry(table_name: str, column_name: str) -> ColumnVectorIndexEntry:
    return ColumnVectorIndexEntry(
        entry_id=1,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
        statistical_type="nominal"
    )

def test_query_tool_defaults_to_limit_1000(monkeypatch):
    # Setup mocks to skip vector search and resolution
    entries = FinalEntries(
        subject_entries=[_entry("orders", "provider")],
        metric_entry=None,
        filter_entries={},
    )

    mock_vc = MagicMock()
    mock_vc.run.return_value = MagicMock()
    mock_vc.get_current_index_entries.return_value = []
    monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
    monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
    monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: MagicMock())
    _mock_setup_database(monkeypatch)

    # Query without explicit limit
    query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order total")
    llm = MockLLM('SELECT "orders"."provider" FROM "orders" LIMIT 1000')
    _, sql = _invoke_query_tool(query, llm=llm)

    assert "LIMIT 1000" in sql

def test_query_tool_respects_explicit_limit(monkeypatch):
    entries = FinalEntries(
        subject_entries=[_entry("orders", "provider")],
        metric_entry=None,
        filter_entries={},
    )

    mock_vc = MagicMock()
    mock_vc.run.return_value = MagicMock()
    mock_vc.get_current_index_entries.return_value = []
    monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
    monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a: entries)
    monkeypatch.setattr("src.tools.query_tool.global_database.query", lambda sql: MagicMock())
    _mock_setup_database(monkeypatch)

    # Query with explicit limit 10
    query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order total", limit=10)
    llm = MockLLM('SELECT "orders"."provider" FROM "orders" LIMIT 10')
    _, sql = _invoke_query_tool(query, llm=llm)

    assert "LIMIT 10" in sql
    assert "LIMIT 5" not in sql






