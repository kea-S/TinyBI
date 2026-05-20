import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from src.llms.agent import run_agent

@pytest.mark.anyio
async def test_agent_handles_greeting():
    # Mock the LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()
    
    mock_response = AIMessage(content="Hello! How can I help you today?")
    mock_llm.ainvoke.return_value = mock_response

    messages = [HumanMessage(content="Hello")]
    result = await run_agent(messages, llm=mock_llm)
    
    assert "Hello" in result["output"]
    assert result["sql"] is None
    assert result["data"] is None

@pytest.mark.anyio
async def test_agent_calls_query_tool():
    # Mock the LLM to return a tool call
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()
    
    # Mock tool call message
    tool_call = {
        "name": "query_tool",
        "args": {
            "subject": "provider",
            "metric_hint": "order value",
            "aggregation": "sum"
        },
        "id": "call_1"
    }
    mock_tool_message = AIMessage(
        content="",
        tool_calls=[tool_call]
    )
    
    # Final summary message
    mock_summary_message = AIMessage(content="Here are the providers by order value.")
    
    mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary_message]

    # Mock the tool implementation
    import pandas as pd
    from src.utils.pydantic_models import QuerySchema
    from langchain_core.tools import StructuredTool
    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})
    
    async def mock_query_func(subject: str, metric_hint: str, aggregation: str = None, **kwargs):
        return "Agent summary", (fake_df, "SELECT ...")
    
    # Create a real tool object but with our mock function
    mock_tool = StructuredTool.from_function(
        func=None,
        coroutine=mock_query_func,
        name="query_tool",
        description="Execute a query",
        response_format="content_and_artifact"
    )
    
    with patch("src.llms.agent.query_tool", mock_tool):
        messages = [HumanMessage(content="Show me providers by order value")]
        result = await run_agent(messages, llm=mock_llm)
        
        assert "providers" in result["output"]
        assert result["sql"] == "SELECT ..."
        assert result["data"] == [{"provider": "SPX", "total": 100}]
