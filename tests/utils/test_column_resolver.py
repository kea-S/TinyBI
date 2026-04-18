import pytest

from src.utils.pydantic_models import (
    CandidateAttributes,
    ColumnVectorIndexEntry,
    FinalAttributes,
    FilterIntent,
    VectorSearchResult,
)
from src.utils.value_resolution.column_resolver import resolve_columns


def _entry(entry_id: int, table_name: str, column_name: str, **extra):
    defaults = dict(
        entry_id=entry_id,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
    )
    defaults.update(extra)
    return ColumnVectorIndexEntry(**defaults)


def _result(entry_id: int, score: float, table_name: str = "orders", column_name: str | None = None, **extra):
    col = column_name or f"col_{entry_id}"
    return VectorSearchResult(
        entry=_entry(entry_id, table_name=table_name, column_name=col, **extra),
        score=score,
    )


def _filter(attribute_hint: str, raw_value_text: list[str] | None = None, operator: str | None = "=", negated: bool = False):
    return FilterIntent(
        attribute_hint=attribute_hint,
        operator=operator,
        raw_value_text=raw_value_text or [attribute_hint],
        negated=negated,
    )


class TestResolveColumnsReturnsPrimaryTable:
    def test_single_table_wins(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_attrs, table = resolve_columns(candidates)
        assert table == "orders"

    def test_majority_table_wins_when_tables_differ(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="shipments", column_name="total")],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_attrs, table = resolve_columns(candidates)
        assert table == "orders"

    def test_tie_break_by_highest_score(self):
        fi = _filter("provider", ("DB Schenker",))
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.80, table_name="payments", column_name="customer")],
            metric_entries=[_result(2, 0.80, table_name="orders", column_name="total")],
            filter_entries={fi: [_result(3, 0.85, table_name="payments", column_name="provider")]},
        )
        final_attrs, table = resolve_columns(candidates)
        assert table == "payments"


class TestResolveColumnsFilterEntries:
    def test_single_filter_maps_to_best_column(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [
                    _result(3, 0.88, table_name="orders", column_name="provider"),
                    _result(4, 0.70, table_name="orders", column_name="provider_alt"),
                ],
            },
        )
        final_attrs, _ = resolve_columns(candidates)

        assert isinstance(final_attrs.filter_entries, dict)
        assert len(final_attrs.filter_entries) == 1
        resolved_intent, resolved_col = list(final_attrs.filter_entries.items())[0]
        assert resolved_col.column_name == "provider"

    def test_multiple_filters_each_map_to_their_best_column(self):
        fi_provider = _filter("provider", ["DB Schenker"])
        fi_country = _filter("buyer_country", ["Singapore"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi_provider: [_result(3, 0.88, table_name="orders", column_name="provider")],
                fi_country: [_result(4, 0.92, table_name="orders", column_name="buyer_country")],
            },
        )
        final_attrs, _ = resolve_columns(candidates)

        assert len(final_attrs.filter_entries) == 2
        assert fi_provider in final_attrs.filter_entries
        assert fi_country in final_attrs.filter_entries
        assert final_attrs.filter_entries[fi_provider].column_name == "provider"
        assert final_attrs.filter_entries[fi_country].column_name == "buyer_country"

    def test_filter_below_confidence_is_excluded(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [_result(3, 0.40, table_name="orders", column_name="provider")],
            },
        )
        final_attrs, _ = resolve_columns(candidates)

        assert len(final_attrs.filter_entries) == 0

    def test_filter_with_all_below_confidence_excluded(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [
                    _result(3, 0.40, table_name="orders", column_name="provider"),
                    _result(4, 0.50, table_name="orders", column_name="provider_alt"),
                ],
            },
        )
        final_attrs, _ = resolve_columns(candidates)

        assert len(final_attrs.filter_entries) == 0

    def test_highest_confidence_filter_column_picked(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [
                    _result(3, 0.70, table_name="orders", column_name="provider_low"),
                    _result(4, 0.95, table_name="orders", column_name="provider_high"),
                ],
            },
        )
        final_attrs, _ = resolve_columns(candidates)

        assert final_attrs.filter_entries[fi].column_name == "provider_high"

    def test_filter_intent_literals_are_resolved_against_best_column(self):
        fi = _filter("provider", ["DB Schenker"])
        result_entry = _result(
            3, 0.95, table_name="orders", column_name="provider",
            payload={"is_categorical": True, "canonical_values": ["DB Schenker", "SPX"]},
        )
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={fi: [result_entry]},
        )
        final_attrs, _ = resolve_columns(candidates)

        resolved_intent = list(final_attrs.filter_entries.keys())[0]
        assert resolved_intent.raw_value_text == ("DB Schenker",)

    def test_filter_intent_with_no_resolvable_literals_is_dropped(self):
        fi = _filter("country", ["Atlantis"])
        result_entry = _result(
            3, 0.95, table_name="orders", column_name="buyer_country",
            payload={"is_categorical": True, "canonical_values": ["Singapore", "Malaysia"]},
        )
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={fi: [result_entry]},
        )
        final_attrs, _ = resolve_columns(candidates)

        assert len(final_attrs.filter_entries) == 0


class TestResolveColumnsPreservesSubjectAndMetric:
    def test_subject_entries_from_primary_table(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[
                _result(1, 0.95, table_name="orders", column_name="customer"),
                _result(5, 0.60, table_name="shipments", column_name="customer"),
            ],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_attrs, _ = resolve_columns(candidates)

        assert len(final_attrs.subject_entries) == 1
        assert final_attrs.subject_entries[0].column_name == "customer"
        assert final_attrs.subject_entries[0].table_name == "orders"

    def test_metric_entry_is_highest_confidence(self):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateAttributes(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[
                _result(2, 0.85, table_name="orders", column_name="total_low"),
                _result(6, 0.95, table_name="orders", column_name="total_high"),
            ],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_attrs, _ = resolve_columns(candidates)

        assert final_attrs.metric_entry is not None
        assert final_attrs.metric_entry.column_name == "total_high"