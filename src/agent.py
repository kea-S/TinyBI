import logging
from typing import Dict, List, Any, Optional

from langchain_core.messages import BaseMessage, SystemMessage

from src.utils.pydantic_models import AgentDecision
from src.tools.query_tool import execute_query

logger = logging.getLogger(__name__)


async def run_agent(messages: List[BaseMessage], llm: Any, tools: list, system_prompt: str) -> Dict[str, Any]:
    system_message = SystemMessage(content=system_prompt)
    all_messages = [system_message] + messages

    # 1. Use the LLM with structured output to make the routing decision
    structured_llm = llm.with_structured_output(AgentDecision)
    try:
        decision = await structured_llm.ainvoke(all_messages)
        
        # The LLM doesn't always populate user_question accurately, so we inject it here
        if decision.query_parameters:
            user_question = messages[-1].content if messages else "No question provided."
            decision.query_parameters.user_question = user_question
            
        logger.info(f"LLM Routing Decision: needs_database_query={decision.needs_database_query}")
        if decision.query_parameters:
            logger.info(f"Extracted Query Parameters: {decision.query_parameters.model_dump_json(indent=2)}")
    except Exception as e:
        logger.error(f"Error extracting AgentDecision: {e}")
        return {
            "output": f"Error parsing response: {str(e)}",
            "sql": None,
            "data": None,
            "token_usage": {"prompt": 0, "completion": 0, "total": 0, "num_requests": 1}
        }

    sql = None
    df = None
    output_message = ""

    # 2. Route based on the decision
    if decision.needs_database_query and decision.query_parameters:
        try:
            # We call the self-correcting query tool directly
            df, sql = execute_query(decision.query_parameters, llm)
            
            # Generate the natural language explanation
            from langchain_core.messages import HumanMessage
            markdown_table = df.head(10).to_markdown() if df is not None and not df.empty else "No data returned."
            user_question = messages[-1].content if messages else "No question provided."
            
            explainer_prompt = (
                f"The user asked: {user_question}\n"
                f"The database returned this data:\n{markdown_table}\n\n"
                f"Please write a concise natural language explanation answering their question based strictly on this data."
            )
            
            # Keep history context and append our prompt
            explainer_messages = all_messages + [HumanMessage(content=explainer_prompt)]
            explainer_response = await llm.ainvoke(explainer_messages)
            output_message = explainer_response.content
            
        except Exception as e:
            output_message = f"Error executing query: {str(e)}"
    else:
        # Conversational response
        output_message = decision.conversational_response or "I don't have a response for that."

    return {
        "output": output_message,
        "sql": sql,
        "data": df.to_dict(orient='records') if hasattr(df, "to_dict") else None,
        "token_usage": {
            "prompt": 0,
            "completion": 0,
            "total": 0,
            "num_requests": 1,
        }
    }



