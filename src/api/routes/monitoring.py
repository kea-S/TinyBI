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

def _is_error(e: Dict[str, Any]) -> bool:
    if e.get("success"):
        return False
    error_str = str(e.get("error", ""))
    if "Python score" in error_str and "less than threshold" in error_str:
        return False
    return True

@router.get("/overview")
async def get_overview():
    data = _load_eval_data()
    evals = []
    last_run = None
    if data:
        evals = data.get("results", {}).get("results", [])
        last_run = data.get("results", {}).get("timestamp")

    if not evals:
        return {
            "overallAccuracy": 0,
            "meanLatencyMs": 0,
            "meanTokens": 0,
            "totalTokens": 0,
            "lastRun": last_run
        }
    
    # We aggregate just the TinyBI ones by default
    tinybi_evals = [e for e in evals if e.get("provider", {}).get("label", "").startswith("TinyBI")]
    if not tinybi_evals:
        return {
            "overallAccuracy": 0,
            "meanLatencyMs": 0,
            "meanTokens": 0,
            "totalTokens": 0,
            "lastRun": last_run
        }

    total_accuracy = sum(1 for e in tinybi_evals if e.get("success"))
    
    # Calculate latency excluding errors
    valid_latency_evals = [e for e in tinybi_evals if not _is_error(e)]
    total_latency = sum(e.get("latencyMs", 0) for e in valid_latency_evals)
    latency_count = len(valid_latency_evals) if valid_latency_evals else 1
    
    total_tokens = sum(e.get("response", {}).get("tokenUsage", {}).get("total", 0) for e in tinybi_evals)
    count = len(tinybi_evals)

    return {
        "overallAccuracy": total_accuracy / count,
        "meanLatencyMs": total_latency / latency_count,
        "meanTokens": total_tokens / count,
        "totalTokens": total_tokens,
        "lastRun": last_run
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
            groups[diff] = {"accuracy": 0, "latencyMs": 0, "latencyCount": 0, "tokens": 0, "count": 0}
            
        if e.get("success"):
            groups[diff]["accuracy"] += 1
            
        if not _is_error(e):
            groups[diff]["latencyMs"] += e.get("latencyMs", 0)
            groups[diff]["latencyCount"] += 1
            
        groups[diff]["tokens"] += e.get("response", {}).get("tokenUsage", {}).get("total", 0)
        groups[diff]["count"] += 1
        
    result = []
    for diff, data in groups.items():
        count = data["count"]
        latency_count = data["latencyCount"] if data["latencyCount"] > 0 else 1
        result.append({
            "difficulty": diff,
            "accuracy": data["accuracy"] / count,
            "latencyMs": data["latencyMs"] / latency_count,
            "tokens": data["tokens"] / count
        })
        
    order = {"simple": 0, "moderate": 1, "challenging": 2}
    result.sort(key=lambda x: order.get(x["difficulty"], 99))
        
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
            groups[provider_name] = {"accuracy": 0, "tokens": 0, "correct": 0, "fail": 0, "error": 0, "count": 0}
            
        if e.get("success"):
            groups[provider_name]["accuracy"] += 1
        groups[provider_name]["tokens"] += e.get("response", {}).get("tokenUsage", {}).get("total", 0)
        groups[provider_name]["count"] += 1
        
        # Determine correct/fail/error
        if e.get("success"):
            groups[provider_name]["correct"] += 1
        else:
            if not _is_error(e):
                groups[provider_name]["fail"] += 1
            else:
                groups[provider_name]["error"] += 1
        
    result = []
    for p_name, data in groups.items():
        count = data["count"]
        result.append({
            "provider": p_name,
            "accuracy": data["accuracy"] / count,
            "tokens": data["tokens"] / count,
            "correct": data["correct"],
            "fail": data["fail"],
            "error": data["error"]
        })
        
    return result

@router.get("/difficulty-segregated")
async def get_difficulty_segregated():
    evals = _get_eval_list()
    if not evals:
        return []
    
    # Group by provider label AND difficulty
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
            
        diff = e.get("vars", {}).get("difficulty", "unknown")
        
        key = (provider_name, diff)
        if key not in groups:
            groups[key] = {"accuracy": 0, "latencyMs": 0, "latencyCount": 0, "tokens": 0, "count": 0}
            
        if e.get("success"):
            groups[key]["accuracy"] += 1
            
        if not _is_error(e):
            groups[key]["latencyMs"] += e.get("latencyMs", 0)
            groups[key]["latencyCount"] += 1
            
        groups[key]["tokens"] += e.get("response", {}).get("tokenUsage", {}).get("total", 0)
        groups[key]["count"] += 1
        
    result = []
    for (p_name, diff), data in groups.items():
        count = data["count"]
        latency_count = data["latencyCount"] if data["latencyCount"] > 0 else 1
        result.append({
            "provider": p_name,
            "difficulty": diff,
            "accuracy": data["accuracy"] / count,
            "latencyMs": data["latencyMs"] / latency_count,
            "tokens": data["tokens"] / count
        })
        
    order = {"simple": 0, "moderate": 1, "challenging": 2}
    result.sort(key=lambda x: (order.get(x["difficulty"], 99), x["provider"]))
        
    return result
