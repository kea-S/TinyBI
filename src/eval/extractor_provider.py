import json
import math
import sys
from pathlib import Path
from datetime import date, datetime

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llms.main_pipeline import run_pipeline
from src.utils.models import get_local_llm, get_remote_llm


class BenchmarkEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)

    def _sanitize(self, obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        return obj

    def encode(self, o):
        return super().encode(self._sanitize(o))


def _get_llm(model_name: str, local: bool):
    return get_local_llm(model_name) if local else get_remote_llm(model_name)


async def call_api(prompt, options, context):
    config = options.get("config", {})
    model_name = config.get("model_name")
    local = config.get("local", False)

    try:
        df, sql = await run_pipeline(prompt, model_name, local)

        data = df.to_dict(orient="records") if df is not None and not df.empty else []

        result = {
            "output": json.dumps(
                {"sql": sql, "data": data},
                indent=2,
                cls=BenchmarkEncoder,
            ),
            "metadata": {
                "model_name": model_name,
                "local": local,
                "parsed_sql": sql,
                "data": data,
            },
        }
    except Exception as e:
        result = {
            "output": json.dumps({"error": str(e)}),
            "metadata": {
                "model_name": model_name,
                "local": local,
                "parsed_sql": None,
                "data": None,
            },
        }

    return result