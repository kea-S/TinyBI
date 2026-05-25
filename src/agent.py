import logging
from typing import Annotated, Dict, List, Any, Optional, Union, Tuple

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools.query_tool import query_tool

logger = logging.getLogger(__name__)


class AgentState(MessagesState):
    sql: Optional[str] = None
    data: Optional[List[dict]] = None


def get_model_node(llm_with_tools):
    async def call_model(state: AgentState):
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}
    return call_model


def get_sql_tool_result(state: MessagesState) -> Tuple[Optional[str], Any]:
    """
    Returns the sql string generated as well as the result
    dataframe that was produced by running the sql string
    on the current database

    RETURNS
    sql: string
    df: pd.DataFrame
    """
    sql = None
    df = None

    messages = state.get("messages", [])
    # Iterate through messages to find tool results
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "query_tool":
            artifact = getattr(msg, "artifact", None)
            if artifact is None:
                continue

            try:
                # When using response_format="content_and_artifact", the second
                # return value is in 'artifact'.
                if isinstance(artifact, (tuple, list)) and len(artifact) == 2:
                    temp_df, temp_sql = artifact
                    # Basic validation that we have the right types
                    if hasattr(temp_df, "to_dict") and isinstance(temp_sql, str):
                        df = temp_df
                        sql = temp_sql
                        break
            except Exception as e:
                logger.error("Failed to extract tool result from artifact: %s", e)

    return sql, df


async def run_agent(messages: List[BaseMessage], llm: Any) -> Dict[str, Any]:
    # Bind tools
    tools = [query_tool]
    llm_with_tools = llm.bind_tools(tools)

    # Define the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", get_model_node(llm_with_tools))
    workflow.add_node("tools", ToolNode(tools))

    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )
    workflow.add_edge("tools", "agent")

    app = workflow.compile()

    # Run the graph
    final_state = await app.ainvoke({"messages": messages})

    # Extract results
    agent_output = final_state["messages"][-1].content
    sql, df = get_sql_tool_result(final_state)

    return {
        "output": agent_message if (agent_message := agent_output) else "",
        "sql": sql,
        "data": df.to_dict(orient='records') if df is not None else None
    }

