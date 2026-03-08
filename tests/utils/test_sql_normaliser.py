import pytest
from datetime import date

from src.utils.sql_normaliser import (
    map_subject,
    map_metric,
    map_validity,
    map_date,
    map_limit,
    map_sort_on,
    map_ordering,
    map_extra_conditions,
)


class TestMapSubject:
    def test_logistics_provider(self):
        assert map_subject("logistics_provider") == "logistics_provider"

    def test_country(self):
        assert map_subject("country") == "buyer_country AS country"

    def test_route(self):
        assert map_subject("route") == "CONCAT(seller_region, ' -> ', buyer_region)"

    def test_global(self):
        assert map_subject("global") == ""

    @pytest.mark.parametrize("granularity,expected", [
        ("day", "day(dt)"),
        ("week", "week(dt)"),
        ("month", "month(dt)"),
    ])
    def test_time_series_with_granularity(self, granularity, expected):
        assert map_subject("time_series", granularity) == expected

    def test_time_series_missing_granularity_raises(self):
        with pytest.raises(ValueError):
            map_subject("time_series", None)

    def test_time_series_invalid_granularity_raises(self):
        with pytest.raises(ValueError):
            map_subject("time_series", "quarter")


class TestMapMetric:
    def test_total_parcel_qty(self):
        assert map_metric("total_parcel_qty") == "sum(parcel_qty) AS total_parcels"

    def test_avg_bwt(self):
        assert map_metric("avg_bwt") == "round(sum(sum_bwt)/sum(parcel_qty), 3) AS avg_bwt"

    def test_avg_apt(self):
        assert map_metric("avg_apt") == "round(sum(sum_apt)/sum(parcel_qty), 3) AS avg_apt"

    def test_avg_parcel_qty(self):
        assert map_metric("avg_parcel_qty") == "avg(parcel_qty) AS avg_parcel_qty"

    def test_unsupported_metric_raises(self):
        with pytest.raises(ValueError):
            map_metric("median_bwt")


class TestMapValidity:
    def test_valid_only(self):
        assert map_validity("Valid Only") == "WHERE is_valid_pdt = TRUE"

    def test_anomalies_only(self):
        assert map_validity("Anomalies Only") == "WHERE is_valid_pdt = FALSE"

    def test_all_data(self):
        assert map_validity("All Data") == ""

    def test_empty_or_none(self):
        assert map_validity("") == ""
        assert map_validity(None) == ""  # type: ignore[arg-type]


class TestMapDate:
    def test_date_object(self):
        # Note: If this fails with a TypeError in isinstance, there is likely a name shadowing bug in map_date.
        d = date(2025, 1, 2)
        assert map_date(d) == "2025-01-02"

    def test_date_string(self):
        assert map_date("2025-01-02") == "2025-01-02"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            map_date(123)  # type: ignore[arg-type]


class TestMapLimit:
    def test_limit_none(self):
        assert map_limit(None) is None

    def test_limit_value(self):
        assert map_limit(10) == 10


class TestMapSortOn:
    def test_sort_on_metric_aliases(self):
        assert map_sort_on("metric", metric="total_parcel_qty") == "total_parcels"
        assert map_sort_on("metric", metric="avg_parcel_qty") == "avg_parcel_qty"
        assert map_sort_on("metric", metric="avg_bwt") == "avg_bwt"
        assert map_sort_on("metric", metric="avg_apt") == "avg_apt"

    def test_sort_on_metric_requires_metric(self):
        with pytest.raises(ValueError):
            map_sort_on("metric")

    def test_sort_on_subject_columns(self):
        assert map_sort_on("subject", subject="logistics_provider") == "logistics_provider"
        assert map_sort_on("subject", subject="country") == "country"
        assert map_sort_on("subject", subject="route") == "CONCAT(seller_region, ' -> ', buyer_region)"
        assert map_sort_on("subject", subject="global") == ""

    def test_sort_on_time_series(self):
        assert map_sort_on("subject", subject="time_series", time_granularity="month") == "month(dt)"
        with pytest.raises(ValueError):
            map_sort_on("subject", subject="time_series")  # missing granularity
        with pytest.raises(ValueError):
            map_sort_on("subject", subject="time_series", time_granularity="quarter")  # invalid granularity

    def test_sort_on_invalid_key_returns_empty(self):
        assert map_sort_on("something_else", subject="country") == ""


class TestMapOrdering:
    def test_ordering_norm(self):
        assert map_ordering("asc") == "ASC"
        assert map_ordering("desc") == "DESC"

    def test_ordering_empty(self):
        assert map_ordering("") == ""

    def test_ordering_invalid_raises(self):
        with pytest.raises(ValueError):
            map_ordering("sideways")


class TestMapExtraConditions:
    def test_empty_inputs(self):
        assert map_extra_conditions() == ""

    def test_providers_only(self):
        out = map_extra_conditions(logistics_providers=["SPX", "DB Schenker"])
        assert out == "AND logistics_provider IN ('SPX', 'DB Schenker')"

    def test_countries_and_regions(self):
        out = map_extra_conditions(
            buyer_countries=["Malaysia", "Singapore"],
            seller_countries=["Germany"],
            buyer_regions=["SEA"],
            seller_regions=["EU"],
        )
        assert out == (
            "AND buyer_country IN ('Malaysia', 'Singapore') AND "
            "seller_country IN ('Germany') AND "
            "buyer_region IN ('SEA') AND "
            "seller_region IN ('EU')"
        )

    def test_multiple_dimensions_with_providers(self):
        out = map_extra_conditions(
            logistics_providers=["SPX"],
            buyer_countries=["Malaysia"],
        )
        assert out == "AND logistics_provider IN ('SPX') AND buyer_country IN ('Malaysia')"

    def test_escaping_single_quotes(self):
        out = map_extra_conditions(logistics_providers=["O'Reilly Logistics"])
        assert out == "AND logistics_provider IN ('O''Reilly Logistics')"

