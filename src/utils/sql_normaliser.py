from datetime import date
from typing import Optional


def map_subject(subject: str, time_granularity: Optional[str] = None) -> str:
    """
    Map QuerySchema.subject (+ time_granularity when needed) to a SQL expression.
    Returns an empty string when no subject column is needed (global).
    """
    if not subject:
        return ""

    s = subject.strip().lower()
    if s == "logistics_provider":
        return "logistics_provider"
    if s == "country":
        return "buyer_country AS country"
    if s == "route":
        return "CONCAT(seller_region, ' -> ', buyer_region)"
    if s == "global":
        return ""
    if s == "time_series":
        if not time_granularity:
            raise ValueError("time_series subject requires time_granularity")
        g = time_granularity.strip().lower()
        if g not in ("day", "week", "month"):
            raise ValueError("time_granularity must be one of: day, week, month")
        return f"{g}(dt)"

    raise ValueError(f"Unsupported subject: {subject!r}")


def map_metric(metric: str) -> str:
    """
    Map QuerySchema.metric to a SQL aggregation expression.
    """
    if not metric:
        raise ValueError("metric is required")

    m = metric.strip().lower()
    if m == "total_parcel_qty":
        return "sum(parcel_qty) AS total_parcels"
    if m == "avg_bwt":
        return "round(sum(sum_bwt)/sum(parcel_qty), 3) AS avg_bwt"
    if m == "avg_apt":
        return "round(sum(sum_apt)/sum(parcel_qty), 3) AS avg_apt"
    if m == "avg_parcel_qty":
        return "avg(parcel_qty) AS avg_parcel_qty"

    raise ValueError(f"Unsupported metric: {metric!r}")


def map_validity(include: str) -> str:
    """
    Map QuerySchema.validity_filter to a WHERE clause (or empty string).
    """
    if not include:
        return ""
    v = include.strip().lower()
    if v == "valid only":
        return "WHERE is_valid_pdt = TRUE"
    if v == "anomalies only":
        return "WHERE is_valid_pdt = FALSE"
    if v in ("all data", "all"):
        return ""
    return ""


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
    *,
    metric: Optional[str] = None,
    subject: Optional[str] = None,
    time_granularity: Optional[str] = None,
) -> str:
    """
    Resolve the ORDER BY target:
    - If sort_on == 'metric', return the metric alias (e.g., 'total_parcels', 'avg_bwt').
    - If sort_on == 'subject', return the subject column/expression (or alias if applicable).
    """
    if not sort_on:
        return ""
    key = sort_on.strip().lower()

    if key == "metric":
        if not metric:
            raise ValueError("metric is required to sort on metric")
        m = metric.strip().lower()
        if m == "total_parcel_qty":
            return "total_parcels"
        if m in ("avg_bwt", "avg_apt", "avg_parcel_qty"):
            return m
        raise ValueError(f"Unsupported metric for sort: {metric!r}")

    if key == "subject":
        if not subject:
            raise ValueError("subject is required to sort on subject")
        s = subject.strip().lower()
        if s == "logistics_provider":
            return "logistics_provider"
        if s == "country":
            # map_subject returns 'buyer_country AS country', we sort by the alias
            return "country"
        if s == "route":
            return "CONCAT(seller_region, ' -> ', buyer_region)"
        if s == "global":
            # No subject column available in global rollups
            return ""
        if s == "time_series":
            if not time_granularity:
                raise ValueError("time_series subject requires time_granularity to sort")
            g = time_granularity.strip().lower()
            if g not in ("day", "week", "month"):
                raise ValueError("time_granularity must be one of: day, week, month")
            return f"{g}(dt)"
        raise ValueError(f"Unsupported subject for sort: {subject!r}")

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


def map_extra_conditions(
    *,
    logistics_providers: list[str] | None = None,
    buyer_countries: list[str] | None = None,
    seller_countries: list[str] | None = None,
    buyer_regions: list[str] | None = None,
    seller_regions: list[str] | None = None,
) -> str:
    """
    Deterministic Filter Assembly:
    - Same-dimension values -> OR semantics via IN (...)
    - Cross-dimension filters -> AND semantics by joining blocks
    - Returns a string starting with 'AND ' (assuming a preceding WHERE clause exists)
    - Handles empty lists by returning an empty string
    """

    def _quote_list(values: list[str]) -> str:
        # SQL-escape single quotes by doubling them
        escaped = [v.replace("'", "''") for v in values]
        return ", ".join(f"'{v}'" for v in escaped)

    def _in_block(column: str, values: list[str] | None) -> str | None:
        if not values:
            return None
        return f"{column} IN ({_quote_list(values)})"

    conditions: list[str] = []

    # Providers
    block = _in_block("logistics_provider", logistics_providers)
    if block:
        conditions.append(block)

    # Countries
    block = _in_block("buyer_country", buyer_countries)
    if block:
        conditions.append(block)
    block = _in_block("seller_country", seller_countries)
    if block:
        conditions.append(block)

    # Regions
    block = _in_block("buyer_region", buyer_regions)
    if block:
        conditions.append(block)
    block = _in_block("seller_region", seller_regions)
    if block:
        conditions.append(block)

    if not conditions:
        return ""

    return "AND " + " AND ".join(conditions)
