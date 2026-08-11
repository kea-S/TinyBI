import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import CONFIG_JSON_PATH
from src.utils.models import test_llm_connection, test_embedding_connection
from src.utils.rag.vector_controller import VectorController

router = APIRouter(prefix="/config", tags=["config"])

class LocalLLMConfig(BaseModel):
    model: str = ""
    base_url: str = ""

class RemoteLLMConfig(BaseModel):
    model: str = ""
    api_key: str = ""

class EmbeddingConfig(BaseModel):
    model: str = ""
    base_url: str = ""
    api_key: str = ""

class ConfigPayload(BaseModel):
    active_llm: str = "local"
    local_llm: LocalLLMConfig
    remote_llm: RemoteLLMConfig
    embedding: EmbeddingConfig


def _load_config():
    if not os.path.exists(CONFIG_JSON_PATH):
        return None
    with open(CONFIG_JSON_PATH, "r") as f:
        return json.load(f)

def load_config_to_env():
    cfg = _load_config()
    if cfg:
        local_llm = cfg.get("local_llm", {})
        if local_llm.get("base_url"):
            os.environ["OLLAMA_BASE_URL"] = local_llm["base_url"]
            
        remote_llm = cfg.get("remote_llm", {})
        if remote_llm.get("api_key"):
            os.environ["GROQ_API_KEY"] = remote_llm["api_key"]
            
        embedding = cfg.get("embedding", {})
        if embedding.get("base_url"):
            os.environ["LOCAL_API_BASE"] = embedding["base_url"]
        if embedding.get("api_key"):
            os.environ["JINA_API_KEY"] = embedding["api_key"]
            
        active_llm = cfg.get("active_llm", "local")
        if active_llm == "local":
            os.environ["TINYBI_MODEL"] = local_llm.get("model", "")
        else:
            os.environ["TINYBI_MODEL"] = remote_llm.get("model", "")
            
        os.environ["TINYBI_EMBEDDING_MODEL"] = embedding.get("model", "")
        os.environ["TINYBI_ACTIVE_LLM_TYPE"] = active_llm

@router.get("")
def get_config():
    cfg = _load_config()
    if cfg is None:
        return {"configured": False, "config": None}
    return {"configured": True, "config": cfg}

@router.post("")
def save_config(payload: ConfigPayload):
    old_cfg = _load_config()
    old_ollama_base = os.getenv("OLLAMA_BASE_URL")
    old_groq_key = os.getenv("GROQ_API_KEY")
    old_local_api_base = os.getenv("LOCAL_API_BASE")
    old_jina_key = os.getenv("JINA_API_KEY")

    if payload.local_llm.base_url:
        os.environ["OLLAMA_BASE_URL"] = payload.local_llm.base_url
    if payload.remote_llm.api_key:
        os.environ["GROQ_API_KEY"] = payload.remote_llm.api_key
    if payload.embedding.base_url:
        os.environ["LOCAL_API_BASE"] = payload.embedding.base_url
    if payload.embedding.api_key:
        os.environ["JINA_API_KEY"] = payload.embedding.api_key

    errors = []
    
    if payload.active_llm == "local":
        if payload.local_llm.model:
            res = test_llm_connection(payload.local_llm.model, is_local=True)
            if not res["success"]:
                errors.append(f"Local LLM Error: {res['error']}")
    else:
        if payload.remote_llm.model:
            res = test_llm_connection(payload.remote_llm.model, is_local=False)
            if not res["success"]:
                errors.append(f"Remote LLM Error: {res['error']}")

    if payload.embedding.model:
        res = test_embedding_connection(
            payload.embedding.model,
            base_url=payload.embedding.base_url,
            api_key=payload.embedding.api_key
        )
        if not res["success"]:
            errors.append(f"Embedding Error: {res['error']}")

    if errors:
        if old_ollama_base: os.environ["OLLAMA_BASE_URL"] = old_ollama_base
        if old_groq_key: os.environ["GROQ_API_KEY"] = old_groq_key
        if old_local_api_base: os.environ["LOCAL_API_BASE"] = old_local_api_base
        if old_jina_key: os.environ["JINA_API_KEY"] = old_jina_key
        
        raise HTTPException(status_code=400, detail=" | ".join(errors))
    
    os.makedirs(os.path.dirname(CONFIG_JSON_PATH), exist_ok=True)
    with open(CONFIG_JSON_PATH, "w") as f:
        json.dump(payload.model_dump(), f, indent=2)
        
    load_config_to_env()

    # Automatically re-embed vector index if embedding model/config changed
    embedding_changed = False
    if old_cfg is None:
        embedding_changed = True
    else:
        old_emb = old_cfg.get("embedding", {})
        if old_emb.get("model") != payload.embedding.model or old_emb.get("base_url") != payload.embedding.base_url:
            embedding_changed = True

    if embedding_changed and payload.embedding.model:
        try:
            controller = VectorController(
                payload.embedding.model,
                base_url=payload.embedding.base_url,
                api_key=payload.embedding.api_key,
            )
            entries = controller.get_current_index_entries()
            if entries:
                controller.batch_insert_index_entries(entries)
        except Exception as e:
            print(f"Auto re-embedding skipped or failed: {e}")

    return {"success": True}
