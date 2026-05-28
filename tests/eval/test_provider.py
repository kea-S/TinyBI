import pytest
from src.eval.provider import call_api
from unittest.mock import patch, AsyncMock, MagicMock
import json

@pytest.mark.asyncio
async def test_call_api_invokes_run_agent():
    prompt = "How many accounts?"
    options = {
        "config": {
            "model_name": "gpt-4o",
            "local": False
        }
    }
    context = {}
    
    # Mock return value of run_agent
    mock_df = AsyncMock()
    mock_df.to_dict.return_value = [{"count": 4500}]
    
    mock_run_agent = AsyncMock()
    mock_run_agent.return_value = {
        "output": "There are 4500 accounts.",
        "sql": "SELECT count(*) FROM account",
        "data": [{"count": 4500}]
    }
    
    with patch("src.eval.provider.run_agent", mock_run_agent):
        with patch("src.eval.provider._get_llm") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            
            result = await call_api(prompt, options, context)
            
            assert "output" in result
            assert "metadata" in result
            assert result["metadata"]["parsed_sql"] == "SELECT count(*) FROM account"
            assert result["metadata"]["data"] == [{"count": 4500}]
            
            # Verify run_agent was called
            mock_run_agent.assert_called_once()
