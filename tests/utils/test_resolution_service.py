from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent
from src.utils.value_resolution.value_resolver import resolve_filter_literals


def test_resolve_filter_literals_matches_canonical_values_by_normalized_text():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="provider",
        source_key="orders.provider",
        payload={
            "is_categorical": True,
            "canonical_values": ["DB Schenker", "SPX"],
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="provider",
        operator="=",
        raw_value_text="db-schenker",
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is not None
    assert result.raw_value_text == "DB Schenker"
    assert result.operator == "="
    assert result.negated is False


def test_resolve_filter_literals_uses_value_labels_to_map_user_friendly_text():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="client",
        column_name="gender",
        source_key="client.gender",
        payload={
            "is_categorical": True,
            "canonical_values": ["F", "M"],
            "value_labels": {
                "F": "female",
                "M": "male",
            },
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="gender",
        operator="=",
        raw_value_text="female",
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is not None
    assert result.raw_value_text == "F"
    assert result.operator == "="


def test_resolve_filter_literals_fuzzy_matches_small_typos():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="geo",
        column_name="country",
        source_key="geo.country",
        payload={
            "is_categorical": True,
            "canonical_values": ["Singapore", "Malaysia"],
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="country",
        operator="=",
        raw_value_text="Singapre",
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is not None
    assert result.raw_value_text == "Singapore"
    assert result.operator == "="


def test_resolve_filter_literals_marks_unresolved_values_for_review():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="geo",
        column_name="country",
        source_key="geo.country",
        payload={
            "is_categorical": True,
            "canonical_values": ["Singapore", "Malaysia"],
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="country",
        operator="=",
        raw_value_text="Atlantis",
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is None


def test_resolve_filter_literals_passes_non_categorical_values_through():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="created_at",
        source_key="orders.created_at",
        payload={
            "is_categorical": False,
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="date",
        operator="BETWEEN",
        raw_value_text=["2025-01-01", "2025-01-31"],
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is not None
    assert result.raw_value_text == ["2025-01-01", "2025-01-31"]
    assert result.operator == "BETWEEN"


def test_resolve_filter_literals_drops_unresolved_values_and_upgrades_operator_to_in():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="geo",
        column_name="country",
        source_key="geo.country",
        payload={
            "is_categorical": True,
            "canonical_values": ["Singapore", "Malaysia"],
        },
    )
    filter_intent = FilterIntent(
        attribute_hint="country",
        operator="=",
        raw_value_text=["Singapore", "Atlantis", "Malaysia"],
    )

    result = resolve_filter_literals(filter_intent, entry)

    assert result is not None
    assert result.raw_value_text == ["Singapore", "Malaysia"]
    assert result.operator == "IN"
