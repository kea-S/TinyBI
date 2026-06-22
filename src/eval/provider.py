import json
import math
import sys
import io
import logging
import ast
import re
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
from src.tools.query_tool import make_query_tool
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


class PrettyLogFormatter(logging.Formatter):
    def highlight_column(self, col_name: str) -> str:
        return f">>> {col_name} <<<"

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        
        # Check Candidate entries
        if message.startswith("Candidate entries:"):
            dict_str = message[len("Candidate entries:"):].strip()
            try:
                data = ast.literal_eval(dict_str)
                
                # Collect all unique candidate columns
                cols = []
                subjects = data.get("subject_entries", [])
                for s in subjects:
                    entry = s.get("entry", {})
                    col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                    if col not in cols:
                        cols.append(col)
                
                metrics = data.get("metric_entries", [])
                for m in metrics:
                    entry = m.get("entry", {})
                    col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                    if col not in cols:
                        cols.append(col)
                        
                filters = data.get("filter_entries", [])
                for f in filters:
                    for res in f.get("results", []):
                        entry = res.get("entry", {})
                        col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                        if col not in cols:
                            cols.append(col)

                if cols:
                    cols_str = ", ".join(self.highlight_column(c) for c in cols)
                else:
                    cols_str = "None"

                formatted_lines = [
                    "### 🔍 Candidate Columns Resolution",
                    f"Columns matched: {cols_str}",
                    ""
                ]
                
                # Format subjects
                if subjects:
                    formatted_lines.append("**Subjects matched:**")
                    for s in subjects:
                        entry = s.get("entry", {})
                        col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                        desc = entry.get("description", "No description")
                        score = s.get("score", 0.0)
                        formatted_lines.append(f"  - {self.highlight_column(col)} (similarity: `{score:.3f}`) — *{desc}*")
                
                # Format metrics
                if metrics:
                    formatted_lines.append("**Metrics matched:**")
                    for m in metrics:
                        entry = m.get("entry", {})
                        col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                        desc = entry.get("description", "No description")
                        score = m.get("score", 0.0)
                        formatted_lines.append(f"  - {self.highlight_column(col)} (similarity: `{score:.3f}`) — *{desc}*")
                
                # Format filters
                if filters:
                    formatted_lines.append("**Filters matched:**")
                    for f in filters:
                        intent = f.get("intent", {})
                        hint = intent.get("attribute_hint", "unknown")
                        op = intent.get("operator", "=")
                        vals = ", ".join(f"'{v}'" for v in intent.get("raw_value_text", []))
                        formatted_lines.append(f"  - Attribute Hint: `{hint}` ({op} {vals}) matched:")
                        for res in f.get("results", []):
                            entry = res.get("entry", {})
                            col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                            desc = entry.get("description", "No description")
                            score = res.get("score", 0.0)
                            formatted_lines.append(f"    - {self.highlight_column(col)} (similarity: `{score:.3f}`) — *{desc}*")
                            
                return "\n".join(formatted_lines).strip()
            except Exception:
                pass
                
        # Check Final entries
        elif message.startswith("Final entries:"):
            dict_str = message[len("Final entries:"):].strip()
            try:
                data = ast.literal_eval(dict_str)
                
                # Collect all unique final columns mapped
                cols = []
                subjects = data.get("subject_entries", [])
                for entry in subjects:
                    col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                    if col not in cols:
                        cols.append(col)
                        
                metric = data.get("metric_entry")
                if metric:
                    col = metric.get("source_key", f"{metric.get('table_name', 'unknown')}.{metric.get('column_name', 'unknown')}")
                    if col not in cols:
                        cols.append(col)
                        
                filters = data.get("filter_entries", [])
                for f in filters:
                    entry = f.get("column", {})
                    col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                    if col not in cols:
                        cols.append(col)

                if cols:
                    cols_str = ", ".join(self.highlight_column(c) for c in cols)
                else:
                    cols_str = "None"

                formatted_lines = [
                    "### 🎯 Final Column Mapping",
                    f"Columns mapped: {cols_str}",
                    ""
                ]
                
                if subjects:
                    formatted_lines.append("**Final Subjects:**")
                    for entry in subjects:
                        col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                        desc = entry.get("description", "No description")
                        formatted_lines.append(f"  - {self.highlight_column(col)} — *{desc}*")
                        
                if metric:
                    col = metric.get("source_key", f"{metric.get('table_name', 'unknown')}.{metric.get('column_name', 'unknown')}")
                    desc = metric.get("description", "No description")
                    formatted_lines.append(f"**Final Metric:**\n  - {self.highlight_column(col)} — *{desc}*")
                else:
                    formatted_lines.append("**Final Metric:** None")
                    
                if filters:
                    formatted_lines.append("**Final Filters:**")
                    for f in filters:
                        intent = f.get("intent", {})
                        hint = intent.get("attribute_hint", "unknown")
                        op = intent.get("operator", "=")
                        vals = ", ".join(f"'{v}'" for v in intent.get("raw_value_text", []))
                        entry = f.get("column", {})
                        col = entry.get("source_key", f"{entry.get('table_name', 'unknown')}.{entry.get('column_name', 'unknown')}")
                        desc = entry.get("description", "No description")
                        formatted_lines.append(f"  - `{hint}` ({op} {vals}) ➔ {self.highlight_column(col)} — *{desc}*")
                        
                return "\n".join(formatted_lines).strip()
            except Exception:
                pass

        # Check for LLM-generated SQL or Executing raw SQL
        elif message.startswith("LLM-generated SQL:") or message.startswith("Executing raw SQL:"):
            title = "🤖 LLM-generated SQL" if message.startswith("LLM-generated SQL:") else "🔌 Executing Raw SQL"
            query_part = message.split("\n", 1)[1].strip() if "\n" in message else ""
            return f"### {title}\n```sql\n{query_part}\n```"
            
        # Check for Raw query returned
        elif message.startswith("Raw query returned"):
            return f"📊 **{message}**"
            
        # Check for Filter literal resolution dropped unresolved values
        elif message.startswith("Filter literal resolution dropped unresolved values for"):
            match = re.match(r"Filter literal resolution dropped unresolved values for ([a-zA-Z0-9_\.]+):\s*(.*)", message)
            if match:
                col_name = match.group(1)
                dict_str = match.group(2)
                highlighted_col = self.highlight_column(col_name)
                try:
                    details = ast.literal_eval(dict_str)
                    raw = details.get("raw_values", [])
                    resolved = details.get("resolved_values", [])
                    unresolved = details.get("unresolved_values", [])
                    hint = details.get("attribute_hint", "")
                    
                    return (
                        f"⚠️ **Filter literal resolution dropped unresolved values** for column {highlighted_col} (attribute hint: `{hint}`):\n"
                        f"  - Raw values: `{raw}`\n"
                        f"  - Resolved: `{resolved}`\n"
                        f"  - Unresolved (dropped): `{unresolved}`"
                    )
                except Exception:
                    return f"⚠️ **Filter literal resolution dropped unresolved values** for column {highlighted_col}: `{dict_str}`"

        return message


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

    # Set up Log Catcher
    log_capture_string = io.StringIO()
    log_handler = logging.StreamHandler(log_capture_string)
    log_handler.setFormatter(PrettyLogFormatter())
    
    src_logger = logging.getLogger("src")
    old_level = src_logger.level
    src_logger.setLevel(logging.INFO)
    src_logger.addHandler(log_handler)

    try:
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
                tools=[make_query_tool(llm)],
                system_prompt=EXTRACTOR_PROMPT,
            )

        result["model_name"] = model_name
        
        captured_logs = log_capture_string.getvalue().strip()
        json_output = json.dumps(result, indent=2, cls=BenchmarkEncoder)
        
        final_output_text = json_output
        if captured_logs:
            final_output_text += "\n\n" + "="*80 + "\nCAPTURED PIPELINE LOGS\n" + "="*80 + "\n" + captured_logs

        return {
            "output": final_output_text,
            "tokenUsage": result.get("token_usage"),
            "metadata": BenchmarkEncoder()._sanitize({
                "model_name": model_name,
                "local": local,
                "agent_type": agent_type,
                "parsed_sql": result.get("sql"),
                "data": result.get("data"),
            }),
        }
    except Exception as e:
        error_msg = f"ERROR: {type(e).__name__}: {str(e)}"
        captured_logs = log_capture_string.getvalue().strip()
        output_text = error_msg
        if captured_logs:
            output_text += "\n\n" + "="*80 + "\nCAPTURED PIPELINE LOGS\n" + "="*80 + "\n" + captured_logs
        return {
            "output": output_text,
            "error": error_msg,
        }
    finally:
        src_logger.removeHandler(log_handler)
        src_logger.setLevel(old_level)
        log_capture_string.close()
