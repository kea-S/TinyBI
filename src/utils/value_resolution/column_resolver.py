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

    metric_entry_final = max(metric_entries, key=lambda r: r.score).entry

    filter_entries_final = [
        max(filter_group, key=lambda r: r.score)
        for filter_group
        in filter_entries
    ]

    return FinalAttributes(
        subject_entries=subject_entries_final,
        metric_entries=metric_entry_final,
        filter_entries=filter_entries_final
    ), primary_table
