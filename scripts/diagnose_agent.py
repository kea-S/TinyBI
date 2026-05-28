import asyncio
import logging
from src.agent import run_agent
from langchain_core.messages import HumanMessage
from src.utils.models import get_remote_llm, REMOTE_LLAMA_8B

# Disable excessive logging for cleaner output
logging.getLogger("src.agent").setLevel(logging.WARNING)
logging.getLogger("src.tools.query_tool").setLevel(logging.WARNING)

async def test():
    llm = get_remote_llm(REMOTE_LLAMA_8B)
    questions = [
        "What are the top 5 order types?",
        "Show me total order amounts by year",
        "Which card types have the highest balance?"
    ]
    for q in questions:
        print(f"\n--- Testing: {q} ---")
        try:
            result = await run_agent([HumanMessage(content=q)], llm)
            print(f"Agent Output: {result.get('output')}")
            print(f"Generated SQL: {result.get('sql')}")
        except Exception as e:
            print(f"FAILED with Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
