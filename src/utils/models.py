import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter

from dotenv import load_dotenv


load_dotenv()

# framework used
LANGCHAIN = "langchain"

# models to be experimented with
REMOTE_GPT_4o = "gpt-4o"
REMOTE_GPT_OSS_LARGE = "openai/gpt-oss-120b"
REMOTE_DEEPSEEK = "deepseek/deepseek-v4-flash"
REMOTE_GRANITE = "ibm-granite/granite-4.1-8b"
REMOTE_LLAMA_8B = "llama-3.1-8b-instant"
LOCAL_GEMMA3 = "gemma3:4b"
LOCAL_GEMMA4 = "gemma4:e4b"
LOCAL_LLAMA = "llama3.2:3b"
LOCAL_PHI4 = "phi4-mini:3.8b"
LOCAL_GRANITE4 = "ibm-granite/granite-4.1-3b"

LOCAL_BIG_LLAMA = "llama3.1:8b"
LOCAL_BIG_GRANITE = "granite3.1-dense:8b"
LOCAL_BIG_GRANITE_NEW = "granite3.3:8b"
LOCAL_BIG_QWEN = "qwen2.5:7b"


NOMIC_EMBED_TEXT = "nomic-embed-text"
QWEN3_EMBEDDING = "qwen3-embedding:0.6b"
BGE_M3 = "bge-m3:567m"
OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"

DEFAULT_EMBEDDING_MODEL = QWEN3_EMBEDDING
EMBEDDING_MODELS_BY_KEY = {
    "nomic": NOMIC_EMBED_TEXT,
    "qwen3": QWEN3_EMBEDDING,
    "bge-m3": BGE_M3,
    "openai-small": OPENAI_TEXT_EMBEDDING_3_SMALL,
}


def get_remote_llm(name: str):
    if name == REMOTE_GPT_4o:
        return ChatOpenAI(model=REMOTE_GPT_4o)
    elif name == REMOTE_LLAMA_8B:
        return ChatGroq(model=REMOTE_LLAMA_8B)
    elif name == REMOTE_DEEPSEEK:
        return ChatOpenRouter(model=REMOTE_DEEPSEEK)
    elif name == REMOTE_GRANITE:
        return ChatOpenRouter(model=REMOTE_DEEPSEEK, openrouter_provider={"allow_fallbacks": True})
    else:
        return ChatGroq(model=REMOTE_GPT_OSS_LARGE)


def get_local_llm(name: str):
    use_vllm = os.getenv("TINYBI_USE_VLLM", "false").lower() == "true"
    if use_vllm:
        vllm_url = os.getenv("TINYBI_VLLM_URL", "http://localhost:8003/v1")
        return ChatOpenAI(
            model=name,
            base_url=vllm_url,
            api_key="none"
        )

    return ChatOllama(
        model=name,
        reasoning=False
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


