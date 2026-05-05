import networkx as nx
from typing import List, Optional
from src.utils.pydantic_models import (
    CandidateEntries,
    FinalEntries,
    FilterIntent,
    VectorSearchResult,
    ColumnVectorIndexEntry,
)
from src.utils.value_resolution.value_resolver import resolve_filter_literals
from src.utils.value_resolution.db_schema_graph import pick_anchor_table

# hyperparameters
MIN_CONFIDENCE = 0.5


def resolve_columns(
        candidates: CandidateEntries,
        schema_graph: nx.Graph
) -> FinalEntries:
    """
    Pick the best column for each intent, ensuring they all connect to a central anchor table.
    """
    
    # 1. Determine the Anchor Table
    # We use high-confidence candidates to guess the "center" of the query.
    potential_subjects = [r.entry.table_name for r in candidates.subject_entries if r.score >= MIN_CONFIDENCE]
    potential_metrics = [r.entry.table_name for r in candidates.metric_entries if r.score >= MIN_CONFIDENCE]
    potential_filters = []
    for group in candidates.filter_entries.values():
        potential_filters.extend([r.entry.table_name for r in group if r.score >= MIN_CONFIDENCE])

    # Precedence: Highest scoring metric's table is the preferred anchor.
    best_metric_table = None
    if candidates.metric_entries:
        valid_metrics = [r for r in candidates.metric_entries if r.score >= MIN_CONFIDENCE]
        if valid_metrics:
            best_metric_table = max(valid_metrics, key=lambda r: r.score).entry.table_name

    anchor_table = pick_anchor_table(
        subject_tables=potential_subjects,
        metric_table=best_metric_table,
        filter_tables=potential_filters
    )

    if not anchor_table:
        # Fallback to absolute highest score across everything if no confidence threshold met
        all_res = candidates.subject_entries + candidates.metric_entries
        for g in candidates.filter_entries.values():
            all_res.extend(g)
        if all_res:
            anchor_table = max(all_res, key=lambda r: r.score).entry.table_name
        else:
            raise ValueError("No column candidates found")

    def is_reachable(table: str) -> bool:
        return table == anchor_table or nx.has_path(schema_graph, anchor_table, table)

    # 2. Resolve Subjects (All that are connected)
    subject_entries_final = [
        r.entry for r in candidates.subject_entries 
        if r.score >= MIN_CONFIDENCE and is_reachable(r.entry.table_name)
    ]

    # 3. Resolve Metric (Highest scoring connected)
    metric_entry_final = None
    valid_metrics = [
        r for r in candidates.metric_entries 
        if r.score >= MIN_CONFIDENCE and is_reachable(r.entry.table_name)
    ]
    if valid_metrics:
        metric_entry_final = max(valid_metrics, key=lambda r: r.score).entry

    # 4. Resolve Filters (Highest scoring connected that also resolves literals)
    filter_entries_final: dict[FilterIntent, ColumnVectorIndexEntry] = {}
    for filter_intent, filter_group in candidates.filter_entries.items():
        # Sort by score descending to try best candidates first
        sorted_group = sorted(filter_group, key=lambda r: r.score, reverse=True)
        
        for r in sorted_group:
            if r.score < MIN_CONFIDENCE:
                break
            
            if is_reachable(r.entry.table_name):
                resolved_intent = resolve_filter_literals(filter_intent, r.entry)
                if resolved_intent is not None:
                    filter_entries_final[resolved_intent] = r.entry
                    break

    return FinalEntries(
        subject_entries=subject_entries_final,
        metric_entry=metric_entry_final,
        filter_entries=filter_entries_final
    )

