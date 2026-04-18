import pytest

from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent
from src.utils.value_resolution.value_resolver import (
    can_resolve_value,
    resolve_filter_literals,
)


def make_categorical_entry(
    canonical_values: list[str],
    value_labels: dict[str, str] | None = None,
):
    return ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="provider",
        source_key="orders.provider",
        payload={
            "is_categorical": True,
            "canonical_values": canonical_values,
            "value_labels": value_labels or {},
        },
    )


def make_non_categorical_entry():
    return ColumnVectorIndexEntry(
        entry_id=2,
        table_name="orders",
        column_name="created_at",
        source_key="orders.created_at",
        payload={
            "is_categorical": False,
        },
    )


class TestCanResolveValue:
    def test_exact_match_returns_true(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_normalized_match_returns_true(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["db-schenker"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_label_match_returns_true(self):
        entry = make_categorical_entry(
            ["DB Schenker", "SPX"],
            value_labels={"DB Schenker": "dbschenker", "SPX": "spx"},
        )
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["dbschenker"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_fuzzy_match_returns_true(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["dbschenkerr"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_no_match_returns_false(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["Atlantis Logistics"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_non_categorical_returns_true(self):
        entry = make_non_categorical_entry()
        intent = FilterIntent(
            attribute_hint="date",
            operator="BETWEEN",
            raw_value_text=["2025-01-01", "2025-01-31"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_multiple_values_one_resolves_returns_true(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker", "Atlantis Logistics"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_multiple_values_none_resolve_returns_false(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["Fake Co", "Atlantis Logistics"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_empty_canonical_values_returns_false(self):
        entry = make_categorical_entry([])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        assert can_resolve_value(intent, entry) is False


class TestResolveFilterLiterals:
    def test_exact_match_resolves_to_canonical(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("DB Schenker",)
        assert result.operator == "="

    def test_normalized_match_resolves_to_canonical(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["db-schenker"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("DB Schenker",)

    def test_label_match_resolves_to_canonical(self):
        entry = make_categorical_entry(
            ["F", "M"],
            value_labels={"F": "female", "M": "male"},
        )
        intent = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=["female"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("F",)

    def test_fuzzy_match_resolves_to_canonical(self):
        entry = make_categorical_entry(["Singapore", "Malaysia"])
        intent = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=["Singapre"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("Singapore",)

    def test_partial_match_returns_only_resolved(self):
        entry = make_categorical_entry(["Singapore", "Malaysia"])
        intent = FilterIntent(
            attribute_hint="country",
            operator="IN",
            raw_value_text=["Singapore", "Atlantis"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("Singapore",)
        assert result.operator == "IN"

    def test_multiple_resolved_upgrades_to_in(self):
        entry = make_categorical_entry(["Singapore", "Malaysia"])
        intent = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=["Singapore", "Malaysia"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("Singapore", "Malaysia")
        assert result.operator == "IN"

    def test_multiple_resolved_single_value_stays_equals(self):
        entry = make_categorical_entry(["Singapore", "Malaysia"])
        intent = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=["Singapore"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("Singapore",)
        assert result.operator == "="

    def test_non_categorical_passes_through(self):
        entry = make_non_categorical_entry()
        intent = FilterIntent(
            attribute_hint="date",
            operator="BETWEEN",
            raw_value_text=["2025-01-01", "2025-01-31"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("2025-01-01", "2025-01-31")
        assert result.operator == "BETWEEN"

    def test_all_unresolved_returns_none(self):
        entry = make_categorical_entry(["Singapore", "Malaysia"])
        intent = FilterIntent(
            attribute_hint="country",
            operator="=",
            raw_value_text=["Atlantis", "Narnia"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result is None

    def test_negated_preserved_in_result(self):
        entry = make_categorical_entry(["DB Schenker", "SPX"])
        intent = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
            negated=True,
        )
        result = resolve_filter_literals(intent, entry)
        assert result.negated is True
        assert result.raw_value_text == ("DB Schenker",)