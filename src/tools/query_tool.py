import logging
from typing import Optional, List, Any

from src.utils.database import global_database
from src.config import SQLITE_DATA_PATH, TABLE_DATA_PATH
from src.utils.pydantic_models import (
    QuerySchema,
    CandidateEntries,
    FinalEntries,
)
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.value_resolution.join_resolution import resolve_joins
from src.utils.value_resolution.db_schema_graph import build_schema_graph
from src.utils.rag.vector_controller import VectorController
from src.utils.models import DEFAULT_EMBEDDING_MODEL
import src.utils.sql_normaliser as nrm

logger = logging.getLogger(__name__)


from langchain_core.tools import tool

@tool(response_format="content_and_artifact")
def query_tool(
    subject: str,
    metric_hint: str,
    aggregation: Optional[str] = None,
    filters: List[dict] = [],
    sort_on: str = "subject",
    ordering: str = "asc",
    limit: Optional[int] = None,
    duckdb_path: str = TABLE_DATA_PATH,
    sqlite_path: str = SQLITE_DATA_PATH
):
    """
    Execute a query against the database.
    
    Args:
        subject: Semantic descriptor for what each result row is about (e.g. 'buyer country').
        metric_hint: Semantic descriptor for the measure to analyze (e.g. 'order value').
        aggregation: Analytic transformation (avg, sum, count, min, max).
        filters: List of filters, each with attribute_hint, operator, and raw_value_text.
        sort_on: Dimension to sort by ('subject' or 'metric_hint').
        ordering: Sort direction ('asc' or 'desc').
        limit: Number of rows to return.
    """
    from src.utils.pydantic_models import FilterIntent

    # Reconstruct QuerySchema
    filter_intents = [FilterIntent(**f) for f in filters]
    structured_query = QuerySchema(
        subject=subject,
        metric_hint=metric_hint,
        aggregation=aggregation,
        filters=filter_intents,
        sort_on=sort_on,
        ordering=ordering,
        limit=limit
    )

    global_database.setup_database(duckdb_path, sqlite_path)
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

    join_clause = nrm.map_join(final_joins)
    subject_clause = nrm.map_subject(final_entries.subject_entries)
    view_name = nrm.map_view_name(final_joins.from_table)
    metric_clause = nrm.map_metric(
        final_entries.metric_entry,
        structured_query.aggregation
    )
    where_clause = nrm.map_conditions(final_entries.filter_entries)
    group_by_clause = nrm.map_groupby(
        final_entries.subject_entries,
        structured_query.aggregation
    )
    order_by_direction = nrm.map_ordering(structured_query.ordering)
    order_by_column = nrm.map_sort_on(
        structured_query.sort_on,
        final_entries.metric_entry,
        final_entries.subject_entries,
        structured_query.aggregation
    )
    limit_clause = nrm.map_limit(structured_query.limit)

    select_parts = []
    if subject_clause:
        select_parts.append(subject_clause)
    if metric_clause:
        select_parts.append(metric_clause)
    select_clause = ", ".join(select_parts)

    sql_parts = [
        f"SELECT {select_clause}",
        f"FROM {view_name}",
    ]

    if join_clause:
        sql_parts.append(join_clause)

    if where_clause:
        sql_parts.append(where_clause)

    if group_by_clause:
        sql_parts.append(group_by_clause)

    if order_by_column:
        direction = f" {order_by_direction}" if order_by_direction else ""
        sql_parts.append(f"ORDER BY {order_by_column}{direction}")

    if limit_clause is not None:
        sql_parts.append(f"LIMIT {limit_clause}")

    sql = "\n".join(sql_parts)

    logger.info("Final SQL:\n%s", sql)

    df = global_database.query(sql)

    global_database.close_connection()

    agent_summary = (
        f"SQL executed successfully.\n"
        f"SQL: {sql}\n"
        f"Data result (top 5 rows):\n{df.head(5).to_markdown() if not df.empty else 'No data found.'}"
    )

    return agent_summary, (df, sql)






