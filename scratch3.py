import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent import run_agent, get_model_node
from src.tools.query_tool import make_query_tool
from src.utils.models import get_local_llm, LOCAL_GRANITE4
from src.utils.prompts import EXTRACTOR_PROMPT

async def main():
    llm = get_local_llm(LOCAL_GRANITE4)
    tools = [make_query_tool(llm)]
    messages = [HumanMessage(content="Show me the average buyer waiting time by provider")]
    
    # We will invoke llm_with_tools without tool_choice="any"
    llm_with_tools = llm.bind_tools(tools)
    
    system_message = SystemMessage(content=EXTRACTOR_PROMPT)
    all_messages = [system_message] + messages
    
    response = await llm_with_tools.ainvoke(all_messages)
    print("RAW RESPONSE:")
    print(repr(response))

if __name__ == "__main__":
    asyncio.run(main())
