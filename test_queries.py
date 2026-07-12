import asyncio
import logging
from langchain_core.messages import HumanMessage
from src.agent import run_agent
from src.utils.models import get_llm
from src.utils.prompts import load_prompt_text

logging.basicConfig(level=logging.ERROR)

async def main():
    queries = [
        "What is the percentage of loan amount that has been fully paid with no issue.",
        "For loan amount less than USD100,000, what is the percentage of accounts that is still running with no issue.",
        "Between 1/1/1995 and 12/31/1997, how many loans in the amount of at least 250,000 per account that chose monthly statement issuance were approved?"
    ]
    
    llm = get_llm(local=True)
    system_prompt = load_prompt_text("extractor", "v3")
    
    for idx, q in enumerate(queries, 1):
        print(f"\n--- Testing Query {idx} ---")
        print(f"Question: {q}")
        try:
            result = await run_agent([HumanMessage(content=q)], llm, tools=[], system_prompt=system_prompt)
            print(f"SQL: {result['sql']}")
            print(f"Output: {result['output'][:200]}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
