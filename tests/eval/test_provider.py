import json
import logging
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eval.provider import call_api


@pytest.fixture
def mock_config():
    return {
        "config": {
            "model_name": "test-model",
            "local": True,
            "agent_type": "tinybi"
        }
    }


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_log_capture_validation(mock_run_agent, mock_get_llm, mock_config):
    # Mock successful agent run
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }
    
    # We simulate a log emission during the agent run
    async def mock_run_agent_side_effect(*args, **kwargs):
        logger = logging.getLogger("src.agent")
        logger.info("Test SQL Query")
        return mock_run_agent.return_value
        
    mock_run_agent.side_effect = mock_run_agent_side_effect

    result = await call_api("Test prompt", mock_config, {})
    
    # Assert output contains the captured log
    assert "Test SQL Query" in result["output"], "The captured logs were not appended to the output JSON."


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_graceful_error_suppression(mock_run_agent, mock_get_llm, mock_config):
    # Mock an LLM crash/timeout
    mock_run_agent.side_effect = ValueError("Mock Timeout")
    
    # This should not raise an exception, but catch it and return {"error": ...}
    result = await call_api("Test prompt", mock_config, {})
    
    assert "error" in result, "The exception was not gracefully caught into the 'error' key."
    assert "ValueError: Mock Timeout" in result["error"]
    assert result["output"] == result["error"]


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_metadata_integrity(mock_run_agent, mock_get_llm, mock_config):
    # Mock successful agent run
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }

    result = await call_api("Test prompt", mock_config, {})
    
    assert "metadata" in result
    assert result["metadata"]["model_name"] == "test-model"
    assert result["metadata"]["parsed_sql"] == "SELECT * FROM test"
    assert "tokenUsage" in result
    assert result["tokenUsage"]["total"] == 30


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_pretty_formatter_candidate_entries(mock_run_agent, mock_get_llm, mock_config):
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }
    
    candidate_dict = {
        "subject_entries": [
            {
                "entry": {
                    "entry_id": 1,
                    "table_name": "orders",
                    "column_name": "customer_id",
                    "source_key": "orders.customer_id",
                    "statistical_type": "identifier",
                    "description": "Unique identifier for customer"
                },
                "score": 0.95
            }
        ],
        "metric_entries": [],
        "filter_entries": []
    }
    
    async def mock_run_agent_side_effect(*args, **kwargs):
        logger = logging.getLogger("src.agent")
        logger.info(f"Candidate entries: {candidate_dict}")
        return mock_run_agent.return_value
        
    mock_run_agent.side_effect = mock_run_agent_side_effect

    result = await call_api("Test prompt", mock_config, {})
    output = result["output"]
    
    assert "Columns matched: >>> orders.customer_id <<<" in output
    assert ">>> orders.customer_id <<< (similarity: `0.950`) — *Unique identifier for customer*" in output


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_pretty_formatter_final_entries(mock_run_agent, mock_get_llm, mock_config):
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }
    
    final_dict = {
        "subject_entries": [
            {
                "entry_id": 1,
                "table_name": "orders",
                "column_name": "customer_id",
                "source_key": "orders.customer_id",
                "statistical_type": "identifier",
                "description": "Unique identifier for customer"
            }
        ],
        "metric_entry": None,
        "filter_entries": []
    }
    
    async def mock_run_agent_side_effect(*args, **kwargs):
        logger = logging.getLogger("src.agent")
        logger.info(f"Final entries: {final_dict}")
        return mock_run_agent.return_value
        
    mock_run_agent.side_effect = mock_run_agent_side_effect

    result = await call_api("Test prompt", mock_config, {})
    output = result["output"]
    
    assert "Columns mapped: >>> orders.customer_id <<<" in output
    assert ">>> orders.customer_id <<< — *Unique identifier for customer*" in output


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_pretty_formatter_sql_logs(mock_run_agent, mock_get_llm, mock_config):
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }
    
    async def mock_run_agent_side_effect(*args, **kwargs):
        logger = logging.getLogger("src.agent")
        logger.info("LLM-generated SQL:\nSELECT * FROM test")
        return mock_run_agent.return_value
        
    mock_run_agent.side_effect = mock_run_agent_side_effect

    result = await call_api("Test prompt", mock_config, {})
    output = result["output"]
    
    assert "```sql\nSELECT * FROM test\n```" in output


@pytest.mark.asyncio
@patch("src.eval.provider.get_local_llm")
@patch("src.eval.provider.run_agent", new_callable=AsyncMock)
async def test_error_handling_includes_logs(mock_run_agent, mock_get_llm, mock_config):
    mock_run_agent.return_value = {
        "output": "Mock agent response",
        "sql": "SELECT * FROM test",
        "data": [{"id": 1}],
        "token_usage": {"prompt": 10, "completion": 20, "total": 30}
    }
    
    async def mock_run_agent_side_effect(*args, **kwargs):
        logger = logging.getLogger("src.agent")
        logger.info("Pre-crash step logged")
        raise ValueError("Mock Timeout")
        
    mock_run_agent.side_effect = mock_run_agent_side_effect

    result = await call_api("Test prompt", mock_config, {})
    
    assert "error" in result
    assert "ValueError: Mock Timeout" in result["error"]
    assert "Pre-crash step logged" in result["output"]
    assert "CAPTURED PIPELINE LOGS" in result["output"]

