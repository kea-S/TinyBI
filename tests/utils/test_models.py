import os
import json
import socket
from urllib.parse import urlparse

import pytest
from langchain_openai import OpenAIEmbeddings

from src.utils.models import (
    BGE_M3,
    NOMIC_EMBED_TEXT,
    OPENAI_TEXT_EMBEDDING_3_SMALL,
    REMOTE_GPT_OSS_LARGE,
    # REMOTE_GPT_4o,
    QWEN3_EMBEDDING,
    REMOTE_LLAMA_8B,
    LOCAL_GRANITE4,
)

from src.utils.models import get_embedding_model, get_remote_llm, get_local_llm

from dotenv import load_dotenv


load_dotenv()


REMOTE_MODEL_ENV_VARS = {
    # REMOTE_GPT_4o: "OPENAI_API_KEY",
    REMOTE_GPT_OSS_LARGE: "GROQ_API_KEY",
    REMOTE_LLAMA_8B: "GROQ_API_KEY",
}

REMOTE_MODEL_HOSTS = {
    # REMOTE_GPT_4o: ("api.openai.com", 443),
    REMOTE_GPT_OSS_LARGE: ("api.groq.com", 443),
    REMOTE_LLAMA_8B: ("api.groq.com", 443),
}


def _ollama_is_reachable() -> bool:
    endpoint = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    hostname = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434

    try:
        with socket.create_connection((hostname, port), timeout=1):
            return True
    except OSError:
        return False


def _host_is_reachable(hostname: str, port: int) -> bool:
    try:
        with socket.create_connection((hostname, port), timeout=1):
            return True
    except OSError:
        return False


def _skip_if_runtime_unavailable(model_name: str, local: bool) -> None:
    if local:
        if not _ollama_is_reachable():
            pytest.skip("Ollama is not reachable at OLLAMA_HOST or http://127.0.0.1:11434")
        return

    required_env_var = REMOTE_MODEL_ENV_VARS[model_name]
    if not os.getenv(required_env_var):
        pytest.skip(f"{required_env_var} is not set")

    host, port = REMOTE_MODEL_HOSTS[model_name]
    if not _host_is_reachable(host, port):
        pytest.skip(f"{host}:{port} is not reachable")


@pytest.mark.integration
@pytest.mark.parametrize(
    "model_name, expected_type, expected_model",
    [
        (NOMIC_EMBED_TEXT, OpenAIEmbeddings, NOMIC_EMBED_TEXT),
        (QWEN3_EMBEDDING, OpenAIEmbeddings, QWEN3_EMBEDDING),
        (BGE_M3, OpenAIEmbeddings, BGE_M3),
        (OPENAI_TEXT_EMBEDDING_3_SMALL, OpenAIEmbeddings, OPENAI_TEXT_EMBEDDING_3_SMALL),
    ],
)
def test_get_embedding_model_returns_expected_langchain_wrapper(model_name, expected_type, expected_model):
    embedding_model = get_embedding_model(model_name)

    assert isinstance(embedding_model, expected_type)
    assert embedding_model.model == expected_model





@pytest.mark.integration
@pytest.mark.parametrize(
    "model_name, local",
    [
        (NOMIC_EMBED_TEXT, True),
        (QWEN3_EMBEDDING, True),
        (BGE_M3, True),
    ],
)
def test_langchain_embedding_call(model_name: str, local: bool, monkeypatch):
    if local:
        monkeypatch.setenv("LOCAL_API_BASE", "http://localhost:11434/v1")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    
    _skip_if_runtime_unavailable(model_name, local)

    embedding_model = get_embedding_model(model_name)

    try:
        vector = embedding_model.embed_query("Hello")
        assert isinstance(vector, list)
        assert len(vector) > 0
    except Exception as e:
        pytest.fail(f"LANGCHAIN embedding model '{model_name}' call failed: {e}")


@pytest.mark.integration
@pytest.mark.parametrize("model_name, local", [
    (LOCAL_GRANITE4, True),
    # (REMOTE_GPT_4o, False),
    (REMOTE_GPT_OSS_LARGE, False),
    (REMOTE_LLAMA_8B, False),
])
def test_langchain_llm_call(model_name, local: bool, monkeypatch):
    if local:
        monkeypatch.setenv("LOCAL_API_BASE", "http://localhost:11434/v1")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        
    _skip_if_runtime_unavailable(model_name, local)

    llm = (get_local_llm(model_name)
           if local else get_remote_llm(model_name))

    try:
        response = llm.invoke("Hello").text
        assert response is not None and len(str(response)) > 0
    except Exception as e:
        pytest.fail(f"LANGCHAIN model '{model_name}' call failed: {e}")


def test_get_embedding_model_jina():
    # Test that /embeddings suffix is trimmed so OpenAI client doesn't append it twice
    model = get_embedding_model("jina-embeddings-v5-text-small", base_url="https://api.jina.ai/v1/embeddings", api_key="jina_test_key")
    assert isinstance(model, OpenAIEmbeddings)
    assert model.openai_api_base == "https://api.jina.ai/v1"
    assert model.openai_api_key.get_secret_value() == "jina_test_key"

    # Test that base_url without /v1 appends /v1
    model2 = get_embedding_model("jina-embeddings-v3", base_url="https://api.jina.ai", api_key="jina_test_key2")
    assert model2.openai_api_base == "https://api.jina.ai/v1"
    assert model2.openai_api_key.get_secret_value() == "jina_test_key2"


def test_get_embedding_model_prioritizes_local_api_base_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("LOCAL_API_BASE", "https://api.jina.ai/v1/embeddings")
    monkeypatch.setenv("JINA_API_KEY", "env_jina_key")

    model = get_embedding_model("jina-embeddings-v5-text-small")
    assert model.openai_api_base == "https://api.jina.ai/v1"
    assert model.openai_api_key.get_secret_value() == "env_jina_key"


def test_get_active_embedding_model_name_from_config_json(tmp_path, monkeypatch):
    from src.utils.models import get_active_embedding_model_name
    mock_cfg = tmp_path / "config.json"
    with open(mock_cfg, "w") as f:
        json.dump({"embedding": {"model": "jina-embeddings-v5-text-small"}}, f)

    monkeypatch.setattr("src.utils.models.CONFIG_JSON_PATH", mock_cfg)
    monkeypatch.delenv("TINYBI_EMBEDDING_MODEL", raising=False)

    assert get_active_embedding_model_name() == "jina-embeddings-v5-text-small"



