from pathlib import Path

from src.utils.pydantic_models import ColumnVectorIndexEntry
from src.utils.rag import vector_controller as vector_controller_module
from src.utils.rag.vector_controller import VectorController


class FakeEmbeddingModel:
    def __init__(self):
        self.document_inputs = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_inputs.append(texts)
        return [[1.0, 0.0], [0.0, 1.0]]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


def test_batch_insert_index_entries_builds_and_persists_index(monkeypatch, tmp_path):
    fake_embedding_model = FakeEmbeddingModel()
    monkeypatch.setattr(
        vector_controller_module,
        "get_embedding_model",
        lambda _: fake_embedding_model,
    )

    entries = [
        ColumnVectorIndexEntry(
            entry_id=1,
            table_name="orders",
            column_name="customer_city",
            source_key="orders.customer_city",
            description="Customer city",
        ),
        ColumnVectorIndexEntry(
            entry_id=2,
            table_name="orders",
            column_name="order_total",
            source_key="orders.order_total",
            description="Order total",
        ),
    ]

    index_path = tmp_path / "columns"
    controller = VectorController("fake-embedding-model", vector_index_path=index_path)

    response = controller.batch_insert_index_entries(entries)

    assert fake_embedding_model.document_inputs == [[entry.to_embedding_text() for entry in entries]]
    assert response.embedding_model == "fake-embedding-model"
    assert response.entry_count == 2
    assert response.table_names == ["orders"]
    assert Path(response.vector_index_path).exists()
    assert Path(response.metadata_path).exists()


def test_batch_insert_index_entries_requires_non_empty_entries(monkeypatch, tmp_path):
    monkeypatch.setattr(
        vector_controller_module,
        "get_embedding_model",
        lambda _: FakeEmbeddingModel(),
    )

    controller = VectorController("fake-embedding-model", vector_index_path=tmp_path / "columns")

    try:
        controller.batch_insert_index_entries([])
    except ValueError as exc:
        assert "At least one ColumnVectorIndexEntry is required" in str(exc)
    else:
        raise AssertionError("Expected batch_insert_index_entries to reject an empty batch")
