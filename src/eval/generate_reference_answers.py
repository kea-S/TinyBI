"""
One-off script to generate reference answers for the insight eval.

Runs the gold SQL for each test case, gets the actual data, and uses
the LLM to generate a natural language answer. Writes results to
data/app_data/reference_answers.json.

Usage:
    TINYBI_VLLM_URL=http://localhost:8001/v1 uv run python -m src.eval.generate_reference_answers
"""
import asyncio
import json
import logging
from pathlib import Path

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import APP_DATA_PATH, SQLITE_DATA_PATH, TABLE_DATA_PATH
from src.utils.database import global_database
from src.utils.models import get_local_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TESTS_PATH = Path(__file__).parent / "tests.yaml"
OUTPUT_PATH = Path(APP_DATA_PATH) / "reference_answers.json"

SUMMARIZE_PROMPT = """You are a data analyst. Given a natural language question and the
actual query results, write a concise natural language answer (1-2 sentences) that
directly answers the question using the data provided.

Question: {query}

Query Results:
{data}

Answer:"""


def _ensure_database():
    global_database.setup_database(str(TABLE_DATA_PATH), str(SQLITE_DATA_PATH))


def _format_data(df) -> str:
    if df is None or len(df) == 0:
        return "No results."
    rows = df.to_dict(orient="records")
    if len(rows) == 1 and len(df.columns) == 1:
        col = df.columns[0]
        val = rows[0][col]
        return f"{col}: {val}"
    return "\n".join(str(r) for r in rows[:20])


async def generate_reference_answers(model_name: str = "ibm-granite/granite-4.1-3b"):
    _ensure_database()

    test_cases = yaml.safe_load(TESTS_PATH.read_text())
    llm = get_local_llm(model_name)

    answers = {}

    for tc in test_cases:
        vars_ = tc.get("vars", {})
        query_id = vars_.get("id", "")
        query = vars_.get("query", "")
        expected_sql = vars_.get("expected_sql", "")

        if not query_id or not expected_sql:
            continue

        logger.info(f"Generating reference answer for {query_id}...")
        df = global_database.query(expected_sql)
        data_str = _format_data(df)

        messages = [
            SystemMessage(content="You are a helpful data analyst. Answer concisely."),
            HumanMessage(content=SUMMARIZE_PROMPT.format(query=query, data=data_str)),
        ]
        response = await llm.ainvoke(messages)
        answer = response.content.strip()
        answers[query_id] = answer
        logger.info(f"  -> {answer[:100]}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(answers, indent=2))
    logger.info(f"Wrote {len(answers)} reference answers to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(generate_reference_answers())
