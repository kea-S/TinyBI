import logging
from typing import Tuple, Optional, Any

import pandas as pd
from langchain_core.tools import tool

from src.utils.database import global_database
from src.config import SQLITE_DATA_PATH, TABLE_DATA_PATH

logger = logging.getLogger(__name__)

ALLOWED_PREFIXES = ("select", "with", "explain")


def execute_raw_query(sql: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if global_database._database is None:
        global_database.setup_database(TABLE_DATA_PATH, SQLITE_DATA_PATH, read_only=True)

    normalized = sql.strip().lower()
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise ValueError(
            f"Only SELECT/WITH/EXPLAIN queries are allowed. "
            f"Got: {sql.strip()[:60]}"
        )

    logger.info("Executing raw SQL:\n%s", sql)
    df = global_database.query(sql)
    logger.info("Raw query returned %d rows", len(df))

    return df, sql


@tool(response_format="content_and_artifact")
def raw_query_tool(sql: str) -> Tuple[str, Optional[Tuple[pd.DataFrame, str]]]:
    """
    Execute raw SQL against the database and return results.

    Use this tool to run any SELECT query. The database schema is provided
    in the system prompt as DDL statements.
    """
    try:
        df, executed_sql = execute_raw_query(sql)
    except Exception as e:
        error_msg = f"Query error: {type(e).__name__}: {e}"
        logger.warning("Raw query failed: %s", error_msg)
        return error_msg, None

    content = (
        f"SQL executed successfully.\n"
        f"SQL: {executed_sql}\n"
        f"Data result (top 5 rows):\n"
        f"{df.head(5).to_markdown() if not df.empty else 'No data found.'}"
    )

    return content, (df, executed_sql)
