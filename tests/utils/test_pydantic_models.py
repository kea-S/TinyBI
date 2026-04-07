from pydantic import ValidationError
import pytest

from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FilterIntent,
    QuerySchema,
)


def _base_kwargs():
    return {
        "subject": "route",
        "metric_hint": "buyer waiting time",
    }


def test_query_schema_accepts_minimal_shape():
    q = QuerySchema(**_base_kwargs())

    assert q.subject == "route"
    assert q.metric_hint == "buyer waiting time"
    assert q.aggregation is None
    assert q.filters == []
    assert q.sort_on == "subject"
    assert q.ordering == "desc"
    assert q.limit is None


def test_query_schema_accepts_metric_aggregation_and_filters():
    q = QuerySchema(
        **_base_kwargs(),
        aggregation="avg",
        sort_on="metric",
        ordering="asc",
        limit=5,
        filters=[
            {
                "attribute_hint": "country",
                "operator": "=",
                "raw_value_text": "Singapore",
            },
            {
                "attribute_hint": "provider",
                "operator": "=",
                "raw_value_text": "DB Schenker",
                "negated": True,
            },
        ],
    )

    assert q.aggregation == "avg"
    assert q.sort_on == "metric"
    assert q.ordering == "asc"
    assert q.limit == 5
    assert len(q.filters) == 2
    assert q.filters[0].attribute_hint == "country"
    assert q.filters[1].negated is True


def test_query_schema_rejects_empty_metric_hint():
    with pytest.raises(ValidationError):
        QuerySchema(subject="route", metric_hint="")


def test_query_schema_rejects_invalid_aggregation():
    with pytest.raises(ValidationError):
        QuerySchema(**_base_kwargs(), aggregation="median")


def test_query_schema_rejects_limit_above_guardrail():
    with pytest.raises(ValidationError):
        QuerySchema(**_base_kwargs(), limit=101)


def test_filter_intent_normalises_operator_and_value_text():
    filter_intent = FilterIntent(
        attribute_hint=" provider ",
        operator="==",
        raw_value_text="  DB Schenker  ",
    )

    assert filter_intent.attribute_hint == "provider"
    assert filter_intent.operator == "="
    assert filter_intent.raw_value_text == "DB Schenker"


def test_filter_intent_normalises_list_value_text():
    filter_intent = FilterIntent(
        attribute_hint="country",
        operator="IN",
        raw_value_text=[" Singapore ", " Malaysia ", ""],
    )

    assert filter_intent.raw_value_text == ["Singapore", "Malaysia"]


def test_filter_intent_rejects_empty_value_text():
    with pytest.raises(ValueError):
        FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text="   ",
        )


def test_filter_intent_rejects_non_string_attribute_hint():
    with pytest.raises(ValueError):
        FilterIntent(
            attribute_hint=123,
            operator="=",
            raw_value_text="Singapore",
        )


def test_column_vector_entry_moves_legacy_data_type_to_data_format():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="customer_city",
        source_key="orders.customer_city",
        payload={"data_type": "text", "is_groupable": True},
    )

    assert entry.data_format == "text"
    assert entry.payload == {"is_groupable": True}


def test_column_vector_entry_preserves_explicit_data_format_over_legacy_payload_value():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="customer_city",
        source_key="orders.customer_city",
        data_format="city_name",
        payload={"data_type": "text", "is_groupable": True},
    )

    assert entry.data_format == "city_name"
    assert entry.payload == {"is_groupable": True}
