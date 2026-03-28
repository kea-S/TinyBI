import pytest

from src.utils.sql_normaliser import (
    map_on_sale_filter,
    map_ordering,
    map_quantity_condition,
    map_select_clause,
    map_sort_column,
    map_supermarket_condition,
)


def test_map_select_clause_returns_expected_columns():
    assert map_select_clause() == "name, price, original_price, on_sale, quantity_g, supermarket"


@pytest.mark.parametrize(
    ("sort_by", "expected"),
    [
        ("price", "price"),
        ("original_price", "original_price"),
        ("quantity_g", "quantity_g"),
        ("name", "name"),
        ("supermarket", "supermarket"),
    ],
)
def test_map_sort_column(sort_by, expected):
    assert map_sort_column(sort_by) == expected


def test_map_sort_column_rejects_unknown_value():
    with pytest.raises(ValueError):
        map_sort_column("unknown")


def test_map_ordering_normalizes_sql_direction():
    assert map_ordering("asc") == "ASC"
    assert map_ordering("desc") == "DESC"


def test_map_on_sale_filter_builds_expected_conditions():
    assert map_on_sale_filter("any") == ""
    assert map_on_sale_filter("on_sale_only") == "on_sale = TRUE"
    assert map_on_sale_filter("not_on_sale_only") == "on_sale = FALSE"


def test_map_quantity_condition_supports_weight_thresholds():
    assert map_quantity_condition("gt", 1000) == "quantity_g > 1000"
    assert map_quantity_condition("gte", 500) == "quantity_g >= 500"
    assert map_quantity_condition("none", None) == ""


def test_map_quantity_condition_requires_value_when_needed():
    with pytest.raises(ValueError):
        map_quantity_condition("lt", None)


def test_map_supermarket_condition_quotes_and_escapes_values():
    assert map_supermarket_condition(["Sheng Siong"]) == "supermarket IN ('Sheng Siong')"
    assert map_supermarket_condition(["O'Reilly Market"]) == "supermarket IN ('O''Reilly Market')"
    assert map_supermarket_condition([]) == ""
