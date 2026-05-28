import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

import pandas as pd

from src.eval.extractor_provider import call_api


@pytest.mark.asyncio
async def test_call_api_returns_correct_dict_shape():
    prompt = "How many accounts?"
    options = {
        "config": {
            "model_name": "gpt-4o",
            "local": False,
        }
    }
    context = {}

    mock_df = pd.DataFrame([{"count": 4500}])
    mock_sql = 'SELECT count(*) AS "count" FROM "account"'

    mock_run_pipeline = AsyncMock(return_value=(mock_df, mock_sql))

    with patch("src.eval.extractor_provider.run_pipeline", mock_run_pipeline):
        with patch("src.eval.extractor_provider._get_llm", return_value=MagicMock()):
            result = await call_api(prompt, options, context)

    assert "output" in result
    assert "metadata" in result
    assert result["metadata"]["model_name"] == "gpt-4o"
    assert result["metadata"]["local"] is False
    assert result["metadata"]["parsed_sql"] == mock_sql
    assert result["metadata"]["data"] == [{"count": 4500}]

    parsed_output = json.loads(result["output"])
    assert "sql" in parsed_output
    assert "data" in parsed_output


@pytest.mark.asyncio
async def test_call_api_passes_prompt_to_run_pipeline():
    prompt = "Total balance by district"
    options = {
        "config": {
            "model_name": "granite4:3b",
            "local": True,
        }
    }
    context = {}

    mock_df = pd.DataFrame([{"district": "Prague", "total": 1000}])
    mock_sql = 'SELECT "district", sum("balance") AS "total" FROM "account"'

    mock_run_pipeline = AsyncMock(return_value=(mock_df, mock_sql))

    with patch("src.eval.extractor_provider.run_pipeline", mock_run_pipeline):
        with patch("src.eval.extractor_provider._get_llm", return_value=MagicMock()):
            result = await call_api(prompt, options, context)

    mock_run_pipeline.assert_called_once_with(
        prompt, "granite4:3b", True
    )


@pytest.mark.asyncio
async def test_call_api_handles_pipeline_error():
    prompt = "Bad query that crashes"
    options = {
        "config": {
            "model_name": "gpt-4o",
            "local": False,
        }
    }
    context = {}

    mock_run_pipeline = AsyncMock(side_effect=RuntimeError("DB connection failed"))

    with patch("src.eval.extractor_provider.run_pipeline", mock_run_pipeline):
        with patch("src.eval.extractor_provider._get_llm", return_value=MagicMock()):
            result = await call_api(prompt, options, context)

    assert "output" in result
    assert "error" in result["output"].lower() or result["metadata"].get("parsed_sql") is None