from src.utils.database import global_database
from src.config import TABLE_DATA_PATH
from src.utils.pydantic_models import (
    QuerySchema,
    CandidateAttributes,
    FinalAttributes,
)
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.rag.vector_controller import VectorController
from src.utils.models import DEFAULT_EMBEDDING_MODEL
import src.utils.sql_normaliser as nrm


def query_tool(structured_query: QuerySchema,
               dataset_path: str = TABLE_DATA_PATH):
    """
    Resolve canonical locations for deterministic SQL filters
    """

    global_database.get_connection(dataset_path)
    vector_controller = VectorController(DEFAULT_EMBEDDING_MODEL)

    candidate_attributes: CandidateAttributes = \
        vector_controller.run(structured_query)

    final_attributes: FinalAttributes
    primary_table: str
    final_attributes, primary_table = \
        resolve_columns(candidate_attributes)

    subject_clause = nrm.map_subject(final_attributes.subject_entries)
    view_name = nrm.map_view_name(primary_table)
    metric_clause = nrm.map_metric(
        final_attributes.metric_entry,
        structured_query.aggregation
    )
    where_clause = nrm.map_conditions(final_attributes.filter_entries)
    group_by_clause = nrm.map_groupby(
        final_attributes.subject_entries,
        structured_query.aggregation
    )
    order_by_direction = nrm.map_ordering(structured_query.ordering)
    order_by_column = nrm.map_sort_on(
        structured_query.sort_on,
        final_attributes.metric_entry,
        final_attributes.subject_entries,
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

    df = global_database.query(sql)

    global_database.close_connection()

    return df, sql