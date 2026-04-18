import pytest
from datetime import date

from src.utils.pydantic_models import ColumnVectorIndexEntry
from src.utils.sql_normaliser import (
    map_subject,
    map_metric,
    map_date,
    map_limit,
    map_sort_on,
    map_ordering,
    map_groupby,
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
