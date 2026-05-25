import pytest
from unittest.mock import MagicMock, patch
from src.tools.query_tool import query_tool
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
    """Helper to explicitly unpack QuerySchema for the LangChain tool."""
    summary, (df, sql) = query_tool.func(
        subject=query.subject,
        metric_hint=query.metric_hint,
        aggregation=query.aggregation,
        filters=[f.model_dump() for f in query.filters] if query.filters else [],
        sort_on=query.sort_on,
        ordering=query.ordering,
        limit=query.limit,
    )
    return df, sql


def _result(entry_id: int, score: float, table_name: str, column_name: str, references: str = None):
    return VectorSearchResult(
        entry=_entry(entry_id, table_name, column_name, references),
        score=score
    )

@patch("src.tools.query_tool.VectorController")
@patch("src.tools.query_tool.global_database")
def test_query_tool_cross_table_sql_generation(mock_db, mock_vc_class):
    # Setup mock VectorController
    mock_vc = mock_vc_class.return_value
    
    # 1. Mock candidates: Subject in 'users', Metric in 'orders'
    # Both connected via orders.user_id -> users.id
    candidates = CandidateEntries(
        subject_entries=[_result(1, 0.95, "users", "name")],
        metric_entries=[_result(2, 0.90, "orders", "total")],
        filter_entries={}
    )
    mock_vc.run.return_value = candidates
    
    # 2. Mock all index entries for graph building
    mock_vc.get_current_index_entries.return_value = [
        _entry(1, "users", "id"),
        _entry(2, "orders", "total"),
        _entry(3, "orders", "user_id", references="users.id")
    ]
    
    # 3. Create a structured query
    query = QuerySchema(
        subject="name",
        metric_hint="total",
        aggregation="sum"
    )

    # 4. Run tool
    df, sql = _invoke_query_tool(query)

    # 5. Assertions

    # SQL should contain a JOIN and select from both tables
    sql_lower = sql.lower()
    assert "select" in sql_lower
    assert "from orders" in sql_lower or "from users" in sql_lower
    assert "join" in sql_lower
    assert "users.name" in sql_lower
    assert "sum(orders.total)" in sql_lower or "sum(total)" in sql_lower
    
    # Ensure database was called
    assert mock_db.query.called
