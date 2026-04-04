import os
import socket
from urllib.parse import urlparse

import pytest

from src.utils.models import (
    REMOTE_GPT_OSS_SMALL,
    REMOTE_GPT_5,
    REMOTE_GPT_4o,
    LOCAL_LLAMA3,
)

from src.utils.models import get_remote_llm, get_local_llm

from dotenv import load_dotenv


load_dotenv()


REMOTE_MODEL_ENV_VARS = {
    REMOTE_GPT_5: "OPENAI_API_KEY",
    REMOTE_GPT_4o: "OPENAI_API_KEY",
    REMOTE_GPT_OSS_SMALL: "GROQ_API_KEY",
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


def _skip_if_runtime_unavailable(model_name: str, local: bool) -> None:
    if local:
        if not _ollama_is_reachable():
            pytest.skip("Ollama is not reachable at OLLAMA_HOST or http://127.0.0.1:11434")
        return

    required_env_var = REMOTE_MODEL_ENV_VARS[model_name]
    if not os.getenv(required_env_var):
        pytest.skip(f"{required_env_var} is not set")


@pytest.mark.integration
@pytest.mark.parametrize("model_name, local", [
    (REMOTE_GPT_5, False),
    (REMOTE_GPT_4o, False),
    (REMOTE_GPT_OSS_SMALL, False),
    (LOCAL_LLAMA3, True),
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
