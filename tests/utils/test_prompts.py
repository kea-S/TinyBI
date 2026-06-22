from src.utils.prompts import EXTRACTOR_PROMPT


def test_extractor_prompt_directs_post_tool_answer():
    assert "After calling the tool" in EXTRACTOR_PROMPT
    assert "natural-language answer" in EXTRACTOR_PROMPT


def test_extractor_prompt_grounds_answer_in_data():
    assert "based on" in EXTRACTOR_PROMPT.lower()
    assert "data" in EXTRACTOR_PROMPT.lower()


def test_prompt_loading_functions_correctly():
    from src.utils.prompts import load_prompt_text
    content = load_prompt_text("sql_generation", version="v3")
    assert isinstance(content, str)
    assert len(content) > 0


def test_sql_generation_context_uses_search_synonyms_and_explicit_physical_column_instructions():
    from src.utils.prompts import format_sql_generation_context
    from src.utils.pydantic_models import FinalEntries, FinalJoins, QuerySchema, ColumnVectorIndexEntry
    
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="district",
        column_name="A3",
        source_key="district.A3",
        statistical_type="nominal",
        description="region of district",
        aliases=["region"]
    )
    
    final_entries = FinalEntries(
        subject_entries=[entry],
        metric_entry=None,
        filter_entries={}
    )
    final_joins = FinalJoins(
        from_table="district",
        joins=[]
    )
    structured_query = QuerySchema(
        user_question="Show region of district",
        subject="district",
        metric_hint="region",
        filters=[]
    )
    
    context = format_sql_generation_context(
        final_entries,
        final_joins,
        structured_query,
        all_entries=[entry]
    )
    
    assert "search_synonyms: region" in context
    assert "A3 VARCHAR" in context


def test_sql_generation_context_includes_table_identifiers():
    from src.utils.prompts import format_sql_generation_context
    from src.utils.pydantic_models import FinalEntries, FinalJoins, QuerySchema, ColumnVectorIndexEntry
    
    subject_entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="district",
        column_name="A3",
        source_key="district.A3",
        statistical_type="nominal",
        description="region of district"
    )
    
    id_entry = ColumnVectorIndexEntry(
        entry_id=2,
        table_name="district",
        column_name="district_id",
        source_key="district.district_id",
        statistical_type="identifier",
        description="location of branch"
    )
    
    final_entries = FinalEntries(
        subject_entries=[subject_entry],
        metric_entry=None,
        filter_entries={}
    )
    final_joins = FinalJoins(
        from_table="district",
        joins=[]
    )
    structured_query = QuerySchema(
        user_question="Show region of district",
        subject="district",
        metric_hint="region",
        filters=[]
    )
    
    context = format_sql_generation_context(
        final_entries,
        final_joins,
        structured_query,
        all_entries=[subject_entry, id_entry]
    )
    
    assert "district_id VARCHAR" in context
    assert "A3 VARCHAR" in context
