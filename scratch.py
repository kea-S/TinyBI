import asyncio
import os
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent import run_agent
from src.tools.query_tool import make_query_tool
from src.utils.models import get_local_llm, LOCAL_GRANITE4
from src.utils.prompts import EXTRACTOR_PROMPT

async def main():
    llm = get_local_llm(LOCAL_GRANITE4)
    tools = [make_query_tool(llm)]
    system_message = SystemMessage(content=EXTRACTOR_PROMPT)
    messages = [HumanMessage(content="Show me the average buyer waiting time by provider")]
    
    result = await run_agent(messages, llm, tools, EXTRACTOR_PROMPT)
    print("FINAL STATE MESSAGES:")
    print(result.get("messages", []))
    print("AGENT OUTPUT:")
    print(result.get("output", "None"))
    
    # Check if sql exists in final result
    print("SQL:")
    print(result.get("sql", "None"))

if __name__ == "__main__":
    asyncio.run(main())
