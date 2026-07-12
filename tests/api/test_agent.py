import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import HumanMessage
from src.agent import run_agent

try:
    from src.utils.pydantic_models import QuerySchema, AgentDecision
except ImportError:
    # Fallbacks so the test file parses, but fails in the test
    QuerySchema = None
    AgentDecision = None

import pandas as pd

@pytest.mark.asyncio
async def test_router_decides_conversation_only():
    """Test when the agent decides it only needs to converse and not query."""
    if AgentDecision is None:
        pytest.fail("AgentDecision schema is not defined")
        
    mock_llm = MagicMock()
    mock_structured_llm = AsyncMock()
    
    # Mock the LLM to return a conversational decision
    mock_decision = AgentDecision(
        needs_database_query=False,
        conversational_response="I can certainly help explain those numbers."
    )
    mock_structured_llm.ainvoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    messages = [HumanMessage(content="Can you explain those numbers?")]
    
    # We should be able to run the agent without the query_tool ever being invoked
    result = await run_agent(messages, mock_llm, tools=[], system_prompt="Test Prompt")
    
    assert result["output"] == "I can certainly help explain those numbers."
    assert result["sql"] is None
    assert result["data"] is None

@pytest.mark.asyncio
async def test_agent_generates_explainer_on_success():
    """Test when the agent queries the database and then generates a natural language explanation."""
    if AgentDecision is None or QuerySchema is None:
        pytest.fail("AgentDecision or QuerySchema is not defined")
        
    mock_llm = MagicMock()
    
    # 1. Mock the structured LLM for the routing decision
    mock_structured_llm = AsyncMock()
    mock_decision = AgentDecision(
        needs_database_query=True,
        query_parameters=QuerySchema(subject="provider")
    )
    mock_structured_llm.ainvoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    # 2. Mock the unstructured LLM for the final explainer response
    from langchain_core.messages import AIMessage
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Based on the data, the average is 5."))
    
    # 3. Mock execute_query
    fake_df = pd.DataFrame({"col": [1, 2]})
    fake_sql = "SELECT * FROM dummy"
    
    messages = [HumanMessage(content="Show me average waiting time")]
    
    with patch("src.agent.execute_query", return_value=(fake_df, fake_sql)):
        result = await run_agent(messages, mock_llm, tools=[], system_prompt="Test Prompt")
        
    assert result["sql"] == fake_sql
    assert result["data"] is not None
    assert result["output"] == "Based on the data, the average is 5."
    # Assert that the explainer was actually called
    assert mock_llm.ainvoke.call_count == 1

@pytest.mark.asyncio
async def test_agent_skips_explainer_on_error():
    """Test that if the database query throws an error, the LLM is not invoked a second time."""
    mock_llm = MagicMock()
    
    mock_structured_llm = AsyncMock()
    mock_decision = AgentDecision(
        needs_database_query=True,
        query_parameters=QuerySchema(subject="provider")
    )
    mock_structured_llm.ainvoke.return_value = mock_decision
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_llm.ainvoke = AsyncMock()
    
    messages = [HumanMessage(content="Break it")]
    
    with patch("src.agent.execute_query", side_effect=ValueError("Database exploded")):
        result = await run_agent(messages, mock_llm, tools=[], system_prompt="Test Prompt")
        
    assert result["sql"] is None
    assert "Database exploded" in result["output"]
    # Should NOT have called the explainer
    mock_llm.ainvoke.assert_not_called()

def test_agent_decision_schema():
    """Test the Pydantic schema for AgentDecision."""
    if AgentDecision is None:
        pytest.fail("AgentDecision schema is not defined")
        
    decision_conv = AgentDecision(
        needs_database_query=False,
        conversational_response="Hello!"
    )
    assert decision_conv.needs_database_query is False
    assert decision_conv.conversational_response == "Hello!"
    assert decision_conv.query_parameters is None
    
    decision_query = AgentDecision(
        needs_database_query=True,
        query_parameters=QuerySchema(subject="provider")
    )
    assert decision_query.needs_database_query is True
    assert decision_query.query_parameters is not None
    assert decision_query.query_parameters.subject == "provider"
