from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_LLAMA3 = "llama-3.3-70b-versatile"
REMOTE_QWEN = "qwen/qwen3-32b"   # mixtral is deprecated
REMOTE_GPT_OSS_SMALL = "openai/gpt-oss-20b"
REMOTE_GPT_OSS_LARGE = "openai/gpt-oss-120b"

REMOTE_JUDGE = "gpt-5"

REMOTE_OPENAI = "gpt-5"

LOCAL_LLAMA3 = "llama3.1:latest"


def get_remote_llm(name: str):
    if name == REMOTE_OPENAI:
        return ChatOpenAI(model=REMOTE_OPENAI)
    if name == REMOTE_JUDGE:
        return ChatOpenAI(model=REMOTE_JUDGE)
    else:
        return ChatGroq(model=name)


def get_local_llm(name: str):
    return ChatOllama(
        model=name
    )
