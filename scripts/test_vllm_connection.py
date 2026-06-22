import os
import asyncio
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_vllm():
    use_vllm = os.getenv("TINYBI_USE_VLLM", "false").lower() == "true"
    vllm_url = os.getenv("TINYBI_VLLM_URL", "http://localhost:8003/v1")
    model_name = "ibm-granite/granite-4.1-3b"
    
    print(f"USE_VLLM: {use_vllm}")
    print(f"VLLM_URL: {vllm_url}")
    print(f"MODEL_NAME: {model_name}")
    
    llm = ChatOpenAI(
        model=model_name,
        base_url=vllm_url,
        api_key="none"
    )
    
    try:
        response = await llm.ainvoke("Hi")
        print("Success!")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_vllm())
