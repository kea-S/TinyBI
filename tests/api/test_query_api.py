import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api.main import create_app

@pytest.fixture
def client():
    return TestClient(create_app())

def test_query_endpoint_success(client):
    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})
    fake_result = {
        "output": "Here are the providers.",
        "sql": "SELECT provider, SUM(order_value) FROM orders GROUP BY provider",
        "data": fake_df.to_dict(orient="records")
    }

    async def mock_run_agent(messages, llm, tools, system_prompt):
        return fake_result

    with patch("src.api.routes.query.run_agent", mock_run_agent):
        response = client.post("/query", json={
            "messages": [{"role": "user", "content": "show me providers"}]
        })

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Here are the providers."
    assert body["sql"] == "SELECT provider, SUM(order_value) FROM orders GROUP BY provider"
    assert len(body["data"]) == 1

def test_query_endpoint_no_data(client):
    fake_result = {
        "output": "I couldn't find any data.",
        "sql": None,
        "data": None
    }

    async def mock_run_agent(messages, llm, tools, system_prompt):
        return fake_result

    with patch("src.api.routes.query.run_agent", mock_run_agent):
        response = client.post("/query", json={
            "messages": [{"role": "user", "content": "hello"}]
        })

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "I couldn't find any data."
    assert body["sql"] is None
    assert body["data"] is None

def test_query_endpoint_error(client):
    async def mock_run_agent_fail(messages, llm, tools, system_prompt):
        raise RuntimeError("Agent failed")

    with patch("src.api.routes.query.run_agent", mock_run_agent_fail):
        response = client.post("/query", json={
            "messages": [{"role": "user", "content": "error"}]
        })

    assert response.status_code == 500
    assert "Agent failed" in response.json()["detail"]

def test_query_config_endpoint(client):
    response = client.get("/query/config")
    assert response.status_code == 200
    body = response.json()
    assert body["llm"] == "ibm/granite4.1:3b"
    assert body["embedding"] == "qwen3-embedding:0.6b"

def test_query_endpoint_keeps_history(client):
    fake_result = {
        "output": "Sure.",
        "sql": None,
        "data": None
    }

    async def mock_run_agent(messages, llm, tools, system_prompt):
        # We assert that history is NOT dropped
        assert len(messages) == 3
        assert messages[-1].content == "what about for Singapore?"
        return fake_result

    with patch("src.api.routes.query.run_agent", mock_run_agent):
        response = client.post("/query", json={
            "messages": [
                {"role": "user", "content": "average buyer waiting time"},
                {"role": "assistant", "content": "The average waiting time is 2 days."},
                {"role": "user", "content": "what about for Singapore?"}
            ]
        })

    assert response.status_code == 200
