import pytest

from src.utils.pydantic_models import QuerySchema


def test_supermarket_aliases_are_canonicalized_and_deduplicated():
    schema = QuerySchema(
        supermarkets=["sheng siong", "ShengSiong", "ntuc fairprice", "coldstorage"],
    )

    assert schema.supermarkets == ["Sheng Siong", "FairPrice", "Cold Storage"]


def test_unknown_supermarkets_are_dropped():
    schema = QuerySchema(supermarkets=["sheng siong", "some other store"])

    assert schema.supermarkets == ["Sheng Siong"]


def test_quantity_filter_requires_value():
    with pytest.raises(ValueError):
        QuerySchema(quantity_g_op="gt")


def test_quantity_filter_none_clears_value():
    schema = QuerySchema(quantity_g_op="none", quantity_g_value=1000)

    assert schema.quantity_g_value is None


def test_defaults_match_cheapest_lookup_shape():
    schema = QuerySchema()

    assert schema.on_sale_filter == "any"
    assert schema.quantity_g_op == "none"
    assert schema.sort_by == "price"
    assert schema.ordering == "asc"
    assert schema.limit == 1
    assert schema.persona == "Shopper"
