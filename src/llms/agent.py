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
    sql = None
    data = None

    # Iterate through messages to find tool results
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, ToolMessage) and msg.name == "query_tool":
            try:
                # When using response_format="content_and_artifact", the second 
                # return value is in 'artifact'.
                if msg.artifact and isinstance(msg.artifact, tuple):
                    df, sql = msg.artifact
                    data = df.to_dict(orient="records")
                    break
            except Exception as e:
                logger.error("Failed to extract tool result from artifact: %s", e)

    return {
        "output": agent_message if (agent_message := agent_output) else "",
        "sql": sql,
        "data": data
    }
