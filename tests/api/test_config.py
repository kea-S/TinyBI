import os
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api.main import app

client = TestClient(app)

DUMMY_PAYLOAD = {
  "active_llm": "local",
  "local_llm": {
    "model": "granite4.1:3b",
    "base_url": "http://127.0.0.1:11434"
  },
  "remote_llm": {
    "model": "llama-3.1-8b-instant",
    "api_key": "gsk_..."
  },
  "embedding": {
    "model": "qwen3-embedding:0.6b",
    "base_url": "http://127.0.0.1:11434",
    "api_key": ""
  }
}

@pytest.fixture
def mock_config_path(tmp_path):
    config_file = tmp_path / "config.json"
    with patch("src.api.routes.config.CONFIG_JSON_PATH", str(config_file)):
        yield config_file


def test_get_config_no_file(mock_config_path):
    response = client.get("/config/")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["config"] is None


@patch("src.api.routes.config.test_llm_connection")
@patch("src.api.routes.config.test_embedding_connection")
def test_post_config_valid(mock_embed, mock_llm, mock_config_path):
    mock_llm.return_value = {"success": True, "error": None}
    mock_embed.return_value = {"success": True, "error": None}

    response = client.post("/config/", json=DUMMY_PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"success": True}

    # Verify file written
    assert mock_config_path.exists()
    with open(mock_config_path) as f:
        saved = json.load(f)
    assert saved == DUMMY_PAYLOAD


@patch("src.api.routes.config.test_llm_connection")
@patch("src.api.routes.config.test_embedding_connection")
def test_post_config_invalid_connection(mock_embed, mock_llm, mock_config_path):
    mock_llm.return_value = {"success": False, "error": "Connection timed out"}
    mock_embed.return_value = {"success": True, "error": None}

    response = client.post("/config/", json=DUMMY_PAYLOAD)
    assert response.status_code == 400
    assert "Connection timed out" in response.text
    assert not mock_config_path.exists()


def test_get_config_with_file(mock_config_path):
    with open(mock_config_path, "w") as f:
        json.dump(DUMMY_PAYLOAD, f)

    response = client.get("/config/")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["config"] == DUMMY_PAYLOAD


def test_load_config_to_env(mock_config_path, monkeypatch):
    with open(mock_config_path, "w") as f:
        json.dump(DUMMY_PAYLOAD, f)

    from src.api.routes.config import load_config_to_env
    
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("TINYBI_MODEL", raising=False)
    monkeypatch.delenv("TINYBI_ACTIVE_LLM_TYPE", raising=False)

    load_config_to_env()

    assert os.environ["OLLAMA_BASE_URL"] == "http://127.0.0.1:11434"
    assert os.environ["TINYBI_MODEL"] == "granite4.1:3b"
    assert os.environ["TINYBI_ACTIVE_LLM_TYPE"] == "local"
