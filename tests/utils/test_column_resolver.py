import pytest
import networkx as nx

from src.utils.pydantic_models import (
    CandidateEntries,
    ColumnVectorIndexEntry,
    FinalEntries,
    FilterIntent,
    VectorSearchResult,
)
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.value_resolution.db_schema_graph import pick_anchor_table

@pytest.fixture
def fully_connected_graph():
    G = nx.Graph()
    G.add_nodes_from(["orders", "shipments", "payments", "users", "products"])
    # Connect everything to simulate old behavior where everything was allowed
    for u in G.nodes:
        for v in G.nodes:
            if u != v:
                G.add_edge(u, v)
    return G

def _entry(entry_id: int, table_name: str, column_name: str, **extra):
    defaults = dict(
        entry_id=entry_id,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
        statistical_type="nominal",
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
    def test_single_table_wins(self, fully_connected_graph):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)
        assert final_entries.metric_entry.table_name == "orders"

    def test_majority_table_wins_when_tables_differ(self, fully_connected_graph):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="shipments", column_name="total")],
            filter_entries={fi: [_result(3, 0.88, table_name="orders", column_name="provider")]},
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)
        # Anchor logic remains: orders(2) vs shipments(1)
        assert final_entries.subject_entries[0].table_name == "orders"

    def test_tie_break_by_highest_score(self, fully_connected_graph):
        fi = _filter("provider", ("DB Schenker",))
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.80, table_name="payments", column_name="customer")],
            metric_entries=[_result(2, 0.80, table_name="orders", column_name="total")],
            filter_entries={fi: [_result(3, 0.85, table_name="payments", column_name="provider")]},
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)
        assert final_entries.subject_entries[0].table_name == "payments"


class TestResolveColumnsFilterEntries:
    def test_single_filter_maps_to_best_column(self, fully_connected_graph):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [
                    _result(3, 0.88, table_name="orders", column_name="provider", 
                            categorical_values={"DB Schenker": []}),
                    _result(4, 0.70, table_name="orders", column_name="provider_alt"),
                ],
            },
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)

        assert isinstance(final_entries.filter_entries, dict)
        assert len(final_entries.filter_entries) == 1
        resolved_intent, resolved_col = list(final_entries.filter_entries.items())[0]
        assert resolved_col.column_name == "provider"

    def test_multiple_filters_each_map_to_their_best_column(self, fully_connected_graph):
        fi_provider = _filter("provider", ["DB Schenker"])
        fi_country = _filter("buyer_country", ["Singapore"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi_provider: [_result(3, 0.88, table_name="orders", column_name="provider", 
                                      categorical_values={"DB Schenker": []})],
                fi_country: [_result(4, 0.92, table_name="orders", column_name="buyer_country", 
                                     categorical_values={"Singapore": []})],
            },
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)

        assert len(final_entries.filter_entries) == 2
        assert any(fi.attribute_hint == "provider" for fi in final_entries.filter_entries.keys())
        assert any(fi.attribute_hint == "buyer_country" for fi in final_entries.filter_entries.keys())

    def test_filter_below_confidence_is_excluded(self, fully_connected_graph):
        fi = _filter("provider", ["DB Schenker"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="customer")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={
                fi: [_result(3, 0.40, table_name="orders", column_name="provider")],
            },
        )
        final_entries = resolve_columns(candidates, fully_connected_graph)

        assert len(final_entries.filter_entries) == 0


class TestResolveColumnsCrossTableConnectivity:
    @pytest.fixture
    def schema_graph(self):
        G = nx.Graph()
        G.add_edge("orders", "users")
        G.add_node("hr_data") # Disconnected
        return G

    def test_resolve_columns_cross_table_reachable(self, schema_graph):
        # Subject in users, Metric in orders. Both connected.
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="users", column_name="name")],
            metric_entries=[_result(2, 0.90, table_name="orders", column_name="total")],
            filter_entries={},
        )
        final_entries = resolve_columns(candidates, schema_graph)
        
        assert final_entries.metric_entry.table_name == "orders"
        assert final_entries.subject_entries[0].table_name == "users"

    def test_resolve_columns_prune_unreachable(self, schema_graph):
        # Anchor will be 'orders' (metric wins). 
        # Subject 1 is in 'hr_data' (disconnected, higher score).
        # Subject 2 is in 'users' (connected, lower score).
        candidates = CandidateEntries(
            subject_entries=[
                _result(1, 0.99, table_name="hr_data", column_name="salary"),
                _result(2, 0.80, table_name="users", column_name="name"),
            ],
            metric_entries=[_result(3, 0.90, table_name="orders", column_name="total")],
            filter_entries={},
        )
        final_entries = resolve_columns(candidates, schema_graph)
        
        # hr_data should be pruned
        assert len(final_entries.subject_entries) == 1
        assert final_entries.subject_entries[0].table_name == "users"
        assert final_entries.metric_entry.table_name == "orders"

    def test_resolve_columns_filter_fallback_connectivity(self, schema_graph):
        # Anchor is 'orders'.
        # Filter candidate 1 is 'hr_data' (disconnected).
        # Filter candidate 2 is 'users' (connected).
        fi = _filter("name", ["Alice"])
        candidates = CandidateEntries(
            subject_entries=[_result(1, 0.95, table_name="orders", column_name="id")],
            metric_entries=[],
            filter_entries={
                fi: [
                    _result(2, 0.99, table_name="hr_data", column_name="employee_name"),
                    _result(3, 0.80, table_name="users", column_name="username", 
                            statistical_type="categorical", categorical_values={"Alice": []}),
                ]
            },
        )
        final_entries = resolve_columns(candidates, schema_graph)
        
        assert len(final_entries.filter_entries) == 1
        resolved_col = list(final_entries.filter_entries.values())[0]
        assert resolved_col.table_name == "users"