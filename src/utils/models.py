import os
import json
import requests
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter

from dotenv import load_dotenv
from src.config import CONFIG_JSON_PATH

load_dotenv()

def resolve_docker_host(url: str) -> str:
    if not url:
        return url
    if os.path.exists("/.dockerenv"):
        return url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
    return url.replace("host.docker.internal", "localhost")

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
LOCAL_GRANITE4 = "granite4:3b"

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

def load_saved_config() -> dict | None:
    if CONFIG_JSON_PATH.exists():
        try:
            with open(CONFIG_JSON_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def get_active_embedding_model_name() -> str:
    env_model = os.getenv("TINYBI_EMBEDDING_MODEL")
    if env_model:
        return env_model

    cfg = load_saved_config()
    if cfg:
        model = cfg.get("embedding", {}).get("model")
        if model:
            return model

    return DEFAULT_EMBEDDING_MODEL


def get_remote_llm(name: str):
    return ChatGroq(model=name)



from langchain_ollama import ChatOllama

def get_local_llm(name: str):
    use_vllm = os.getenv("TINYBI_USE_VLLM", "false").lower() == "true"
    
    if use_vllm:
        base_url = os.getenv("TINYBI_VLLM_URL", "http://localhost:8003/v1")
        base_url = resolve_docker_host(base_url)
            
        return ChatOpenAI(
            model=name,
            base_url=base_url,
            api_key="none",
            max_retries=0
        )
    else:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        base_url = resolve_docker_host(base_url)
        ollama_host = base_url.split('/v1')[0]
        
        try:
            response = requests.get(f"{ollama_host}/", timeout=5)
            response.raise_for_status()
            if response.text.strip() != "Ollama is running":
                raise ValueError("Endpoint did not return the Ollama signature.")
        except Exception as e:
            raise ValueError(f"The provided local endpoint does not appear to be a valid Ollama instance. Details: {e}")
            
        return ChatOllama(
            model=name,
            base_url=ollama_host,
            reasoning=False
        )


def get_embedding_model(name: str = None, base_url: str = None, api_key: str = None):
    if not name:
        name = get_active_embedding_model_name()
    if base_url is None:
        base_url = os.getenv("LOCAL_API_BASE") or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            
    base_url = resolve_docker_host(base_url)
    
    is_jina = "jina" in base_url.lower() or (name and "jina" in name.lower())
    if is_jina:
        cleaned_url = base_url.rstrip("/")
        while cleaned_url.endswith("/embeddings") or cleaned_url.endswith("/v1"):
            if cleaned_url.endswith("/embeddings"):
                cleaned_url = cleaned_url[:-len("/embeddings")].rstrip("/")
            elif cleaned_url.endswith("/v1"):
                cleaned_url = cleaned_url[:-len("/v1")].rstrip("/")
        cleaned_url = f"{cleaned_url}/v1"
            
        key = api_key or os.getenv("JINA_API_KEY", "none")
        return OpenAIEmbeddings(
            model=name,
            base_url=cleaned_url,
            api_key=key,
            check_embedding_ctx_length=False
        )

    if not base_url.endswith("/v1"):
        base_url = f"{base_url.rstrip('/')}/v1"
    
    ollama_host = base_url.split('/v1')[0]
    try:
        response = requests.get(f"{ollama_host}/", timeout=5)
        response.raise_for_status()
        if response.text.strip() != "Ollama is running":
            raise ValueError("Endpoint did not return the Ollama signature.")
    except Exception as e:
        raise ValueError(f"Only Jina or Ollama endpoints are supported right now, and the provided local endpoint does not appear to be a valid Ollama instance. Details: {e}")
        
    if not base_url.endswith("/v1") and "jina" not in base_url.lower():
        base_url = f"{ollama_host}/v1"

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


def test_embedding_connection(name: str, base_url: str = None, api_key: str = None):
    try:
        model = get_embedding_model(name, base_url=base_url, api_key=api_key)
        model.embed_query("test")
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
