import os
from pathlib import Path

def load_prompt_text(name: str, version: str = "v3") -> str:
    path = Path(__file__).resolve().parent / "prompts" / f"{name}_{version}.txt"
    return path.read_text(encoding="utf-8").strip()

EXTRACTOR_PROMPT = load_prompt_text("extractor", "v3")
EXPLAINER_PROMPT = load_prompt_text("explainer", "v3")
SQL_GENERATION_PROMPT = load_prompt_text("sql_generation", "v3")



def format_sql_generation_context(
    final_entries: "FinalEntries",
    final_joins: "FinalJoins",
    structured_query: "QuerySchema",
    all_entries: list["ColumnVectorIndexEntry"] = None
) -> str:
    from collections import defaultdict
    import re
    from src.baselines.ddl_generator import _build_comment, TYPE_MAP

    lines = []
    
    lines.append("<user_raw_question>")
    lines.append(structured_query.user_question)
    lines.append("</user_raw_question>")
    lines.append("")

    # Identify all relevant tables
    tables = {final_joins.from_table}
    for step in final_joins.joins:
        tables.add(step.table)
    
    for entry in final_entries.subject_entries:
        tables.add(entry.table_name)
    if final_entries.metric_entry:
        tables.add(final_entries.metric_entry.table_name)
    for entry in final_entries.filter_entries.values():
        tables.add(entry.table_name)

    lines.append("Database Schema:")
    if all_entries:
        table_cols = defaultdict(list)
        for entry in all_entries:
            if entry.table_name in tables:
                table_cols[entry.table_name].append(entry)

        for table_name, cols in table_cols.items():
            lines.append(f"CREATE TABLE {table_name} (")
            for col in cols:
                dtype_val = col.data_format or "VARCHAR"
                dtype = TYPE_MAP.get(dtype_val, dtype_val)
                col_def = f"    {col.column_name} {dtype}"
                if col.references:
                    ref_table, ref_column = col.references.split(".")
                    col_def += f" REFERENCES {ref_table}({ref_column})"
                
                col_dict = col.model_dump() if hasattr(col, 'model_dump') else col.dict()
                col_def += f"  -- {_build_comment(col_dict)}"
                lines.append(col_def)
            lines.append(");")
            lines.append("")

    if final_joins.joins:
        lines.append("Suggested JOIN path:")
        lines.append(f"  FROM {final_joins.from_table}")
        for step in final_joins.joins:
            lines.append(f"  LEFT JOIN {step.table} ON {step.on_clause}")
        lines.append("")

    return "\n".join(lines)
