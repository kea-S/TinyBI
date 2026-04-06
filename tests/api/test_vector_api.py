import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.routes import vector as vector_routes
from src.utils.pydantic_models import BatchColumnVectorIndexResponse


class FakeVectorController:
    def __init__(self, embedding_model: str):
        self.embedding_model = embedding_model

    def batch_insert_index_entries(self, entries):
        return BatchColumnVectorIndexResponse(
            embedding_model=self.embedding_model,
            entry_count=len(entries),
            table_names=sorted({entry.table_name for entry in entries}),
            vector_index_path="/tmp/columns.faiss",
            metadata_path="/tmp/columns.json",
        )


def test_batch_insert_index_entries_endpoint(monkeypatch):
    monkeypatch.setattr(vector_routes, "VectorController", FakeVectorController)
    client = TestClient(create_app())

    response = client.post(
        "/vector/index-entries/batch",
        json={
            "entries": [
                {
                    "entry_id": 1,
                    "table_name": "orders",
                    "column_name": "customer_city",
                    "source_key": "orders.customer_city",
                    "description": "Customer city",
                    "aliases": ["city"],
                    "sample_values": ["Berlin"],
                    "payload": {"data_type": "text"},
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "embedding_model": "nomic-embed-text",
        "entry_count": 1,
        "table_names": ["orders"],
        "vector_index_path": "/tmp/columns.faiss",
        "metadata_path": "/tmp/columns.json",
    }


def test_batch_insert_index_entries_qwen3_endpoint(monkeypatch):
    monkeypatch.setattr(vector_routes, "VectorController", FakeVectorController)
    client = TestClient(create_app())

    response = client.post(
        "/vector/index-entries/batch/by-model/qwen3",
        json={
            "entries": [
                {
                    "entry_id": 1,
                    "table_name": "orders",
                    "column_name": "customer_city",
                    "source_key": "orders.customer_city",
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["embedding_model"] == "qwen3-embedding:0.6b"


def test_batch_insert_index_entries_endpoint_rejects_unknown_model_key(monkeypatch):
    monkeypatch.setattr(vector_routes, "VectorController", FakeVectorController)
    client = TestClient(create_app())

    response = client.post(
        "/vector/index-entries/batch/by-model/not-a-model",
        json={
            "entries": [
                {
                    "entry_id": 1,
                    "table_name": "orders",
                    "column_name": "customer_city",
                    "source_key": "orders.customer_city",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "Unsupported embedding model key" in response.json()["detail"]


def test_batch_insert_index_entries_endpoint_rejects_empty_batches():
    client = TestClient(create_app())

    response = client.post(
        "/vector/index-entries/batch",
        json={"entries": []},
    )

    assert response.status_code == 422
