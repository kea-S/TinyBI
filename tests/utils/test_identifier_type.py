from src.utils.pydantic_models import ColumnVectorIndexEntry, FilterIntent
from src.utils.value_resolution.value_resolver import resolve_filter_literals

def test_identifier_type_passes_through_resolver():
    # 1. Test explicit identifier type
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="clients",
        column_name="client_id",
        source_key="clients.client_id",
        statistical_type="identifier", # New type
    )
    
    filter_intent = FilterIntent(
        attribute_hint="id",
        operator="=",
        raw_value_text="ABC-123",
    )

    # Should NOT be dropped
    result = resolve_filter_literals(filter_intent, entry)
    assert result is not None
    assert result.raw_value_text == ("ABC-123",)

def test_legacy_id_migration_to_identifier():
    # 2. Test migration logic for legacy ID-like columns
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="order_id",
        source_key="orders.order_id",
        payload={"is_categorical": False}
    )
    
    assert entry.statistical_type == "identifier", f"Got {entry.statistical_type}, expected identifier"
