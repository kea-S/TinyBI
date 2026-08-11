import pytest
import pandas as pd
from unittest.mock import MagicMock

from src.utils.pydantic_models import QuerySchema
from src.tools.query_tool import execute_query
from tests.tools.test_query_tool import _base_final_entries, MockAIMessage

class MockSelfCorrectingLLM:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.last_prompt = None

    def invoke(self, prompt):
        response = self.responses[self.call_count]
        self.call_count += 1
        self.last_prompt = prompt
        return MockAIMessage(response)

def test_query_tool_self_correction(monkeypatch):
    entries = _base_final_entries()
    mock_vc = MagicMock()
    mock_vc.run.return_value = MagicMock()
    mock_vc.get_current_index_entries.return_value = []
    monkeypatch.setattr("src.tools.query_tool.VectorController", lambda *a, **kw: mock_vc)
    monkeypatch.setattr("src.tools.query_tool.resolve_columns", lambda *a, **kw: entries)
    monkeypatch.setattr("src.tools.query_tool.resolve_joins", lambda *a, **kw: MagicMock(joins=[], from_table="orders"))
    
    query = QuerySchema(user_question="dummy question", subject="provider", metric_hint="order_value")
    
    # First response is bad SQL, second is good SQL
    llm = MockSelfCorrectingLLM([
        "SELECT provider FROM orders WHERE bad_syntax",
        "SELECT provider FROM orders"
    ])
    
    # db.query should fail on the first call and succeed on the second
    call_count = [0]
    def mock_query(sql):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("bad syntax error from duckdb")
        return pd.DataFrame({"provider": ["SPX"]})
        
    monkeypatch.setattr("src.tools.query_tool.global_database.query", mock_query)
    
    # Execute query
    df, sql = execute_query(query, llm=llm)
    
    assert llm.call_count == 2
    assert call_count[0] == 2
    assert sql == "SELECT provider FROM orders"
    assert len(df) == 1
    
    # Check that the error message was passed in the second prompt
    last_prompt = llm.last_prompt
    assert isinstance(last_prompt, list)
    prompt_text = " ".join(getattr(m, "content", "") for m in last_prompt)
    assert "bad syntax error from duckdb" in prompt_text
