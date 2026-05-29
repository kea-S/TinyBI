import pytest
from unittest.mock import MagicMock, patch
from src.tools.query_tool import execute_query
from src.utils.pydantic_models import (
    QuerySchema,
    CandidateEntries,
    ColumnVectorIndexEntry,
    VectorSearchResult
)

def _entry(entry_id: int, table_name: str, column_name: str, references: str = None):
    return ColumnVectorIndexEntry(
        entry_id=entry_id,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
        references=references,
        statistical_type="nominal",
    )


def _invoke_query_tool(query: QuerySchema):
    """Call execute_query directly (bypasses @tool wrapper)."""
    df, sql = execute_query(query)
    return df, sql


def _result(entry_id: int, score: float, table_name: str, column_name: str, references: str = None):
    return VectorSearchResult(
        entry=_entry(entry_id, table_name, column_name, references),
        score=score
    )

@patch("src.tools.query_tool.VectorController")
@patch("src.tools.query_tool.global_database")
def test_query_tool_cross_table_sql_generation(mock_db, mock_vc_class):
    mock_db.query.return_value = MagicMock()

    mock_vc = mock_vc_class.return_value
    
    candidates = CandidateEntries(
        subject_entries=[_result(1, 0.95, "users", "name")],
        metric_entries=[_result(2, 0.90, "orders", "total")],
        filter_entries={}
    )
    mock_vc.run.return_value = candidates
    
    mock_vc.get_current_index_entries.return_value = [
        _entry(1, "users", "id"),
        _entry(2, "orders", "total"),
        _entry(3, "orders", "user_id", references="users.id")
    ]
    
    query = QuerySchema(
        subject="name",
        metric_hint="total",
        aggregation="sum"
    )

    df, sql = _invoke_query_tool(query)

    sql_lower = sql.lower()
    assert "select" in sql_lower
    assert 'from "orders"' in sql_lower or 'from "users"' in sql_lower
    assert "join" in sql_lower
    assert '"users"."name"' in sql_lower
    assert 'sum("orders"."total")' in sql_lower or 'sum("total")' in sql_lower
    
    assert mock_db.query.called
