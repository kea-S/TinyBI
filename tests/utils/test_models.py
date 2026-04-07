import os
import socket
from urllib.parse import urlparse

import pytest
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.utils.models import (
    BGE_M3,
    NOMIC_EMBED_TEXT,
    OPENAI_TEXT_EMBEDDING_3_SMALL,
    REMOTE_GPT_OSS_LARGE,
    REMOTE_GPT_4o,
    QWEN3_EMBEDDING,
)

from src.utils.models import get_embedding_model, get_remote_llm, get_local_llm

from dotenv import load_dotenv


load_dotenv()


REMOTE_MODEL_ENV_VARS = {
    REMOTE_GPT_4o: "OPENAI_API_KEY",
    REMOTE_GPT_OSS_LARGE: "GROQ_API_KEY",
}

REMOTE_MODEL_HOSTS = {
    REMOTE_GPT_4o: ("api.openai.com", 443),
    REMOTE_GPT_OSS_LARGE: ("api.groq.com", 443),
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
        (NOMIC_EMBED_TEXT, OllamaEmbeddings, NOMIC_EMBED_TEXT),
        (QWEN3_EMBEDDING, OllamaEmbeddings, QWEN3_EMBEDDING),
        (BGE_M3, OllamaEmbeddings, BGE_M3),
        (OPENAI_TEXT_EMBEDDING_3_SMALL, OpenAIEmbeddings, OPENAI_TEXT_EMBEDDING_3_SMALL),
    ],
)
def test_get_embedding_model_returns_expected_langchain_wrapper(model_name, expected_type, expected_model):
    embedding_model = get_embedding_model(model_name)

    assert isinstance(embedding_model, expected_type)
    assert embedding_model.model == expected_model


def test_get_embedding_model_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unsupported embedding model"):
        get_embedding_model("unknown-embedding-model")


@pytest.mark.integration
@pytest.mark.parametrize(
    "model_name, local",
    [
        (NOMIC_EMBED_TEXT, True),
        (QWEN3_EMBEDDING, True),
        (BGE_M3, True),
    ],
)
def test_langchain_embedding_call(model_name: str, local: bool):
    _skip_if_runtime_unavailable(REMOTE_GPT_4o if not local else model_name, local)

    embedding_model = get_embedding_model(model_name)

    try:
        vector = embedding_model.embed_query("Hello")
        assert isinstance(vector, list)
        assert len(vector) > 0
    except Exception as e:
        pytest.fail(f"LANGCHAIN embedding model '{model_name}' call failed: {e}")


@pytest.mark.integration
@pytest.mark.parametrize("model_name, local", [
    (REMOTE_GPT_4o, False),
    (REMOTE_GPT_OSS_LARGE, False),
])
def test_langchain_llm_call(model_name, local: bool):
    _skip_if_runtime_unavailable(model_name, local)

    llm = (get_local_llm(model_name)
           if local else get_remote_llm(model_name))

    try:
        response = llm.invoke("Hello").text
        assert response is not None and len(str(response)) > 0
    except Exception as e:
        pytest.fail(f"LANGCHAIN model '{model_name}' call failed: {e}")
