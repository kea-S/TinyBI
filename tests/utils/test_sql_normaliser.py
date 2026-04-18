import pytest
from datetime import date

from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent
from src.utils.sql_normaliser import (
    map_subject,
    map_metric,
    map_date,
    map_limit,
    map_sort_on,
    map_ordering,
    map_groupby,
    map_conditions,
)


class TestMapSubject:
    def test_single_entry(self):
        entries = [ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='provider', source_key='shipments.provider'
        )]
        assert map_subject(entries) == "shipments.provider AS provider"

    def test_multiple_entries(self):
        entries = [
            ColumnVectorIndexEntry(
                entry_id=1, table_name='shipments',
                column_name='provider', source_key='shipments.provider'
            ),
            ColumnVectorIndexEntry(
                entry_id=2, table_name='shipments',
                column_name='region', source_key='shipments.region'
            ),
        ]
        assert map_subject(entries) == "shipments.provider AS provider, shipments.region AS region"

    def test_empty_list(self):
        assert map_subject([]) == ""

    def test_no_dot_in_source_key(self):
        entries = [ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='provider', source_key='provider'
        )]
        assert map_subject(entries) == "provider AS provider"


class TestMapMetric:
    def test_with_aggregation(self):
        entry = ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='order_value', source_key='shipments.order_value'
        )
        assert map_metric(entry, "sum") == "SUM(shipments.order_value)"

    def test_with_avg_aggregation(self):
        entry = ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='bwt', source_key='shipments.bwt'
        )
        assert map_metric(entry, "avg") == "AVG(shipments.bwt)"

    def test_without_aggregation(self):
        entry = ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='bwt', source_key='shipments.bwt'
        )
        assert map_metric(entry, None) == "shipments.bwt"

    def test_none_entry(self):
        assert map_metric(None, "sum") == ""

    def test_none_entry_no_aggregation(self):
        assert map_metric(None, None) == ""


class TestMapDate:
    def test_date_object(self):
        d = date(2025, 1, 2)
        assert map_date(d) == "2025-01-02"

    def test_date_string(self):
        assert map_date("2025-01-02") == "2025-01-02"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            map_date(123)


class TestMapLimit:
    def test_limit_none(self):
        assert map_limit(None) is None

    def test_limit_value(self):
        assert map_limit(10) == 10


class TestMapSortOn:
    def test_sort_on_metric_with_aggregation(self):
        from src.utils.pydantic_models import ColumnVectorIndexEntry
        metric_entry = ColumnVectorIndexEntry(
            entry_id=1,
            table_name='shipments',
            column_name='order_value',
            source_key='shipments.order_value'
        )
        assert map_sort_on("metric", metric_entry, [], "sum") == "SUM(shipments.order_value)"

    def test_sort_on_metric_hint_with_aggregation(self):
        from src.utils.pydantic_models import ColumnVectorIndexEntry
        metric_entry = ColumnVectorIndexEntry(
            entry_id=1,
            table_name='shipments',
            column_name='order_value',
            source_key='shipments.order_value'
        )
        assert map_sort_on("metric_hint", metric_entry, [], "avg") == "AVG(shipments.order_value)"

    def test_sort_on_metric_without_aggregation(self):
        from src.utils.pydantic_models import ColumnVectorIndexEntry
        metric_entry = ColumnVectorIndexEntry(
            entry_id=1,
            table_name='shipments',
            column_name='order_value',
            source_key='shipments.order_value'
        )
        assert map_sort_on("metric", metric_entry, [], None) == "shipments.order_value"

    def test_sort_on_metric_no_metric_entry(self):
        assert map_sort_on("metric", None, [], "sum") == ""

    def test_sort_on_subject(self):
        from src.utils.pydantic_models import ColumnVectorIndexEntry
        subject_entries = [ColumnVectorIndexEntry(
            entry_id=1,
            table_name='shipments',
            column_name='provider',
            source_key='shipments.provider'
        )]
        assert map_sort_on("subject", None, subject_entries, None) == "shipments.provider"

    def test_sort_on_subject_multiple_entries(self):
        from src.utils.pydantic_models import ColumnVectorIndexEntry
        subject_entries = [
            ColumnVectorIndexEntry(
                entry_id=1,
                table_name='shipments',
                column_name='provider',
                source_key='shipments.provider'
            ),
            ColumnVectorIndexEntry(
                entry_id=2,
                table_name='shipments',
                column_name='region',
                source_key='shipments.region'
            )
        ]
        assert map_sort_on("subject", None, subject_entries, None) == "shipments.provider"

    def test_sort_on_subject_no_entries(self):
        assert map_sort_on("subject", None, [], None) == ""

    def test_sort_on_invalid_key_returns_empty(self):
        assert map_sort_on("something_else", None, [], None) == ""

    def test_sort_on_empty_returns_empty(self):
        assert map_sort_on("", None, [], None) == ""


class TestMapOrdering:
    def test_ordering_norm(self):
        assert map_ordering("asc") == "ASC"
        assert map_ordering("desc") == "DESC"

    def test_ordering_empty(self):
        assert map_ordering("") == ""

    def test_ordering_invalid_raises(self):
        with pytest.raises(ValueError):
            map_ordering("sideways")


class TestMapGroupby:
    def test_with_aggregation_single_entry(self):
        entries = [ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='provider', source_key='shipments.provider'
        )]
        assert map_groupby(entries, "sum") == "GROUP BY shipments.provider"

    def test_with_aggregation_multiple_entries(self):
        entries = [
            ColumnVectorIndexEntry(
                entry_id=1, table_name='shipments',
                column_name='provider', source_key='shipments.provider'
            ),
            ColumnVectorIndexEntry(
                entry_id=2, table_name='shipments',
                column_name='region', source_key='shipments.region'
            ),
        ]
        assert map_groupby(entries, "sum") == "GROUP BY shipments.provider, shipments.region"

    def test_no_aggregation_returns_empty(self):
        entries = [ColumnVectorIndexEntry(
            entry_id=1, table_name='shipments',
            column_name='provider', source_key='shipments.provider'
        )]
        assert map_groupby(entries, None) == ""

    def test_empty_entries_returns_empty(self):
        assert map_groupby([], "sum") == ""

    def test_empty_entries_no_aggregation(self):
        assert map_groupby([], None) == ""


def _entry(table_name: str, column_name: str) -> ColumnVectorIndexEntry:
    return ColumnVectorIndexEntry(
        entry_id=1,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
    )


class TestMapConditions:
    def test_empty_dict_returns_empty(self):
        assert map_conditions({}) == ""

    def test_single_equals_condition(self):
        fi = FilterIntent(attribute_hint="country", operator="=", raw_value_text=("Singapore",))
        entry = _entry("orders", "buyer_country")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.buyer_country = 'Singapore'"

    def test_single_in_condition(self):
        fi = FilterIntent(attribute_hint="country", operator="IN", raw_value_text=("Singapore", "Malaysia"))
        entry = _entry("orders", "buyer_country")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.buyer_country IN ('Singapore', 'Malaysia')"

    def test_greater_than_condition(self):
        fi = FilterIntent(attribute_hint="order_value", operator=">", raw_value_text=("100",))
        entry = _entry("orders", "order_value")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.order_value > '100'"

    def test_less_than_condition(self):
        fi = FilterIntent(attribute_hint="order_value", operator="<", raw_value_text=("50",))
        entry = _entry("orders", "order_value")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.order_value < '50'"

    def test_greater_equal_condition(self):
        fi = FilterIntent(attribute_hint="order_value", operator=">=", raw_value_text=("100",))
        entry = _entry("orders", "order_value")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.order_value >= '100'"

    def test_less_equal_condition(self):
        fi = FilterIntent(attribute_hint="order_value", operator="<=", raw_value_text=("50",))
        entry = _entry("orders", "order_value")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.order_value <= '50'"

    def test_between_condition(self):
        fi = FilterIntent(attribute_hint="created_at", operator="BETWEEN", raw_value_text=("2025-01-01", "2025-01-31"))
        entry = _entry("orders", "created_at")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.created_at BETWEEN '2025-01-01' AND '2025-01-31'"

    def test_contains_condition(self):
        fi = FilterIntent(attribute_hint="description", operator="CONTAINS", raw_value_text=("shipped",))
        entry = _entry("orders", "description")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.description LIKE '%shipped%'"

    def test_negated_condition(self):
        fi = FilterIntent(attribute_hint="provider", operator="=", raw_value_text=("SPX",), negated=True)
        entry = _entry("orders", "logistics_provider")
        result = map_conditions({fi: entry})
        assert result == "WHERE NOT (orders.logistics_provider = 'SPX')"

    def test_negated_in_condition(self):
        fi = FilterIntent(attribute_hint="country", operator="IN", raw_value_text=("Singapore", "Malaysia"), negated=True)
        entry = _entry("orders", "buyer_country")
        result = map_conditions({fi: entry})
        assert result == "WHERE NOT (orders.buyer_country IN ('Singapore', 'Malaysia'))"

    def test_multiple_conditions_joined_with_and(self):
        fi1 = FilterIntent(attribute_hint="country", operator="=", raw_value_text=("Singapore",))
        fi2 = FilterIntent(attribute_hint="provider", operator="=", raw_value_text=("DB Schenker",))
        entry1 = _entry("orders", "buyer_country")
        entry2 = _entry("orders", "logistics_provider")
        result = map_conditions({fi1: entry1, fi2: entry2})
        assert "WHERE" in result
        assert "orders.buyer_country = 'Singapore'" in result
        assert "orders.logistics_provider = 'DB Schenker'" in result
        assert result.index("'Singapore'") < result.index("'DB Schenker'")
        parts = result.split(" ", 2)
        assert parts[0] == "WHERE"

    def test_sql_escapes_single_quotes(self):
        fi = FilterIntent(attribute_hint="provider", operator="=", raw_value_text=("O'Brien",))
        entry = _entry("orders", "provider")
        result = map_conditions({fi: entry})
        assert result == "WHERE orders.provider = 'O''Brien'"
