import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from src.agent import run_agent
from src.utils.prompts import EXTRACTOR_PROMPT

@pytest.mark.anyio
async def test_agent_handles_greeting():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    mock_response = AIMessage(content="Hello! How can I help you today?")
    mock_llm.ainvoke.return_value = mock_response

    messages = [HumanMessage(content="Hello")]
    result = await run_agent(messages, llm=mock_llm, tools=[], system_prompt=EXTRACTOR_PROMPT)

    assert "Hello" in result["output"]
    assert result["sql"] is None
    assert result["data"] is None

@pytest.mark.anyio
async def test_agent_calls_query_tool():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    tool_call = {
        "name": "query_tool",
        "args": {
            "subject": "provider",
            "metric_hint": "order value",
            "aggregation": "sum"
        },
        "id": "call_1"
    }
    mock_tool_message = AIMessage(content="", tool_calls=[tool_call])
    mock_summary_message = AIMessage(content="Here are the providers by order value.")
    mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary_message]

    import pandas as pd
    from langchain_core.tools import StructuredTool
    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})

    async def mock_query_func(subject: str, metric_hint: str, aggregation: str = None, **kwargs):
        return "Agent summary", (fake_df, "SELECT ...")

    mock_tool = StructuredTool.from_function(
        func=None,
        coroutine=mock_query_func,
        name="query_tool",
        description="Execute a query",
        response_format="content_and_artifact"
    )

    messages = [HumanMessage(content="Show me providers by order value")]
    result = await run_agent(messages, llm=mock_llm, tools=[mock_tool], system_prompt=EXTRACTOR_PROMPT)

    assert "providers" in result["output"]
    assert result["sql"] == "SELECT ..."
    assert result["data"] == [{"provider": "SPX", "total": 100}]


@pytest.mark.anyio
async def test_agent_tracks_token_usage_single_call():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    mock_response = AIMessage(
        content="Hello! How can I help you today?",
        usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    )
    mock_llm.ainvoke.return_value = mock_response

    messages = [HumanMessage(content="Hello")]
    result = await run_agent(messages, llm=mock_llm, tools=[], system_prompt=EXTRACTOR_PROMPT)

    assert "token_usage" in result
    assert result["token_usage"] == {
        "prompt": 10,
        "completion": 20,
        "total": 30,
        "num_requests": 1,
    }


@pytest.mark.anyio
async def test_agent_accumulates_token_usage_across_calls():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    tool_call = {
        "name": "query_tool",
        "args": {
            "subject": "account",
            "metric_hint": "count",
            "aggregation": "count",
        },
        "id": "call_1",
    }
    mock_tool_message = AIMessage(
        content="",
        tool_calls=[tool_call],
        usage_metadata={"input_tokens": 5, "output_tokens": 8, "total_tokens": 13},
    )
    mock_summary_message = AIMessage(
        content="There are 10 accounts.",
        usage_metadata={"input_tokens": 12, "output_tokens": 6, "total_tokens": 18},
    )

    mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary_message]

    import pandas as pd
    from langchain_core.tools import StructuredTool

    async def mock_query_func(subject: str, metric_hint: str, aggregation: str = None, **kwargs):
        return "Agent summary", (pd.DataFrame({"count": [10]}), "SELECT COUNT(*) FROM account")

    mock_tool = StructuredTool.from_function(
        func=None,
        coroutine=mock_query_func,
        name="query_tool",
        description="Execute a query",
        response_format="content_and_artifact",
    )

    messages = [HumanMessage(content="How many accounts are there?")]
    result = await run_agent(messages, llm=mock_llm, tools=[mock_tool], system_prompt=EXTRACTOR_PROMPT)

    assert "token_usage" in result
    assert result["token_usage"] == {
        "prompt": 17,
        "completion": 14,
        "total": 31,
        "num_requests": 2,
    }


@pytest.mark.anyio
async def test_run_agent_uses_tools_param():
    import pandas as pd
    from langchain_core.tools import StructuredTool

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    fake_df = pd.DataFrame({"result": [42]})

    async def mock_custom_tool(query: str):
        return "Custom result", (fake_df, "SELECT 42")

    custom_tool = StructuredTool.from_function(
        func=None,
        coroutine=mock_custom_tool,
        name="custom_tool",
        description="A custom tool",
        response_format="content_and_artifact",
    )

    tool_call = {
        "name": "custom_tool",
        "args": {"query": "test"},
        "id": "call_1",
    }
    mock_tool_message = AIMessage(content="", tool_calls=[tool_call])
    mock_summary = AIMessage(content="Result is 42")
    mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary]

    from src.utils.prompts import EXTRACTOR_PROMPT
    messages = [HumanMessage(content="test query")]
    result = await run_agent(messages, llm=mock_llm, tools=[custom_tool], system_prompt=EXTRACTOR_PROMPT)

    assert result["output"] == "Result is 42"
    assert result["sql"] == "SELECT 42"
    assert result["data"] == [{"result": 42}]


@pytest.mark.anyio
async def test_run_agent_uses_system_prompt_param():
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    mock_llm.ainvoke.return_value = AIMessage(content="Hello!")

    from src.utils.prompts import EXTRACTOR_PROMPT
    from langchain_core.messages import SystemMessage

    custom_prompt = "You are a custom SQL expert. Answer questions using SQL."
    messages = [HumanMessage(content="Hi")]

    await run_agent(messages, llm=mock_llm, tools=[], system_prompt=custom_prompt)

    first_call_args = mock_llm.ainvoke.call_args_list[0]
    call_messages = first_call_args[0][0]
    system_msgs = [m for m in call_messages if isinstance(m, SystemMessage)]

    assert len(system_msgs) == 1
    assert system_msgs[0].content == custom_prompt


@pytest.mark.anyio
async def test_run_agent_derives_tool_name_from_tools():
    import pandas as pd
    from langchain_core.tools import StructuredTool
    from langchain_core.messages import ToolMessage

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()

    fake_df = pd.DataFrame({"x": [1]})

    async def mock_func(sql: str):
        return "ok", (fake_df, "SELECT 1")

    named_tool = StructuredTool.from_function(
        func=None,
        coroutine=mock_func,
        name="my_custom_tool",
        description="Custom",
        response_format="content_and_artifact",
    )

    tool_call = {
        "name": "my_custom_tool",
        "args": {"sql": "SELECT 1"},
        "id": "call_1",
    }
    mock_tool_message = AIMessage(content="", tool_calls=[tool_call])
    mock_summary = AIMessage(content="Done")
    mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary]

    from src.utils.prompts import EXTRACTOR_PROMPT
    messages = [HumanMessage(content="test")]
    result = await run_agent(messages, llm=mock_llm, tools=[named_tool], system_prompt=EXTRACTOR_PROMPT)

    assert result["sql"] == "SELECT 1"
    assert result["data"] == [{"x": 1}]
