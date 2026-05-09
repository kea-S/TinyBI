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
