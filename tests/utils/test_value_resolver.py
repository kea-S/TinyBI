import pytest

from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent
from src.utils.value_resolution.value_resolver import (
    can_resolve_value,
    resolve_filter_literals,
)


def make_entry(
    statistical_type: str = "nominal",
    categorical_values: dict[str, list[str]] | None = None,
    **kwargs
):
    return ColumnVectorIndexEntry(
        entry_id=1,
        table_name="test_table",
        column_name="test_col",
        source_key="test_table.test_col",
        statistical_type=statistical_type,
        categorical_values=categorical_values or {},
        **kwargs
    )


class TestValueResolverNewTaxonomy:
    def test_resolve_synonym_from_mapping(self):
        # 'woman' is a synonym for 'F'
        entry = make_entry(
            statistical_type="nominal",
            categorical_values={"F": ["female", "woman"], "M": ["male", "man"]}
        )
        intent = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=["woman"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("F",)

    def test_resolve_exact_category_match(self):
        # User uses the raw DB code 'F' directly
        entry = make_entry(
            statistical_type="nominal",
            categorical_values={"F": ["female"], "M": ["male"]}
        )
        intent = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=["F"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("F",)

    def test_resolve_ordinal_preserves_order(self):
        entry = make_entry(
            statistical_type="ordinal",
            categorical_values={"low": [], "medium": [], "high": []}
        )
        intent = FilterIntent(
            attribute_hint="priority",
            operator="=",
            raw_value_text=["high"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("high",)

    def test_quantitative_pass_through(self):
        # Continuous data should not attempt mapping resolution
        entry = make_entry(
            statistical_type="continuous",
            categorical_values={} # Cannot have categorical_values for continuous
        )
        intent = FilterIntent(
            attribute_hint="price",
            operator=">",
            raw_value_text=["100"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("100",)
        assert result.operator == ">"

    def test_resolve_multiple_synonyms_to_in_clause(self):
        entry = make_entry(
            statistical_type="nominal",
            categorical_values={"F": ["female", "woman"], "M": ["male", "man"]}
        )
        intent = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=["woman", "man"],
        )
        result = resolve_filter_literals(intent, entry)
        assert set(result.raw_value_text) == {"F", "M"}
        assert result.operator == "IN"

    def test_unresolvable_categorical_returns_none(self):
        entry = make_entry(
            statistical_type="categorical",
            categorical_values={"A": ["Apple"], "B": []}
        )
        intent = FilterIntent(
            attribute_hint="fruit",
            operator="=",
            raw_value_text=["Banana"], # Not in mapping or categories
        )
        result = resolve_filter_literals(intent, entry)
        assert result is None

    def test_fuzzy_match_on_synonyms(self):
        # 'womann' (typo) should match 'woman' synonym for 'F'
        entry = make_entry(
            statistical_type="nominal",
            categorical_values={"F": ["female", "woman"]}
        )
        intent = FilterIntent(
            attribute_hint="gender",
            operator="=",
            raw_value_text=["womann"],
        )
        result = resolve_filter_literals(intent, entry)
        assert result.raw_value_text == ("F",)


class TestCanResolveValueTypeCompatibility:
    """H2: String categorical values must not bind to numeric columns."""

    def test_string_value_on_continuous_rejected(self):
        entry = make_entry(statistical_type="continuous")
        intent = FilterIntent(
            attribute_hint="amount",
            operator="=",
            raw_value_text=["North Bohemia"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_string_value_on_discrete_rejected(self):
        entry = make_entry(statistical_type="discrete")
        intent = FilterIntent(
            attribute_hint="count",
            operator="=",
            raw_value_text=["North Bohemia"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_string_value_on_quantitative_rejected(self):
        entry = make_entry(statistical_type="quantitative")
        intent = FilterIntent(
            attribute_hint="value",
            operator="=",
            raw_value_text=["North Bohemia"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_numeric_value_on_continuous_accepted(self):
        entry = make_entry(statistical_type="continuous")
        intent = FilterIntent(
            attribute_hint="amount",
            operator=">",
            raw_value_text=["10000"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_numeric_value_on_discrete_accepted(self):
        entry = make_entry(statistical_type="discrete")
        intent = FilterIntent(
            attribute_hint="duration",
            operator="=",
            raw_value_text=["12"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_numeric_value_on_quantitative_accepted(self):
        entry = make_entry(statistical_type="quantitative")
        intent = FilterIntent(
            attribute_hint="balance",
            operator=">=",
            raw_value_text=["5000"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_float_value_on_continuous_accepted(self):
        entry = make_entry(statistical_type="continuous")
        intent = FilterIntent(
            attribute_hint="rate",
            operator="<",
            raw_value_text=["3.14"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_negative_numeric_value_accepted(self):
        entry = make_entry(statistical_type="continuous")
        intent = FilterIntent(
            attribute_hint="delta",
            operator="<=",
            raw_value_text=["-42.5"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_categorical_entry_with_string_value_accepted(self):
        entry = make_entry(
            statistical_type="nominal",
            categorical_values={"North Bohemia": ["north bohemia"]},
        )
        intent = FilterIntent(
            attribute_hint="region",
            operator="=",
            raw_value_text=["North Bohemia"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_categorical_entry_unrelated_value_rejected(self):
        entry = make_entry(
            statistical_type="categorical",
            categorical_values={"apple": ["fruit"], "banana": ["fruit"]},
        )
        intent = FilterIntent(
            attribute_hint="food",
            operator="=",
            raw_value_text=["car"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_temporal_entry_passthrough_unaffected(self):
        entry = make_entry(statistical_type="temporal")
        intent = FilterIntent(
            attribute_hint="date",
            operator="BETWEEN",
            raw_value_text=["2024-01-01", "2024-12-31"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_temporal_entry_with_invalid_date_rejected(self):
        entry = make_entry(statistical_type="temporal")
        intent = FilterIntent(
            attribute_hint="date",
            operator="=",
            raw_value_text=["oldest"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_temporal_entry_mixed_valid_invalid_rejected(self):
        entry = make_entry(statistical_type="temporal")
        intent = FilterIntent(
            attribute_hint="date",
            operator="BETWEEN",
            raw_value_text=["2024-01-01", "oldest"],
        )
        assert can_resolve_value(intent, entry) is False

    def test_identifier_entry_passthrough_unaffected(self):
        entry = make_entry(statistical_type="identifier")
        intent = FilterIntent(
            attribute_hint="client_id",
            operator="=",
            raw_value_text=["ABC-123"],
        )
        assert can_resolve_value(intent, entry) is True

    def test_mixed_numeric_and_non_numeric_values_rejected(self):
        entry = make_entry(statistical_type="continuous")
        intent = FilterIntent(
            attribute_hint="amount",
            operator="IN",
            raw_value_text=("100", "North Bohemia"),
        )
        assert can_resolve_value(intent, entry) is False
