def map_select_clause() -> str:
    return "name, price, original_price, on_sale, quantity_g, supermarket"


def map_sort_column(sort_by: str) -> str:
    allowed = {
        "price": "price",
        "original_price": "original_price",
        "quantity_g": "quantity_g",
        "name": "name",
        "supermarket": "supermarket",
    }

    try:
        return allowed[sort_by]
    except KeyError as exc:
        raise ValueError(f"Unsupported sort column: {sort_by!r}") from exc


def map_ordering(ordering: str) -> str:
    normalized = ordering.strip().lower()
    if normalized == "asc":
        return "ASC"
    if normalized == "desc":
        return "DESC"
    raise ValueError("ordering must be 'asc' or 'desc'")


def map_on_sale_filter(on_sale_filter: str) -> str:
    normalized = on_sale_filter.strip().lower()
    if normalized == "any":
        return ""
    if normalized == "on_sale_only":
        return "on_sale = TRUE"
    if normalized == "not_on_sale_only":
        return "on_sale = FALSE"
    raise ValueError(f"Unsupported on_sale_filter: {on_sale_filter!r}")


def map_quantity_condition(quantity_g_op: str, quantity_g_value: int | None) -> str:
    operators = {
        "none": "",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "eq": "=",
    }

    try:
        sql_operator = operators[quantity_g_op]
    except KeyError as exc:
        raise ValueError(f"Unsupported quantity_g_op: {quantity_g_op!r}") from exc

    if not sql_operator:
        return ""

    if quantity_g_value is None:
        raise ValueError("quantity_g_value is required when quantity_g_op is not 'none'")

    return f"quantity_g {sql_operator} {quantity_g_value}"


def map_supermarket_condition(supermarkets: list[str] | None) -> str:
    if not supermarkets:
        return ""

    escaped = [value.replace("'", "''") for value in supermarkets]
    joined = ", ".join(f"'{value}'" for value in escaped)
    return f"supermarket IN ({joined})"
