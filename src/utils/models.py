import os
import requests
from langchain_groq import ChatGroq
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
LOCAL_GRANITE4 = "ibm/granite4.1:3b"

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
    return ChatGroq(model=name)



from langchain_ollama import ChatOllama

def get_local_llm(name: str):
    use_vllm = os.getenv("TINYBI_USE_VLLM", "false").lower() == "true"
    
    if use_vllm:
        base_url = os.getenv("TINYBI_VLLM_URL", "http://localhost:8003/v1")
        # If running the API locally on the host Mac instead of in Docker, 
        # 'host.docker.internal' will fail DNS resolution. Translate it to localhost.
        if "host.docker.internal" in base_url and not os.path.exists("/.dockerenv"):
            base_url = base_url.replace("host.docker.internal", "localhost")
            
        return ChatOpenAI(
            model=name,
            base_url=base_url,
            api_key="none", # Required by OpenAI client, but ignored by local endpoints
            max_retries=0
        )
    else:
        # User requested to stick with ChatOllama
        return ChatOllama(
            model=name,
            reasoning=False
        )


def get_embedding_model(name: str, base_url: str = None):
    if base_url is None:
        base_url = os.getenv("LOCAL_API_BASE", "http://127.0.0.1:11434/v1")
    
    if "jina" in base_url.lower():
        return OpenAIEmbeddings(
            model=name,
            base_url=base_url,
            api_key=os.getenv("JINA_API_KEY", "none"),
            check_embedding_ctx_length=False
        )
    
    ollama_host = base_url.split('/v1')[0]
    try:
        response = requests.get(f"{ollama_host}/", timeout=5)
        response.raise_for_status()
        if response.text.strip() != "Ollama is running":
            raise ValueError("Endpoint did not return the Ollama signature.")
    except Exception as e:
        raise ValueError(f"Only Jina or Ollama endpoints are supported right now, and the provided local endpoint does not appear to be a valid Ollama instance. Details: {e}")
        
    return OpenAIEmbeddings(
        model=name,
        base_url=base_url,
        api_key="none",
        check_embedding_ctx_length=False
    )


def get_embedding_model_name_from_key(key: str) -> str:
    try:
        return EMBEDDING_MODELS_BY_KEY[key]
    except KeyError as exc:
        supported_keys = ", ".join(sorted(EMBEDDING_MODELS_BY_KEY))
        raise ValueError(
            f"Unsupported embedding model key '{key}'. Supported keys: {supported_keys}"
        ) from exc


def test_llm_connection(name: str, is_local: bool = True):
    try:
        if is_local:
            llm = get_local_llm(name)
        else:
            llm = get_remote_llm(name)
            
        from langchain_core.messages import HumanMessage
        llm.invoke([HumanMessage(content="Hi")])
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_embedding_connection(name: str, base_url: str = None):
    try:
        model = get_embedding_model(name, base_url)
        model.embed_query("test")
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
