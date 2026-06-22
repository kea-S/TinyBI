import pytest
import networkx as nx
from src.utils.pydantic_models import ColumnVectorIndexEntry
from src.utils.value_resolution.db_schema_graph import build_schema_graph, pick_anchor_table

@pytest.fixture
def sample_entries():
    return [
        ColumnVectorIndexEntry(
            entry_id=1,
            table_name="orders",
            column_name="user_id",
            source_key="orders.user_id",
            references="users.id",
            description="Link to user",
            statistical_type="nominal",
        ),
        ColumnVectorIndexEntry(
            entry_id=2,
            table_name="users",
            column_name="id",
            source_key="users.id",
            references=None,
            description="User primary key",
            statistical_type="nominal",
        ),
        ColumnVectorIndexEntry(
            entry_id=3,
            table_name="products",
            column_name="id",
            source_key="products.id",
            references=None,
            description="Product primary key",
            statistical_type="nominal",
        )
    ]

def test_build_schema_graph(sample_entries):
    graph = build_schema_graph(sample_entries)
    
    assert isinstance(graph, nx.Graph)
    assert "orders" in graph.nodes
    assert "users" in graph.nodes
    assert "products" in graph.nodes
    
    # Check edge
    assert graph.has_edge("orders", "users")
    edge_data = graph.get_edge_data("orders", "users")
    assert edge_data["on_clause"] == 'orders.user_id = users.id'

def test_pick_anchor_table_metric_precedence():
    # Metric table should win regardless of frequency
    anchor = pick_anchor_table(
        subject_tables=["users", "users", "users"],
        metric_table="orders",
        filter_tables=["users"]
    )
    assert anchor == "orders"

def test_pick_anchor_table_frequency_fallback():
    # Most frequent table wins if no metric
    anchor = pick_anchor_table(
        subject_tables=["users", "products"],
        metric_table=None,
        filter_tables=["users"]
    )
    assert anchor == "users"

def test_pick_anchor_table_empty():
    assert pick_anchor_table([], None, []) == ""
