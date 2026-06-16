import json
import math
import sys
from pathlib import Path
from datetime import date, datetime

import numpy as np
import pandas as pd
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.prompts import EXTRACTOR_PROMPT
from src.utils.models import get_local_llm, get_remote_llm
from src.agent import run_agent
from src.tools.query_tool import query_tool
from src.baselines.raw_query_tool import raw_query_tool
from src.baselines.prompts import build_schema_dump_prompt
from src.baselines.ddl_generator import generate_ddl
from src.config import APP_DATA_PATH


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
        if isinstance(obj, np.datetime64):
            return str(obj)
        return super().default(obj)

    def _sanitize(self, obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(obj, np.datetime64):
            return str(obj)
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
    """
    Promptfoo entrypoint, the function must be called call_api.
    Supports agent types via config.agent_type:
      - "tinybi" (default): structured QuerySchema → vector search → SQL
      - "schema_dump": DDL schema in prompt → raw SQL via raw_query_tool
    """
    config = options.get("config", {})
    model_name = config.get("model_name")
    local = config.get("local", False)
    agent_type = config.get("agent_type", "tinybi")

    llm = _get_llm(model_name, local)

    if agent_type == "schema_dump":
        columns_path = str(Path(APP_DATA_PATH) / "columns.json")
        ddl_schema = generate_ddl(columns_path)
        result = await run_agent(
            [HumanMessage(content=prompt)], llm,
            tools=[raw_query_tool],
            system_prompt=build_schema_dump_prompt(ddl_schema),
        )
    else:
        result = await run_agent(
            [HumanMessage(content=prompt)], llm,
            tools=[query_tool],
            system_prompt=EXTRACTOR_PROMPT,
        )

    result["model_name"] = model_name

    return {
        "output": json.dumps(result, indent=2, cls=BenchmarkEncoder),
        "tokenUsage": result.get("token_usage"),
        "metadata": BenchmarkEncoder()._sanitize({
            "model_name": model_name,
            "local": local,
            "agent_type": agent_type,
            "parsed_sql": result.get("sql"),
            "data": result.get("data"),
        }),
    }
