import pytest
from unittest.mock import patch, MagicMock
from src.utils.models import get_local_llm, LOCAL_GRANITE4

@pytest.fixture
def mock_env_vllm(monkeypatch):
    monkeypatch.setenv("TINYBI_USE_VLLM", "true")
    monkeypatch.setenv("TINYBI_VLLM_URL", "http://localhost:8003/v1")

@pytest.mark.parametrize("model_name", [LOCAL_GRANITE4, "granite-3.1-8b"])
def test_get_local_llm_routes_to_vllm(mock_env_vllm, model_name, monkeypatch):
    """
    Test that when TINYBI_USE_VLLM is true, get_local_llm returns a ChatOpenAI 
    instance configured for the local vLLM endpoint.
    """
    with patch("src.utils.models.ChatOpenAI") as mock_chat_openai:
        get_local_llm(model_name)
        
        # Verify ChatOpenAI was called with the local vLLM config
        mock_chat_openai.assert_called_once()
        args, kwargs = mock_chat_openai.call_args
        assert kwargs["base_url"] == "http://localhost:8003/v1"
        assert kwargs["model"] == model_name
        # api_key should be dummy for local vLLM
        assert "api_key" in kwargs

def test_get_local_llm_falls_back_to_ollama_when_vllm_disabled(monkeypatch):
    """
    Test that when TINYBI_USE_VLLM is false (or not set), it still uses ChatOllama.
    """
    monkeypatch.delenv("TINYBI_USE_VLLM", raising=False)
    
    with patch("src.utils.models.ChatOllama") as mock_chat_ollama:
        get_local_llm("test-model")
        mock_chat_ollama.assert_called_once_with(
            model="test-model",
            base_url="http://127.0.0.1:11434",
            reasoning=False
        )
