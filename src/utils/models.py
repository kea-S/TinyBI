from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_GPT_4o = "gpt-4o"
LOCAL_QWEN3_5 = "qwen2.5-coder:3b"
LOCAL_GEMMA3 = "gemma3:4b"
LOCAL_LLAMA = "llama3.2:3b"


def get_remote_llm(name: str):
    if name == REMOTE_GPT_4o:
        return ChatOpenAI(model=REMOTE_GPT_4o)


def get_local_llm(name: str):
    return ChatOllama(
        model=name,
        reasoning=False
    )
