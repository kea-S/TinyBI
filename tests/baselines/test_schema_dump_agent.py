import os
import socket
from urllib.parse import urlparse

import pandas as pd
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import StructuredTool

from src.agent import run_agent
from src.baselines.prompts import build_schema_dump_prompt
from src.baselines.raw_query_tool import raw_query_tool


SAMPLE_DDL = """CREATE TABLE account (
    account_id BIGINT  -- the id of the account. | type: identifier
    district_id BIGINT  -- location of branch. | type: identifier
);"""


def _mock_raw_query_tool():
    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})

    async def mock_func(sql: str):
        return "SQL executed successfully.", (fake_df, sql)

    return StructuredTool.from_function(
        func=None,
        coroutine=mock_func,
        name="raw_query_tool",
        description="Execute raw SQL",
        response_format="content_and_artifact",
    )


class TestSchemaDumpAgentDDLInPrompt:
    @pytest.mark.anyio
    async def test_ddl_appears_in_system_prompt(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock()

        mock_llm.ainvoke.return_value = AIMessage(content="Hello!")

        await run_agent(
            messages=[HumanMessage(content="Hi")],
            llm=mock_llm,
            tools=[raw_query_tool],
            system_prompt=build_schema_dump_prompt(SAMPLE_DDL),
        )

        first_call_args = mock_llm.ainvoke.call_args_list[0]
        messages = first_call_args[0][0]
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]

        assert len(system_msgs) == 1
        assert SAMPLE_DDL in system_msgs[0].content
        assert "SQL" in system_msgs[0].content


class TestSchemaDumpAgentToolCall:
    @pytest.mark.anyio
    async def test_agent_calls_raw_query_tool_and_returns_result(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock()

        tool_call = {
            "name": "raw_query_tool",
            "args": {"sql": "SELECT provider, SUM(order_value) FROM orders GROUP BY provider"},
            "id": "call_1",
        }
        mock_tool_message = AIMessage(content="", tool_calls=[tool_call])
        mock_summary = AIMessage(content="Here are the providers by order value.")
        mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary]

        result = await run_agent(
            messages=[HumanMessage(content="Show me providers by order value")],
            llm=mock_llm,
            tools=[_mock_raw_query_tool()],
            system_prompt=build_schema_dump_prompt(SAMPLE_DDL),
        )

        assert "providers" in result["output"]
        assert result["sql"] is not None
        assert result["data"] == [{"provider": "SPX", "total": 100}]


class TestSchemaDumpAgentTokenUsage:
    @pytest.mark.anyio
    async def test_token_usage_tracked(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock()

        tool_call = {
            "name": "raw_query_tool",
            "args": {"sql": "SELECT COUNT(*) FROM account"},
            "id": "call_1",
        }
        mock_tool_message = AIMessage(
            content="",
            tool_calls=[tool_call],
            usage_metadata={"input_tokens": 50, "output_tokens": 30, "total_tokens": 80},
        )
        mock_summary = AIMessage(
            content="There are 100 accounts.",
            usage_metadata={"input_tokens": 60, "output_tokens": 20, "total_tokens": 80},
        )
        mock_llm.ainvoke.side_effect = [mock_tool_message, mock_summary]

        result = await run_agent(
            messages=[HumanMessage(content="How many accounts?")],
            llm=mock_llm,
            tools=[_mock_raw_query_tool()],
            system_prompt=build_schema_dump_prompt(SAMPLE_DDL),
        )

        assert result["token_usage"] == {
            "prompt": 110,
            "completion": 50,
            "total": 160,
            "num_requests": 2,
        }


class TestSchemaDumpAgentGreeting:
    @pytest.mark.anyio
    async def test_greeting_returns_no_sql(self):
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock()

        mock_llm.ainvoke.return_value = AIMessage(content="Hello! How can I help?")

        result = await run_agent(
            messages=[HumanMessage(content="Hello")],
            llm=mock_llm,
            tools=[raw_query_tool],
            system_prompt=build_schema_dump_prompt(SAMPLE_DDL),
        )

        assert "Hello" in result["output"]
        assert result["sql"] is None
        assert result["data"] is None


class TestGetSqlToolResultParameterized:
    def test_finds_raw_query_tool_artifact(self):
        from src.agent import get_sql_tool_result
        from langchain_core.messages import ToolMessage

        fake_df = pd.DataFrame({"x": [1]})
        tool_msg = ToolMessage(
            content="ok",
            tool_call_id="call_1",
            name="raw_query_tool",
            artifact=(fake_df, "SELECT x FROM t"),
        )
        state = {"messages": [tool_msg]}

        sql, df = get_sql_tool_result(state, tool_name="raw_query_tool")

        assert sql == "SELECT x FROM t"
        assert df.equals(fake_df)

    def test_ignores_wrong_tool_name(self):
        from src.agent import get_sql_tool_result
        from langchain_core.messages import ToolMessage

        fake_df = pd.DataFrame({"x": [1]})
        tool_msg = ToolMessage(
            content="ok",
            tool_call_id="call_1",
            name="raw_query_tool",
            artifact=(fake_df, "SELECT x FROM t"),
        )
        state = {"messages": [tool_msg]}

        sql, df = get_sql_tool_result(state, tool_name="query_tool")

        assert sql is None
        assert df is None


class TestSchemaDumpAgentIntegration:
    @pytest.mark.integration
    @pytest.mark.anyio
    async def test_end_to_end_with_real_llm(self):
        endpoint = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        hostname = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        try:
            with socket.create_connection((hostname, port), timeout=1):
                pass
        except OSError:
            pytest.skip("Ollama is not reachable")

        from src.baselines.ddl_generator import generate_ddl
        from src.utils.models import get_local_llm, LOCAL_GRANITE4
        from src.config import APP_DATA_PATH
        from pathlib import Path

        ddl_schema = generate_ddl(str(Path(APP_DATA_PATH) / "columns.json"))
        llm = get_local_llm(LOCAL_GRANITE4)

        result = await run_agent(
            messages=[HumanMessage(content="How many accounts are there?")],
            llm=llm,
            tools=[raw_query_tool],
            system_prompt=build_schema_dump_prompt(ddl_schema),
        )

        assert result["output"], "agent should return a non-empty output"
        assert result["sql"] is not None, "agent should execute a SQL query"
        assert "SELECT" in result["sql"].upper(), "SQL should contain SELECT"
        assert result["data"] is not None, "agent should return data"
        assert result["token_usage"]["num_requests"] >= 1, "should track at least 1 LLM call"
