import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

def _load_eval_data() -> Optional[Dict[str, Any]]:
    # Internal helper to load the eval JSON. 
    # Separated to allow easy patching in tests.
    file_path = Path("data/app_data/insight_results.json")
    if not file_path.exists():
        return None
    try:
        with file_path.open() as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read eval data: {e}")
        return None

def _get_eval_list() -> List[Dict[str, Any]]:
    data = _load_eval_data()
    if not data:
        return []
    return data.get("results", {}).get("results", [])

@router.get("/overview")
async def get_overview():
    evals = _get_eval_list()
    if not evals:
        return {
            "overallAccuracy": 0,
            "meanLatencyMs": 0,
            "meanTokens": 0,
            "totalTokens": 0
        }
    
    # We aggregate just the TinyBI ones by default
    tinybi_evals = [e for e in evals if e.get("provider", {}).get("label", "").startswith("TinyBI")]
    if not tinybi_evals:
        return {
            "overallAccuracy": 0,
            "meanLatencyMs": 0,
            "meanTokens": 0,
            "totalTokens": 0
        }

    total_accuracy = sum(e.get("score", 0) for e in tinybi_evals)
    total_latency = sum(e.get("latencyMs", 0) for e in tinybi_evals)
    total_tokens = sum(e.get("metrics", {}).get("tokenUsage", {}).get("total", 0) for e in tinybi_evals)
    count = len(tinybi_evals)

    return {
        "overallAccuracy": total_accuracy / count,
        "meanLatencyMs": total_latency / count,
        "meanTokens": total_tokens / count,
        "totalTokens": total_tokens
    }


@router.get("/difficulty-breakdown")
async def get_difficulty_breakdown():
    evals = _get_eval_list()
    if not evals:
        return []
    
    tinybi_evals = [e for e in evals if e.get("provider", {}).get("label", "").startswith("TinyBI")]
    
    # Group by difficulty
    groups = {}
    for e in tinybi_evals:
        diff = e.get("vars", {}).get("difficulty", "unknown")
        if diff not in groups:
            groups[diff] = {"accuracy": 0, "latencyMs": 0, "tokens": 0, "count": 0}
            
        groups[diff]["accuracy"] += e.get("score", 0)
        groups[diff]["latencyMs"] += e.get("latencyMs", 0)
        groups[diff]["tokens"] += e.get("metrics", {}).get("tokenUsage", {}).get("total", 0)
        groups[diff]["count"] += 1
        
    result = []
    for diff, data in groups.items():
        count = data["count"]
        result.append({
            "difficulty": diff,
            "accuracy": data["accuracy"] / count,
            "latencyMs": data["latencyMs"] / count,
            "tokens": data["tokens"] / count
        })
        
    return result


@router.get("/provider-comparison")
async def get_provider_comparison():
    evals = _get_eval_list()
    if not evals:
        return []
        
    # Group by provider label
    groups = {}
    for e in evals:
        provider = e.get("provider", {}).get("label", "Unknown")
        # Simplify label
        if provider.startswith("TinyBI"):
            provider_name = "TinyBI"
        elif provider.startswith("Schema Dump"):
            provider_name = "Schema Dump"
        else:
            provider_name = provider
            
        if provider_name not in groups:
            groups[provider_name] = {"accuracy": 0, "tokens": 0, "count": 0}
            
        groups[provider_name]["accuracy"] += e.get("score", 0)
        groups[provider_name]["tokens"] += e.get("metrics", {}).get("tokenUsage", {}).get("total", 0)
        groups[provider_name]["count"] += 1
        
    result = []
    for p_name, data in groups.items():
        count = data["count"]
        result.append({
            "provider": p_name,
            "accuracy": data["accuracy"] / count,
            "tokens": data["tokens"] / count
        })
        
    return result
