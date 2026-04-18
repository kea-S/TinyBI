from datetime import date
from typing import Optional
from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent


def map_subject(subject_entries: list[ColumnVectorIndexEntry]) -> str:
    """
    Convert subject entries (source_key format: table.column) to SQL select clauses.
    Each column is aliased to just the column name.
    Input: [ColumnVectorIndexEntry(source_key='shipments.provider'), ...]
    Output: 'shipments.provider AS provider, shipments.region AS region'
    """
    if not subject_entries:
        return ""
    parts = []
    for entry in subject_entries:
        source_key = entry.source_key
        column_name = source_key.split(".")[-1] if "." in source_key else source_key
        parts.append(f"{source_key} AS {column_name}")
    return ", ".join(parts)


def map_metric(metric_entry: ColumnVectorIndexEntry | None, aggregation: str | None) -> str:
    """
    Map metric entry to SQL aggregation expression.
    - If aggregation is set, wrap in aggregation function (e.g., SUM, AVG)
    - If aggregation is None, return raw column
    Input: (ColumnVectorIndexEntry(source_key='shipments.order_value'), 'sum') -> 'SUM(shipments.order_value)'
    Input: (ColumnVectorIndexEntry(source_key='shipments.bwt'), None) -> 'shipments.bwt'
    """
    if not metric_entry:
        return ""
    source_key = metric_entry.source_key
    if aggregation:
        agg_upper = aggregation.upper()
        return f"{agg_upper}({source_key})"
    return source_key


def map_view_name(view_name: str) -> str:
    """
    Return view name as-is with null safety.
    """
    if not view_name:
        raise ValueError("view_name cannot be empty")
    return view_name


def map_metric(metric_entry: ColumnVectorIndexEntry | None, aggregation: str | None) -> str:
    """
    Map metric entry to SQL aggregation expression.
    - If aggregation is set, wrap in aggregation function (e.g., SUM, AVG)
    - If aggregation is None, return raw column
    Input: (ColumnVectorIndexEntry(source_key='shipments.order_value'), 'sum') -> 'SUM(shipments.order_value)'
    Input: (ColumnVectorIndexEntry(source_key='shipments.bwt'), None) -> 'shipments.bwt'
    """
    if not metric_entry:
        return ""
    source_key = metric_entry.source_key
    if aggregation:
        agg_upper = aggregation.upper()
        return f"{agg_upper}({source_key})"
    return source_key


def map_date(d: date | str) -> str:
    """
    Convert a date (date object or ISO string) to 'YYYY-MM-DD'.
    """
    if isinstance(d, date):
        return d.isoformat()
    if isinstance(d, str):
        return d.strip()
    raise ValueError("date must be a date or ISO date string")


def map_limit(limit: Optional[int]) -> Optional[int]:
    """
    Return the integer limit as-is (or None).
    """
    return limit


def map_sort_on(
    sort_on: str,
    metric_entry: Optional[ColumnVectorIndexEntry],
    subject_entries: list[ColumnVectorIndexEntry],
    aggregation: Optional[str]
) -> str:
    """
    Resolve the ORDER BY target using resolved attributes.
    - sort_on == 'metric' or 'metric_hint': use metric column
    - sort_on == 'subject': use first subject column
    """
    if not sort_on:
        return ""
    key = sort_on.strip().lower()

    if key in ("metric", "metric_hint"):
        if not metric_entry:
            return ""
        source_key = metric_entry.source_key
        if aggregation:
            return f"{aggregation.upper()}({source_key})"
        return source_key

    if key == "subject":
        if not subject_entries:
            return ""
        return subject_entries[0].source_key

    return ""


def map_ordering(ordering: str) -> str:
    """
    Normalize ordering direction to SQL.
    """
    if not ordering:
        return ""
    o = ordering.strip().lower()
    if o == "asc":
        return "ASC"
    if o == "desc":
        return "DESC"

    raise ValueError("ordering must be 'asc' or 'desc'")


def map_conditions(
    filter_mappings: dict[FilterIntent, ColumnVectorIndexEntry]
) -> str:
    if not filter_mappings:
        return ""

    def _escape(value: str) -> str:
        return value.replace("'", "''")

    conditions: list[str] = []

    for filter_intent, entry in filter_mappings.items():
        column = entry.source_key
        operator = filter_intent.operator
        values = filter_intent.raw_value_text
        negated = filter_intent.negated

        if operator == "=":
            condition = f"{column} = '{_escape(values[0])}'"

        elif operator == "IN":
            escaped = ", ".join(f"'{_escape(v)}'" for v in values)
            condition = f"{column} IN ({escaped})"

        elif operator in ("<", "<=", ">", ">="):
            condition = f"{column} {operator} '{_escape(values[0])}'"

        elif operator == "BETWEEN":
            condition = f"{column} BETWEEN '{_escape(values[0])}' AND '{_escape(values[1])}'"

        elif operator == "CONTAINS":
            condition = f"{column} LIKE '%{_escape(values[0])}%'"

        else:
            continue

        if negated:
            condition = f"NOT ({condition})"

        conditions.append(condition)

    if not conditions:
        return ""

    return "WHERE " + " AND ".join(conditions)


def map_groupby(subject_entries: list[ColumnVectorIndexEntry], aggregation: str | None) -> str:
    """
    Generate GROUP BY clause.
    - Only if aggregation is set
    - If multiple subject columns, group by all of them
    - If no aggregation, return empty string
    Input: ([ColumnVectorIndexEntry(...)], 'sum') -> 'GROUP BY shipments.provider, shipments.region'
    Input: ([...], None) -> ''
    """
    if not aggregation:
        return ""
    if not subject_entries:
        return ""
    columns = [entry.source_key for entry in subject_entries]
    return "GROUP BY " + ", ".join(columns)


def map_join():
    """
    TODO: next release
    """
    pass
