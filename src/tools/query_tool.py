import logging
import re
from typing import Optional, List, Any

from src.utils.database import global_database
from src.config import SQLITE_DATA_PATH, TABLE_DATA_PATH

from src.utils.pydantic_models import (
    QuerySchema,
    CandidateEntries,
    FinalEntries,
    FinalJoins,
    FilterIntent,
    ColumnVectorIndexEntry
)
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.value_resolution.join_resolution import resolve_joins
from src.utils.value_resolution.db_schema_graph import build_schema_graph
from src.utils.rag.vector_controller import VectorController
from src.utils.models import DEFAULT_EMBEDDING_MODEL
from src.utils.prompts import SQL_GENERATION_PROMPT, format_sql_generation_context

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)


def _extract_sql_from_llm_response(response_text: str) -> str:
    """
    Extract SQL from LLM response, stripping markdown code blocks if present.
    """
    text = response_text.strip()

    sql_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()

    select_match = re.search(r"(SELECT.*?)(?:\n\n|$)", text, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()

    return text





def execute_query(structured_query: QuerySchema, llm: Optional[Any] = None):
    if global_database._database is None:
        global_database.setup_database(TABLE_DATA_PATH, SQLITE_DATA_PATH, read_only=True)

    vector_controller = VectorController(DEFAULT_EMBEDDING_MODEL)

    candidate_entries: CandidateEntries = \
        vector_controller.run(structured_query)

    logger.info("Candidate entries: %s", candidate_entries.to_log_dict())

    all_entries = vector_controller.get_current_index_entries()
    schema_graph = build_schema_graph(all_entries)

    final_entries: FinalEntries
    final_entries = resolve_columns(candidate_entries, schema_graph)

    final_joins = resolve_joins(final_entries, schema_graph)

    logger.info("Final entries: %s", final_entries.to_log_dict())
    logger.info("Final joins: %s", final_joins.model_dump_json())

    if not final_entries.subject_entries and not final_entries.metric_entry and not final_entries.filter_entries:
        raise ValueError(
            "No columns could be resolved for the SELECT clause. "
            "Please rephrase your question to specify what you want to see "
            "(e.g. a subject, metric, or both)."
        )

    if llm is None:
        raise ValueError(
            "LLM is required for SQL generation. "
            "Pass an LLM instance via the 'llm' parameter."
        )

    context = format_sql_generation_context(final_entries, final_joins, structured_query, all_entries)
    current_prompt = f"{SQL_GENERATION_PROMPT}\n\n{context}\n\nGenerate the SQL query:"
    
    max_retries = 3
    for attempt in range(max_retries + 1):
        response = llm.invoke(current_prompt)
        sql = _extract_sql_from_llm_response(response.content)
        
        logger.info("LLM-generated SQL (attempt %d):\n%s", attempt + 1, sql)
        
        try:
            df = global_database.query(sql)
            return df, sql
        except Exception as e:
            if attempt < max_retries:
                logger.warning("SQL execution failed (attempt %d). Retrying... Error: %s", attempt + 1, str(e))
                # Use string concatenation instead of multi-turn messages. Small models often perform better 
                # when the error is just appended to the ongoing text prompt.
                current_prompt += f"\n\nWait, you generated this SQL:\n```sql\n{sql}\n```\nBut it failed with this error:\n{str(e)}\n\nPlease generate a corrected SQL query that fixes the error:"
            else:
                logger.error("SQL execution failed after %d retries.", max_retries)
                raise ValueError(f"SQL execution failed after {max_retries} retries. Last error: {str(e)}") from e


def make_query_tool(llm: Any):
    @tool(args_schema=QuerySchema, response_format="content_and_artifact")
    def query_tool(**kwargs):
        """
        Execute a semantic query against the database.

        This tool resolves natural language intents into SQL by linking
        subjects and metrics to the underlying schema using vector search.
        """
        structured_query = QuerySchema(**kwargs)
        df, sql = execute_query(structured_query, llm=llm)

        agent_summary = (
            f"SQL executed successfully.\n"
            f"SQL: {sql}\n"
            f"Data result (top 5 rows):\n{df.head(5).to_markdown() if not df.empty else 'No data found.'}"
        )

        return agent_summary, (df, sql)

    return query_tool













