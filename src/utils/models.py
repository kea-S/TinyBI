from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_GPT_OSS_SMALL = "openai/gpt-oss-20b"
REMOTE_GPT_5 = "gpt-5"
REMOTE_GPT_4o = "gpt-4o"
LOCAL_LLAMA3 = "llama3.1:latest"


def get_remote_llm(name: str):
    if name == REMOTE_GPT_5:
        return ChatOpenAI(model=REMOTE_GPT_5)
    if name == REMOTE_GPT_4o:
        return ChatOpenAI(model=REMOTE_GPT_4o)
    else:
        return ChatGroq(model=REMOTE_GPT_OSS_SMALL)


def get_local_llm(name: str):
    return ChatOllama(
        model=name
    )
