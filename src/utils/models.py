from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_GPT_OSS_SMALL = "openai/gpt-oss-20b"
REMOTE_GPT_5 = "gpt-5"
REMOTE_GPT_4o = "gpt-4o"

NOMIC_EMBED_TEXT = "nomic-embed-text"
QWEN3_EMBEDDING = "qwen3-embedding:0.6b"
BGE_M3 = "bge-m3:567m"
OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"


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


def get_embedding_model(name: str):
    if name in {NOMIC_EMBED_TEXT, QWEN3_EMBEDDING, BGE_M3}:
        return OllamaEmbeddings(model=name)
    if name == OPENAI_TEXT_EMBEDDING_3_SMALL:
        return OpenAIEmbeddings(model=OPENAI_TEXT_EMBEDDING_3_SMALL)

    supported_models = (
        NOMIC_EMBED_TEXT,
        QWEN3_EMBEDDING,
        BGE_M3,
        OPENAI_TEXT_EMBEDDING_3_SMALL,
    )
    raise ValueError(f"Unsupported embedding model '{name}'. Supported models: {', '.join(supported_models)}")

