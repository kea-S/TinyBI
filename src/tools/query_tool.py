from src.utils.database import get_connection, register_csv_as_view, query
from src.config import CLEANED_DATASET
from src.utils.sql_normaliser import map_subject, map_metric, map_validity, \
    map_date, map_limit, map_sort_on, map_ordering, map_extra_conditions
from src.utils.pydantic_models import QuerySchema
from src.utils.validate_llm_output import resolve_locations_postvalidated


def query_tool(extracted_object: QuerySchema):
    # Resolve canonical locations for deterministic SQL filters
    extracted_dict = extracted_object.model_dump()
    resolved = resolve_locations_postvalidated(extracted_dict)

    # DB setup
    conn = get_connection()
    view_name = register_csv_as_view(CLEANED_DATASET, view_name="test_csv", conn=conn)

    # SELECT list
    raw_subject_expr = map_subject(
        extracted_object.subject, extracted_object.time_granularity
    )

    # For time_series, alias the expression to its own text so pandas gets column name "month(dt)"
    if extracted_object.subject == "time_series" and raw_subject_expr:
        subject_expr = f'{raw_subject_expr} AS "{raw_subject_expr}"'
    else:
        subject_expr = raw_subject_expr

    metric_expr = map_metric(extracted_object.metric)
    select_parts = [p for p in (subject_expr, metric_expr) if p]
    select_clause = ",\n            ".join(select_parts)

    # WHERE assembly parts: validity (as condition), date range, and extra filters
    validity_clause = map_validity(extracted_object.validity_filter)  # "WHERE ..."/""
    validity_condition = (
        validity_clause.removeprefix("WHERE ").strip() if validity_clause else ""
    )

    sd = map_date(extracted_object.start_date)
    ed = map_date(extracted_object.end_date)
    date_condition = f"dt BETWEEN '{sd}' AND '{ed}'"

    extra_and_prefixed = map_extra_conditions(
        logistics_providers=extracted_object.logistics_providers or None,
        buyer_countries=resolved["buyer_countries"],
        seller_countries=resolved["seller_countries"],
        buyer_regions=resolved["buyer_regions"],
        seller_regions=resolved["seller_regions"],
    )
    extra_condition = (
        extra_and_prefixed[4:] if extra_and_prefixed.startswith("AND ") else extra_and_prefixed
    )

    where_parts = []
    if validity_condition:
        where_parts.append(validity_condition)
    where_parts.append(date_condition)
    if extra_condition:
        where_parts.append(extra_condition)

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    # GROUP BY (only when subject exists)
    group_by_target = (
        map_sort_on(
            "subject",
            subject=extracted_object.subject,
            time_granularity=extracted_object.time_granularity,
        )
        if raw_subject_expr
        else ""
    )
    group_by_clause = f"GROUP BY {group_by_target}" if group_by_target else ""

    # ORDER BY
    order_target = map_sort_on(
        extracted_object.sort_on,
        metric=extracted_object.metric,
        subject=extracted_object.subject,
        time_granularity=extracted_object.time_granularity,
    )
    if not order_target:
        # Fallback to metric when subject is not sortable (e.g., global)
        order_target = map_sort_on("metric", metric=extracted_object.metric)

    order_direction = map_ordering(extracted_object.ordering)
    order_by_clause = (
        f"ORDER BY {order_target} {order_direction}" if order_target and order_direction else ""
    )

    # LIMIT
    limit_val = map_limit(extracted_object.limit)
    limit_clause = f"LIMIT {limit_val}" if limit_val is not None else ""

    # Final SQL
    sql = f"""
        SELECT
            {select_clause}
        FROM {view_name}
        {where_clause}
        {group_by_clause}
        {order_by_clause}
        {limit_clause}
    """.strip()

    df = query(sql, conn=conn)
    return df, sql
