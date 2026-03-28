from src.config import CLEANED_DATASET
from src.utils.database import get_connection, query, register_csv_as_view
from src.utils.pydantic_models import QuerySchema
from src.utils.sql_normaliser import (
    map_on_sale_filter,
    map_ordering,
    map_quantity_condition,
    map_select_clause,
    map_sort_column,
    map_supermarket_condition,
)


def query_tool(extracted_object: QuerySchema):
    conn = get_connection()
    view_name = register_csv_as_view(CLEANED_DATASET, view_name="test_csv", conn=conn)

    select_clause = map_select_clause()
    sort_column = map_sort_column(extracted_object.sort_by)
    order_direction = map_ordering(extracted_object.ordering)

    where_parts = [f"{sort_column} IS NOT NULL"]

    supermarket_condition = map_supermarket_condition(extracted_object.supermarkets)
    if supermarket_condition:
        where_parts.append(supermarket_condition)

    on_sale_condition = map_on_sale_filter(extracted_object.on_sale_filter)
    if on_sale_condition:
        where_parts.append(on_sale_condition)

    quantity_condition = map_quantity_condition(
        extracted_object.quantity_g_op,
        extracted_object.quantity_g_value,
    )
    if quantity_condition:
        where_parts.append("quantity_g IS NOT NULL")
        where_parts.append(quantity_condition)

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    order_by_clause = f"ORDER BY {sort_column} {order_direction}, name ASC, supermarket ASC"
    limit_clause = f"LIMIT {extracted_object.limit}"

    sql = f"""
        SELECT {select_clause}
        FROM {view_name}
        {where_clause}
        {order_by_clause}
        {limit_clause}
    """.strip()

    df = query(sql, conn=conn)
    return df, sql
