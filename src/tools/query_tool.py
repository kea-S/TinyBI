from src.utils.database import global_database
from src.config import TABLE_DATA_PATH
from src.utils.pydantic_models import (
    QuerySchema,
    CandidateAttributes,
    FinalAttributes,
)
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.rag.vector_controller import VectorController
import src.utils.sql_normaliser as nrm
from src.models import DEFAULT_EMBEDDING_MODEL


def query_tool(structured_query: QuerySchema,
               dataset_path: str = TABLE_DATA_PATH):
    """
    Resolve canonical locations for deterministic SQL filters
    """

    # setup
    global_database.get_connection(dataset_path)
    vector_controller = VectorController(DEFAULT_EMBEDDING_MODEL)

    candidate_attributes: CandidateAttributes = \
        vector_controller.run(structured_query)

    final_attributes: FinalAttributes
    primary_table: str
    final_attributes, primary_table = \
        resolve_columns(candidate_attributes)

    select_clause = nrm.map_subject(final_attributes.subject_entries)
    view_name = nrm.map_view_name(primary_table)
    metric_clause = nrm.map_metric(
        final_attributes.metric_entries,
        final_attributes.aggregation
    )
    where_clause = nrm.map_conditions(final_attributes.filter_entries,
                                      structured_query.filters)
    group_by_clause = nrm.map_groupby(final_attributes.subject_entries,
                                      final_attributes.metric_entries)
    order_by_clause = nrm.map_ordering(structured_query.ordering)
    limit_clause = nrm.map_limit(structured_query.limit)
    join_clause = nrm.map_join()    # not implemented as of now

    sql = f"""
        SELECT
        {select_clause},
        {metric_clause}
        FROM
        {view_name}
        {where_clause}
        {group_by_clause}
        {order_by_clause}
        {limit_clause}
        {join_clause}
        """.strip()

    df = global_database.query(sql)

    global_database.close_connection()

    return df, sql
