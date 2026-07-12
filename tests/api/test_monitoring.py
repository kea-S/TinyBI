import pytest
import json
from unittest.mock import patch, mock_open
from fastapi.testclient import TestClient

from src.api.main import create_app

@pytest.fixture
def client():
    return TestClient(create_app())

def get_fake_eval_json():
    # 2 TinyBI queries, 1 Schema Dump query
    return {
        "results": {
            "results": [
                {
                    "provider": {"label": "TinyBI: granite4"},
                    "score": 1,
                    "success": True,
                    "latencyMs": 10000,
                    "response": {"tokenUsage": {"total": 5000}},
                    "vars": {"difficulty": "simple"}
                },
                {
                    "provider": {"label": "TinyBI: granite4"},
                    "score": 0,
                    "success": False,
                    "error": "Python score 0 is less than threshold",
                    "latencyMs": 20000,
                    "response": {"tokenUsage": {"total": 10000}},
                    "vars": {"difficulty": "challenging"}
                },
                {
                    "provider": {"label": "Schema Dump: granite4"},
                    "score": 0.5,
                    "success": False,
                    "error": "BinderException",
                    "latencyMs": 15000,
                    "response": {"tokenUsage": {"total": 30000}},
                    "vars": {"difficulty": "simple"}
                }
            ]
        }
    }

@patch("src.api.routes.monitoring._load_eval_data")
def test_monitoring_overview_success(mock_load, client):
    mock_load.return_value = get_fake_eval_json()
    response = client.get("/monitoring/overview")
    assert response.status_code == 200
    data = response.json()
    # Expecting aggregates for TinyBI only by default
    assert data["overallAccuracy"] == 0.5  # (1 + 0) / 2
    assert data["meanLatencyMs"] == 15000  # (10000 + 20000) / 2
    assert data["meanTokens"] == 7500      # (5000 + 10000) / 2
    assert data["totalTokens"] == 15000    # 5000 + 10000

@patch("src.api.routes.monitoring._load_eval_data")
def test_monitoring_difficulty_breakdown_success(mock_load, client):
    mock_load.return_value = get_fake_eval_json()
    response = client.get("/monitoring/difficulty-breakdown")
    assert response.status_code == 200
    data = response.json()
    # TinyBI breakdown
    assert len(data) == 2
    simple_stats = next(s for s in data if s["difficulty"] == "simple")
    assert simple_stats["accuracy"] == 1
    assert simple_stats["latencyMs"] == 10000
    assert simple_stats["tokens"] == 5000

    challenging_stats = next(s for s in data if s["difficulty"] == "challenging")
    assert challenging_stats["accuracy"] == 0
    assert challenging_stats["latencyMs"] == 20000
    assert challenging_stats["tokens"] == 10000

@patch("src.api.routes.monitoring._load_eval_data")
def test_monitoring_provider_comparison_success(mock_load, client):
    mock_load.return_value = get_fake_eval_json()
    response = client.get("/monitoring/provider-comparison")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    tinybi = next(p for p in data if p["provider"] == "TinyBI")
    assert tinybi["accuracy"] == 0.5
    assert tinybi["tokens"] == 7500

    schema_dump = next(p for p in data if p["provider"] == "Schema Dump")
    assert schema_dump["accuracy"] == 0.5
    assert schema_dump["tokens"] == 30000

@patch("src.api.routes.monitoring._load_eval_data")
def test_monitoring_endpoints_missing_file(mock_load, client):
    # Simulate file missing or empty by returning None or empty data
    mock_load.return_value = None
    
    res1 = client.get("/monitoring/overview")
    assert res1.status_code == 200
    assert res1.json()["totalTokens"] == 0

    res2 = client.get("/monitoring/difficulty-breakdown")
    assert res2.status_code == 200
    assert res2.json() == []

    res3 = client.get("/monitoring/provider-comparison")
    assert res3.status_code == 200
    assert res3.json() == []

@patch("src.api.routes.monitoring._load_eval_data")
def test_monitoring_difficulty_segregated_success(mock_load, client):
    mock_load.return_value = get_fake_eval_json()
    response = client.get("/monitoring/difficulty-segregated")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # 2 for TinyBI (simple, challenging) + 1 for Schema Dump (simple)
    
    tinybi_simple = next(s for s in data if s["provider"] == "TinyBI" and s["difficulty"] == "simple")
    assert tinybi_simple["accuracy"] == 1
    assert tinybi_simple["tokens"] == 5000

    schema_dump_simple = next(s for s in data if s["provider"] == "Schema Dump" and s["difficulty"] == "simple")
    assert schema_dump_simple["accuracy"] == 0.5
    assert schema_dump_simple["tokens"] == 30000
