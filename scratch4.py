import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent import run_agent
from src.tools.query_tool import make_query_tool
from src.utils.models import get_local_llm, LOCAL_GRANITE4
from src.utils.prompts import EXTRACTOR_PROMPT

async def main():
    llm = get_local_llm(LOCAL_GRANITE4)
    tools = [make_query_tool(llm)]
    messages = [HumanMessage(content="what about for Singapore?")]
    result = await run_agent(messages, llm, tools, EXTRACTOR_PROMPT)
    print("AGENT OUTPUT:", repr(result.get("output", "None")))
    print("SQL:", result.get("sql"))

if __name__ == "__main__":
    asyncio.run(main())
