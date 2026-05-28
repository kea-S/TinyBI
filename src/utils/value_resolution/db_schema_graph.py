import networkx as nx
from typing import List, Optional
from collections import Counter
from src.utils.pydantic_models import ColumnVectorIndexEntry


def _quote(identifier: str) -> str:
    """Quote a SQL identifier (table or column) using double quotes."""
    if not identifier:
        return ""
    if "." in identifier:
        parts = identifier.split(".")
        return ".".join(f'"{p.replace('"', '""')}"' for p in parts)
    return f'"{identifier.replace('"', '""')}"'


def build_schema_graph(entries: List[ColumnVectorIndexEntry]) -> nx.Graph:
    """
    Build an undirected graph of table relationships from column metadata.
    Edges store the 'on_clause' as an attribute.
    """
    G = nx.Graph()
    for entry in entries:
        G.add_node(entry.table_name)
        if entry.references:
            try:
                # Parse references: e.g. "users.id"
                target_table = entry.references.split(".")[0]
                on_clause = f"{_quote(entry.source_key)} = {_quote(entry.references)}"
                G.add_edge(entry.table_name, target_table, on_clause=on_clause)
            except Exception:
                continue
    return G


def pick_anchor_table(
    subject_tables: List[str],
    metric_table: Optional[str] = None,
    filter_tables: Optional[List[str]] = None
) -> str:
    """
    Select the central table to start the join path from.
    1. If metric exists, use its table.
    2. Fallback to table with most appearances in subjects and filters.
    """
    if metric_table:
        return metric_table

    combined_tables = subject_tables + (filter_tables or [])
    if not combined_tables:
        return ""

    table_counts = Counter(combined_tables)
    # max() picks the first encounter in tie cases, which is stable enough.
    return max(table_counts, key=table_counts.get)

