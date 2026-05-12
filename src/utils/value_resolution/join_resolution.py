import networkx as nx
from src.utils.pydantic_models import (
    FinalEntries,
    FinalJoins,
    JoinStep,
)
from src.utils.value_resolution.db_schema_graph import pick_anchor_table, build_schema_graph


def resolve_joins(
    selected_entries: FinalEntries,
    schema_graph: nx.Graph
) -> FinalJoins:
    """
    Receive column cleaned entries and find the join path between each.
    Uses BFS (shortest path) to connect required tables to the anchor.
    """
    # Extract table names for anchor selection
    subject_tables = [e.table_name for e in selected_entries.subject_entries]
    metric_table = selected_entries.metric_entry.table_name if selected_entries.metric_entry else None
    filter_tables = [e.table_name for e in selected_entries.filter_entries.values()]

    anchor_table = pick_anchor_table(
        subject_tables=subject_tables,
        metric_table=metric_table,
        filter_tables=filter_tables
    )

    if not anchor_table:
        return FinalJoins(from_table="", joins=[])

    # Get all tables needed in the query
    required_tables = set(subject_tables + filter_tables)
    if metric_table:
        required_tables.add(metric_table)

    # We want to maintain a list of joins in order for SQL generation
    final_join_steps = []
    seen_tables = {anchor_table}

    # BFS from anchor to each required table
    for target_table in required_tables:
        if target_table == anchor_table or target_table in seen_tables:
            continue

        # If target table is not in graph, it can't be reached
        if target_table not in schema_graph:
            continue

        try:
            path = nx.shortest_path(schema_graph, source=anchor_table, target=target_table)

            # Add steps for the path
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                if v in seen_tables:
                    continue

                edge_data = schema_graph.get_edge_data(u, v)
                final_join_steps.append(JoinStep(
                    table=v,
                    parent=u,
                    on_clause=edge_data["on_clause"]
                ))
                seen_tables.add(v)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # This should ideally not happen if resolve_columns did its job
            continue

    return FinalJoins(from_table=anchor_table, joins=final_join_steps)
