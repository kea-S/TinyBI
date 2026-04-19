from pydantic import ValidationError
import pytest

from src.utils.pydantic_models import (
    CandidateAttributes,
    ColumnVectorIndexEntry,
    FilterIntent,
    FinalAttributes,
    QuerySchema,
    VectorSearchResult,
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
    assert q.ordering == "asc"
    assert q.limit is None


def test_query_schema_accepts_metric_aggregation_and_filters():
    q = QuerySchema(
        **_base_kwargs(),
        aggregation="avg",
        sort_on="metric_hint",
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
    assert q.sort_on == "metric_hint"
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
    assert filter_intent.raw_value_text == ("DB Schenker",)


def test_filter_intent_normalises_list_value_text():
    filter_intent = FilterIntent(
        attribute_hint="country",
        operator="IN",
        raw_value_text=[" Singapore ", " Malaysia ", ""],
    )

    assert filter_intent.raw_value_text == ("Singapore", "Malaysia")


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


class TestFilterIntentOperatorNormalization:
    def test_equals_with_single_value_stays_equals(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=("Singapore",),
        )
        assert fi.operator == "="
        assert fi.raw_value_text == ("Singapore",)

    def test_equals_with_multiple_values_upgrades_to_in(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=("Singapore", "Malaysia"),
        )
        assert fi.operator == "IN"
        assert fi.raw_value_text == ("Singapore", "Malaysia")

    def test_none_operator_with_single_value_defaults_to_equals(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator=None,
            raw_value_text=("Singapore",),
        )
        assert fi.operator == "="
        assert fi.raw_value_text == ("Singapore",)

    def test_none_operator_with_multiple_values_upgrades_to_in(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator=None,
            raw_value_text=("Singapore", "Malaysia"),
        )
        assert fi.operator == "IN"
        assert fi.raw_value_text == ("Singapore", "Malaysia")

    def test_in_with_single_value_stays_in(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator="IN",
            raw_value_text=("Singapore",),
        )
        assert fi.operator == "IN"
        assert fi.raw_value_text == ("Singapore",)

    def test_in_with_multiple_values_stays_in(self):
        fi = FilterIntent(
            attribute_hint="country",
            operator="IN",
            raw_value_text=("Singapore", "Malaysia", "Thailand"),
        )
        assert fi.operator == "IN"
        assert fi.raw_value_text == ("Singapore", "Malaysia", "Thailand")

    def test_greater_than_with_multiple_values_takes_max(self):
        fi = FilterIntent(
            attribute_hint="order_value",
            operator=">",
            raw_value_text=("20", "30"),
        )
        assert fi.operator == ">"
        assert fi.raw_value_text == ("30",)

    def test_greater_than_with_single_value_stays(self):
        fi = FilterIntent(
            attribute_hint="order_value",
            operator=">",
            raw_value_text=("100",),
        )
        assert fi.operator == ">"
        assert fi.raw_value_text == ("100",)

    def test_greater_equal_with_multiple_values_takes_max(self):
        fi = FilterIntent(
            attribute_hint="order_value",
            operator=">=",
            raw_value_text=("20", "30"),
        )
        assert fi.operator == ">="
        assert fi.raw_value_text == ("30",)

    def test_less_than_with_multiple_values_takes_min(self):
        fi = FilterIntent(
            attribute_hint="order_value",
            operator="<",
            raw_value_text=("20", "30"),
        )
        assert fi.operator == "<"
        assert fi.raw_value_text == ("20",)

    def test_less_equal_with_multiple_values_takes_min(self):
        fi = FilterIntent(
            attribute_hint="order_value",
            operator="<=",
            raw_value_text=("20", "30"),
        )
        assert fi.operator == "<="
        assert fi.raw_value_text == ("20",)

    def test_contains_with_multiple_values_takes_first(self):
        fi = FilterIntent(
            attribute_hint="description",
            operator="CONTAINS",
            raw_value_text=("shipped", "delivered"),
        )
        assert fi.operator == "CONTAINS"
        assert fi.raw_value_text == ("shipped",)

    def test_contains_with_single_value_stays(self):
        fi = FilterIntent(
            attribute_hint="description",
            operator="CONTAINS",
            raw_value_text=("shipped",),
        )
        assert fi.operator == "CONTAINS"
        assert fi.raw_value_text == ("shipped",)

    def test_between_with_two_values_stays(self):
        fi = FilterIntent(
            attribute_hint="created_at",
            operator="BETWEEN",
            raw_value_text=("2025-01-01", "2025-01-31"),
        )
        assert fi.operator == "BETWEEN"
        assert fi.raw_value_text == ("2025-01-01", "2025-01-31")

    def test_between_with_one_value_raises(self):
        with pytest.raises(ValidationError):
            FilterIntent(
                attribute_hint="created_at",
                operator="BETWEEN",
                raw_value_text=("2025-01-01",),
            )

    def test_between_with_three_values_raises(self):
        with pytest.raises(ValidationError):
            FilterIntent(
                attribute_hint="created_at",
                operator="BETWEEN",
                raw_value_text=("2025-01-01", "2025-01-15", "2025-01-31"),
            )

    def test_negated_preserved_after_normalisation(self):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=("DB Schenker", "SPX"),
            negated=True,
        )
        assert fi.operator == "IN"
        assert fi.negated is True
        assert fi.raw_value_text == ("DB Schenker", "SPX")


class TestCandidateAttributesToLogDict:
    def test_serialises_subject_and_metric_entries(self):
        candidates = CandidateAttributes(
            subject_entries=[
                VectorSearchResult(
                    entry=ColumnVectorIndexEntry(
                        entry_id=1,
                        table_name="orders",
                        column_name="customer",
                        source_key="orders.customer",
                    ),
                    score=0.95,
                )
            ],
            metric_entries=[
                VectorSearchResult(
                    entry=ColumnVectorIndexEntry(
                        entry_id=2,
                        table_name="orders",
                        column_name="total",
                        source_key="orders.total",
                    ),
                    score=0.90,
                )
            ],
            filter_entries={},
        )
        log = candidates.to_log_dict()

        assert "subject_entries" in log
        assert len(log["subject_entries"]) == 1
        assert log["subject_entries"][0]["entry"]["column_name"] == "customer"
        assert log["subject_entries"][0]["score"] == 0.95
        assert "metric_entries" in log
        assert len(log["metric_entries"]) == 1

    def test_serialises_filter_entries_as_list(self):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=("DB Schenker",),
        )
        candidates = CandidateAttributes(
            subject_entries=[
                VectorSearchResult(
                    entry=ColumnVectorIndexEntry(
                        entry_id=1,
                        table_name="orders",
                        column_name="customer",
                        source_key="orders.customer",
                    ),
                    score=0.95,
                )
            ],
            metric_entries=[],
            filter_entries={
                fi: [
                    VectorSearchResult(
                        entry=ColumnVectorIndexEntry(
                            entry_id=3,
                            table_name="orders",
                            column_name="provider",
                            source_key="orders.provider",
                        ),
                        score=0.88,
                    )
                ],
            },
        )
        log = candidates.to_log_dict()

        assert "filter_entries" in log
        assert isinstance(log["filter_entries"], list)
        assert len(log["filter_entries"]) == 1
        entry = log["filter_entries"][0]
        assert entry["intent"]["attribute_hint"] == "provider"
        assert entry["intent"]["raw_value_text"] == ["DB Schenker"]
        assert len(entry["results"]) == 1
        assert entry["results"][0]["entry"]["column_name"] == "provider"

    def test_empty_filter_entries(self):
        candidates = CandidateAttributes(
            subject_entries=[],
            metric_entries=[],
            filter_entries={},
        )
        log = candidates.to_log_dict()
        assert log["filter_entries"] == []
        assert log["subject_entries"] == []
        assert log["metric_entries"] == []


class TestFinalAttributesToLogDict:
    def test_serialises_subject_entries(self):
        attrs = FinalAttributes(
            subject_entries=[
                ColumnVectorIndexEntry(
                    entry_id=1,
                    table_name="orders",
                    column_name="customer",
                    source_key="orders.customer",
                )
            ],
            metric_entry=None,
            filter_entries={},
        )
        log = attrs.to_log_dict()

        assert "subject_entries" in log
        assert len(log["subject_entries"]) == 1
        assert log["subject_entries"][0]["column_name"] == "customer"

    def test_serialises_metric_entry(self):
        attrs = FinalAttributes(
            subject_entries=[],
            metric_entry=ColumnVectorIndexEntry(
                entry_id=2,
                table_name="orders",
                column_name="total",
                source_key="orders.total",
            ),
            filter_entries={},
        )
        log = attrs.to_log_dict()

        assert log["metric_entry"]["column_name"] == "total"

    def test_serialises_none_metric_entry(self):
        attrs = FinalAttributes(
            subject_entries=[],
            metric_entry=None,
            filter_entries={},
        )
        log = attrs.to_log_dict()
        assert log["metric_entry"] is None

    def test_serialises_filter_entries(self):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="IN",
            raw_value_text=("DB Schenker", "SPX"),
        )
        attrs = FinalAttributes(
            subject_entries=[],
            metric_entry=None,
            filter_entries={
                fi: ColumnVectorIndexEntry(
                    entry_id=3,
                    table_name="orders",
                    column_name="provider",
                    source_key="orders.provider",
                )
            },
        )
        log = attrs.to_log_dict()

        assert "filter_entries" in log
        assert isinstance(log["filter_entries"], list)
        assert len(log["filter_entries"]) == 1
        entry = log["filter_entries"][0]
        assert entry["intent"]["attribute_hint"] == "provider"
        assert entry["intent"]["raw_value_text"] == ["DB Schenker", "SPX"]
        assert entry["intent"]["operator"] == "IN"
        assert entry["column"]["column_name"] == "provider"

    def test_empty_filter_entries(self):
        attrs = FinalAttributes(
            subject_entries=[],
            metric_entry=None,
            filter_entries={},
        )
        log = attrs.to_log_dict()
        assert log["filter_entries"] == []
