from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_GPT_4o = "gpt-4o"
REMOTE_GPT_OSS_LARGE = "openai/gpt-oss-120b"
LOCAL_GEMMA3 = "gemma3:4b"
LOCAL_LLAMA = "llama3.2:3b"
LOCAL_PHI4 = "phi4-mini:3.8b"
LOCAL_GRANITE4 = "granite4:3b"

LOCAL_BIG_LLAMA = "llama3.1:8b"
LOCAL_BIG_GRANITE = "granite3.1-dense:8b"
LOCAL_BIG_GRANITE_NEW = "granite3.3:8b"
LOCAL_BIG_QWEN = "qwen2.5:7b"


NOMIC_EMBED_TEXT = "nomic-embed-text"
QWEN3_EMBEDDING = "qwen3-embedding:0.6b"
BGE_M3 = "bge-m3:567m"
OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"

DEFAULT_EMBEDDING_MODEL = NOMIC_EMBED_TEXT
EMBEDDING_MODELS_BY_KEY = {
    "nomic": NOMIC_EMBED_TEXT,
    "qwen3": QWEN3_EMBEDDING,
    "bge-m3": BGE_M3,
    "openai-small": OPENAI_TEXT_EMBEDDING_3_SMALL,
}


def get_remote_llm(name: str):
    if name == REMOTE_GPT_4o:
        return ChatOpenAI(model=REMOTE_GPT_4o)
    else:
        return ChatGroq(model=REMOTE_GPT_OSS_LARGE)


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


def get_embedding_model_name_from_key(key: str) -> str:
    try:
        return EMBEDDING_MODELS_BY_KEY[key]
    except KeyError as exc:
        supported_keys = ", ".join(sorted(EMBEDDING_MODELS_BY_KEY))
        raise ValueError(
            f"Unsupported embedding model key '{key}'. Supported keys: {supported_keys}"
        ) from exc
