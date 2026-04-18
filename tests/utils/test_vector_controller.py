from pathlib import Path

from src.utils.pydantic_models import (
    CandidateAttributes,
    ColumnVectorIndexEntry,
    FilterIntent,
    QuerySchema,
    VectorSearchResult,
)
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


def test_get_current_index_entries_returns_persisted_entries(monkeypatch, tmp_path):
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
        ),
        ColumnVectorIndexEntry(
            entry_id=2,
            table_name="orders",
            column_name="order_total",
            source_key="orders.order_total",
        ),
    ]

    controller = VectorController("fake-embedding-model", vector_index_path=tmp_path / "columns")
    controller.batch_insert_index_entries(entries)

    loaded_entries = controller.get_current_index_entries()

    assert [entry.source_key for entry in loaded_entries] == [
        "orders.customer_city",
        "orders.order_total",
    ]


def test_get_current_index_entries_returns_empty_list_when_index_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        vector_controller_module,
        "get_embedding_model",
        lambda _: FakeEmbeddingModel(),
    )

    controller = VectorController("fake-embedding-model", vector_index_path=tmp_path / "missing")

    assert controller.get_current_index_entries() == []


class FakeVectorIndex:
    def __init__(self, search_results):
        self._search_results = search_results
        self._index = True

    def get_connection(self, _path):
        pass

    def search(self, _embedding, k=3):
        return self._search_results.pop(0)


def _make_entry(entry_id, table_name, column_name, **extra):
    defaults = dict(
        entry_id=entry_id,
        table_name=table_name,
        column_name=column_name,
        source_key=f"{table_name}.{column_name}",
    )
    defaults.update(extra)
    return ColumnVectorIndexEntry(**defaults)


def _make_result(entry_id, score, table_name="orders", column_name=None, **extra):
    col = column_name or f"col_{entry_id}"
    entry = _make_entry(entry_id, table_name, column_name=col, **extra)
    return VectorSearchResult(entry=entry, score=score)


class TestRunReturnsDictBasedFilterEntries:
    def test_run_returns_candidate_attributes_with_filter_dict(self, monkeypatch, tmp_path):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        query = QuerySchema(
            subject="customer",
            metric_hint="order total",
            filters=[fi],
        )

        subject_result = _make_result(1, 0.9, column_name="customer")
        metric_result = _make_result(2, 0.85, column_name="order_total")
        filter_result = _make_result(
            3, 0.88, column_name="provider",
            payload={"is_categorical": True, "canonical_values": ["DB Schenker", "SPX"]},
        )

        fake_index = FakeVectorIndex([
            [subject_result],
            [metric_result],
            [filter_result],
        ])

        fake_embedding = FakeEmbeddingModel()

        monkeypatch.setattr(
            vector_controller_module,
            "get_embedding_model",
            lambda _: fake_embedding,
        )
        monkeypatch.setattr(
            vector_controller_module,
            "VectorIndex",
            lambda: fake_index,
        )
        monkeypatch.setattr(
            vector_controller_module,
            "can_resolve_value",
            lambda *_: True,
        )

        controller = VectorController("fake-model", vector_index_path=tmp_path / "idx")
        result = controller.run(query)

        assert isinstance(result, CandidateAttributes)
        assert isinstance(result.filter_entries, dict)
        assert len(result.filter_entries) == 1
        assert fi in result.filter_entries
        assert len(result.filter_entries[fi]) == 1
        assert result.filter_entries[fi][0].entry.column_name == "provider"

    def test_run_with_multiple_filters_returns_dict_with_all_keys(self, monkeypatch, tmp_path):
        fi_provider = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        fi_country = FilterIntent(
            attribute_hint="buyer country",
            operator="IN",
            raw_value_text=["Singapore", "Malaysia"],
        )
        query = QuerySchema(
            subject="customer",
            metric_hint="order total",
            filters=[fi_provider, fi_country],
        )

        subject_result = _make_result(1, 0.9, column_name="customer")
        metric_result = _make_result(2, 0.85, column_name="order_total")
        provider_result = _make_result(3, 0.88, column_name="provider")
        country_result = _make_result(4, 0.92, column_name="buyer_country")

        fake_index = FakeVectorIndex([
            [subject_result],
            [metric_result],
            [provider_result],
            [country_result],
        ])

        fake_embedding = FakeEmbeddingModel()
        monkeypatch.setattr(vector_controller_module, "get_embedding_model", lambda _: fake_embedding)
        monkeypatch.setattr(vector_controller_module, "VectorIndex", lambda: fake_index)
        monkeypatch.setattr(vector_controller_module, "can_resolve_value", lambda *_: True)

        controller = VectorController("fake-model", vector_index_path=tmp_path / "idx")
        result = controller.run(query)

        assert len(result.filter_entries) == 2
        assert fi_provider in result.filter_entries
        assert fi_country in result.filter_entries

    def test_run_skips_filter_where_no_results_resolve(self, monkeypatch, tmp_path):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        query = QuerySchema(
            subject="customer",
            metric_hint="order total",
            filters=[fi],
        )

        subject_result = _make_result(1, 0.9, column_name="customer")
        metric_result = _make_result(2, 0.85, column_name="order_total")

        fake_index = FakeVectorIndex([
            [subject_result],
            [metric_result],
            [],
        ])

        fake_embedding = FakeEmbeddingModel()
        monkeypatch.setattr(vector_controller_module, "get_embedding_model", lambda _: fake_embedding)
        monkeypatch.setattr(vector_controller_module, "VectorIndex", lambda: fake_index)

        controller = VectorController("fake-model", vector_index_path=tmp_path / "idx")
        result = controller.run(query)

        assert len(result.filter_entries) == 0

    def test_run_filters_results_by_can_resolve_value(self, monkeypatch, tmp_path):
        fi = FilterIntent(
            attribute_hint="provider",
            operator="=",
            raw_value_text=["DB Schenker"],
        )
        query = QuerySchema(
            subject="customer",
            metric_hint="order total",
            filters=[fi],
        )

        subject_result = _make_result(1, 0.9, column_name="customer")
        metric_result = _make_result(2, 0.85, column_name="order_total")
        filter_result = _make_result(3, 0.88, column_name="provider")

        fake_index = FakeVectorIndex([
            [subject_result],
            [metric_result],
            [filter_result],
        ])

        call_count = {"n": 0}

        def fake_can_resolve(intent, entry):
            call_count["n"] += 1
            return entry.column_name == "provider"

        fake_embedding = FakeEmbeddingModel()
        monkeypatch.setattr(vector_controller_module, "get_embedding_model", lambda _: fake_embedding)
        monkeypatch.setattr(vector_controller_module, "VectorIndex", lambda: fake_index)
        monkeypatch.setattr(vector_controller_module, "can_resolve_value", fake_can_resolve)

        controller = VectorController("fake-model", vector_index_path=tmp_path / "idx")
        result = controller.run(query)

        assert len(result.filter_entries) == 1
        assert len(result.filter_entries[fi]) == 1
        assert result.filter_entries[fi][0].entry.column_name == "provider"

