import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.main import create_app

@pytest.fixture
def client():
    return TestClient(create_app())

@pytest.mark.anyio
async def test_query_endpoint_success(client, monkeypatch):
    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})
    fake_result = {
        "output": "Here are the providers.",
        "sql": "SELECT provider, SUM(order_value) FROM orders GROUP BY provider",
        "data": fake_df.to_dict(orient="records")
    }

    async def mock_run_agent(messages, llm):
        return fake_result

    monkeypatch.setattr("src.api.routes.query.run_agent", mock_run_agent)

    response = client.post("/query", json={
        "messages": [{"role": "user", "content": "show me providers"}]
    })

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Here are the providers."
    assert body["sql"] == "SELECT provider, SUM(order_value) FROM orders GROUP BY provider"
    assert len(body["data"]) == 1

@pytest.mark.anyio
async def test_query_endpoint_no_data(client, monkeypatch):
    fake_result = {
        "output": "I couldn't find any data.",
        "sql": None,
        "data": None
    }

    async def mock_run_agent(messages, llm):
        return fake_result

    monkeypatch.setattr("src.api.routes.query.run_agent", mock_run_agent)

    response = client.post("/query", json={
        "messages": [{"role": "user", "content": "hello"}]
    })

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "I couldn't find any data."
    assert body["sql"] is None
    assert body["data"] is None

@pytest.mark.anyio
async def test_query_endpoint_error(client, monkeypatch):
    async def mock_run_agent_fail(messages, llm):
        raise RuntimeError("Agent failed")

    monkeypatch.setattr("src.api.routes.query.run_agent", mock_run_agent_fail)

    response = client.post("/query", json={
        "messages": [{"role": "user", "content": "error"}]
    })

    assert response.status_code == 500
    assert "Agent failed" in response.json()["detail"]
