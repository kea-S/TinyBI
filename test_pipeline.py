import asyncio
from src.utils.database import global_database
from src.config import SQLITE_DATA_PATH, TABLE_DATA_PATH
from src.utils.pydantic_models import QuerySchema
from src.utils.rag.vector_controller import VectorController
from src.utils.models import DEFAULT_EMBEDDING_MODEL
from src.utils.value_resolution.column_resolver import resolve_columns
from src.utils.value_resolution.join_resolution import resolve_joins
from src.utils.value_resolution.db_schema_graph import build_schema_graph
from src.utils.prompts import format_sql_generation_context
from src.llms.extractor import get_extractor

async def main():
    global_database.setup_database(TABLE_DATA_PATH, SQLITE_DATA_PATH, read_only=True)
    
    question = "List all the withdrawals in cash transactions that the client with the id 3356 makes."
    
    # the extractor model can be run, but for reproducibility we can use a hardcoded QuerySchema
    structured_query = QuerySchema(
        user_question=question,
        subject="withdrawals in cash transactions",
        metric_hint="count",
        filters=[
            {"attribute_hint": "client id", "operator": "=", "raw_value_text": ["3356"]},
            {"attribute_hint": "operation", "operator": "=", "raw_value_text": ["VYBER"]}
        ],
        sort_on="subject",
        ordering="asc"
    )

    print("--- STRUCTURED QUERY ---")
    print(structured_query.model_dump_json(indent=2))
    
    vc = VectorController(DEFAULT_EMBEDDING_MODEL)
    candidate_entries = vc.run(structured_query)
    
    all_entries = vc.get_current_index_entries()
    schema_graph = build_schema_graph(all_entries)
    
    final_entries = resolve_columns(candidate_entries, schema_graph)
    final_joins = resolve_joins(final_entries, schema_graph)
    
    print("\n--- FINAL ENTRIES ---")
    print(final_entries.to_log_dict())
    print("\n--- FINAL JOINS ---")
    print(final_joins.model_dump_json(indent=2))
    
    context = format_sql_generation_context(final_entries, final_joins, structured_query, all_entries)
    print("\n--- FORMATTED CONTEXT ---")
    print(context)

if __name__ == "__main__":
    asyncio.run(main())
