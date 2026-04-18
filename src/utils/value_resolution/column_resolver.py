from src.utils.pydantic_models import (
    CandidateAttributes,
    FinalAttributes,
    VectorSearchResult,
    ColumnVectorIndexEntry,
)
from collections import Counter

# hyperparameters
MIN_CONFIDENCE = 0.8


def resolve_columns(
        candidates: CandidateAttributes
) -> (FinalAttributes, str):
    subject_entries = candidates.subject_entries
    metric_entries = candidates.metric_entries
    filter_entries = candidates.filter_entries

    table_counter: Counter[str] = Counter()
    table_best_score: dict[str, float] = {}

    def process_entry(result: VectorSearchResult):
        table = result.entry.table_name
        table_counter[table] += 1
        current_best = table_best_score.get(table, 0.0)
        if result.score > current_best:
            table_best_score[table] = result.score

    for result in subject_entries:
        process_entry(result)

    for result in metric_entries:
        process_entry(result)

    for filter_group in filter_entries:
        for result in filter_group:
            process_entry(result)

    if not table_counter:
        raise ValueError("No table candidates found")

    highest_count = table_counter.most_common(1)[0][1]
    top_tables = [table for table, count
                  in table_counter.items()
                  if count == highest_count]

    if len(top_tables) == 1:
        primary_table = top_tables[0]
    else:
        primary_table = max(top_tables,
                            key=lambda t: table_best_score.get(t, 0.0))

    def pick_entries(
        entries: list[VectorSearchResult],
        table_name: str
    ) -> list[ColumnVectorIndexEntry]:
        return [
            r.entry
            for r
            in entries
            if (
                r.score >= MIN_CONFIDENCE and
                r.entry.table_name == table_name
            )
        ]

    subject_entries_final = pick_entries(subject_entries, primary_table)

    # Metric: pick highest confidence entry that passes threshold
    valid_metrics = [r for r in metric_entries if r.score >= MIN_CONFIDENCE]
    metric_entry_final = max(valid_metrics, key=lambda r: r.score).entry if valid_metrics else None

    # Filters: pick highest confidence from each filter group that passes threshold
    filter_entries_final = []
    for filter_group in filter_entries:
        valid_filters = [r for r in filter_group if r.score >= MIN_CONFIDENCE]
        if valid_filters:
            filter_entries_final.append(max(valid_filters, key=lambda r: r.score).entry)

    return FinalAttributes(
        subject_entries=subject_entries_final,
        metric_entry=metric_entry_final,
        filter_entries=filter_entries_final
    ), primary_table
