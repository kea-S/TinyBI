import pytest
import networkx as nx
from src.utils.pydantic_models import ColumnVectorIndexEntry, FinalEntries, FilterIntent
from src.utils.value_resolution.join_resolution import resolve_joins
from src.utils.value_resolution.db_schema_graph import build_schema_graph

def make_entry(table: str, column: str, references: str = None):
    return ColumnVectorIndexEntry(
        entry_id=0,
        table_name=table,
        column_name=column,
        source_key=f"{table}.{column}",
        references=references,
        statistical_type="nominal",
    )

class TestResolveJoins:
    @pytest.fixture
    def sample_entries(self):
        return [
            make_entry("sales", "user_id", references="users.id"),
            make_entry("users", "id", references="companies.id"),
            make_entry("companies", "id"),
            make_entry("products", "id"),
            make_entry("sales", "product_id", references="products.id")
        ]

    @pytest.fixture
    def schema_graph(self, sample_entries):
        return build_schema_graph(sample_entries)

    def test_resolve_joins_direct_connection(self, sample_entries, schema_graph):
        # sales -> users
        final_entries = FinalEntries(
            subject_entries=[make_entry("users", "name")],
            metric_entry=make_entry("sales", "amount"),
            filter_entries={}
        )
        result = resolve_joins(final_entries, schema_graph)
        
        assert result.from_table == "sales"
        assert len(result.joins) == 1
        assert result.joins[0].table == "users"
        assert result.joins[0].on_clause == '"sales"."user_id" = "users"."id"'

    def test_resolve_joins_multi_hop_connection(self, sample_entries, schema_graph):
        # sales -> users -> companies
        final_entries = FinalEntries(
            subject_entries=[make_entry("companies", "name")],
            metric_entry=make_entry("sales", "amount"),
            filter_entries={}
        )
        result = resolve_joins(final_entries, schema_graph)
        
        assert result.from_table == "sales"
        assert len(result.joins) == 2
        assert result.joins[0].table == "users"
        assert result.joins[1].table == "companies"

    def test_resolve_joins_deduplication(self, sample_entries, schema_graph):
        final_entries = FinalEntries(
            subject_entries=[
                make_entry("users", "name"),
                make_entry("companies", "name")
            ],
            metric_entry=make_entry("sales", "amount"),
            filter_entries={}
        )
        result = resolve_joins(final_entries, schema_graph)
        
        assert result.from_table == "sales"
        assert len(result.joins) == 2
        tables = [j.table for j in result.joins]
        assert "users" in tables
        assert "companies" in tables

    def test_resolve_joins_single_table(self, sample_entries, schema_graph):
        final_entries = FinalEntries(
            subject_entries=[make_entry("sales", "id")],
            metric_entry=make_entry("sales", "amount"),
            filter_entries={}
        )
        result = resolve_joins(final_entries, schema_graph)
        assert result.from_table == "sales"
        assert len(result.joins) == 0

    def test_resolve_joins_no_path(self, sample_entries, schema_graph):
        # disconnected table
        disconnected_entry = make_entry("other", "id")
        final_entries = FinalEntries(
            subject_entries=[make_entry("other", "name")],
            metric_entry=make_entry("sales", "amount"),
            filter_entries={}
        )
        # It should just skip it robustly now
        result = resolve_joins(final_entries, schema_graph)
        assert result.from_table == "sales"
        assert len(result.joins) == 0
