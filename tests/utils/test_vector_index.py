import numpy as np
import pytest

faiss = pytest.importorskip("faiss")

from src.utils.pydantic_models import ColumnVectorIndexEntry
from src.utils.rag.vector_index import VectorIndex


def test_column_vector_index_entry_renders_embedding_text():
    entry = ColumnVectorIndexEntry(
        entry_id=1,
        table_name="orders",
        column_name="customer_city",
        source_key="orders.customer_city",
        description="City where the order was placed",
        aliases=["city", "customer city"],
        sample_values=["Berlin", "Munich"],
        payload={"data_type": "text", "is_groupable": True},
    )

    text = entry.to_embedding_text()

    assert "Table: orders" in text
    assert "Column: customer_city" in text
    assert "Aliases: city, customer city" in text
    assert "Sample values: Berlin, Munich" in text
    assert "Data Type: text" in text
    assert "Is Groupable: True" in text


def test_vector_index_builds_persists_and_hydrates_results(tmp_path):
    entries = [
        ColumnVectorIndexEntry(
            entry_id=10,
            table_name="orders",
            column_name="customer_city",
            source_key="orders.customer_city",
            description="Customer city",
            aliases=["city"],
            sample_values=["Berlin", "Munich"],
        ),
        ColumnVectorIndexEntry(
            entry_id=20,
            table_name="orders",
            column_name="order_total",
            source_key="orders.order_total",
            description="Order value in local currency",
            aliases=["total", "revenue"],
            sample_values=["100.50", "250.00"],
        ),
    ]

    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )

    index_path = tmp_path / "column_index"
    index = VectorIndex()
    index.build_index(entries=entries, embeddings=embeddings, vector_index_path=index_path)

    loaded_index = VectorIndex().get_connection(index_path)
    results = loaded_index.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), k=1)

    assert len(results) == 1
    assert results[0].entry.source_key == "orders.customer_city"
    assert results[0].entry.sample_values == ["Berlin", "Munich"]
    assert results[0].score == pytest.approx(1.0, rel=1e-5)


def test_vector_index_can_filter_results_by_table_name(tmp_path):
    entries = [
        ColumnVectorIndexEntry(
            entry_id=1,
            table_name="orders",
            column_name="customer_city",
            source_key="orders.customer_city",
        ),
        ColumnVectorIndexEntry(
            entry_id=2,
            table_name="customers",
            column_name="customer_city",
            source_key="customers.customer_city",
        ),
    ]

    embeddings = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
        ],
        dtype=np.float32,
    )

    index = VectorIndex()
    index.build_index(entries=entries, embeddings=embeddings, vector_index_path=tmp_path / "shared")

    results = index.search(np.array([1.0, 0.0], dtype=np.float32), k=2, table_name="customers")

    assert len(results) == 1
    assert results[0].entry.table_name == "customers"
