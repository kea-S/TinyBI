import json
from pathlib import Path
from typing import Iterable

import faiss
import numpy as np

from src.utils.pydantic_models import ColumnVectorIndexEntry, VectorSearchResult


class VectorIndex:
    def __init__(self):
        self._entries: dict[int, ColumnVectorIndexEntry] = {}
        self._index = None
        self._index_path: Path | None = None
        self._metadata_path: Path | None = None
        self._dimension: int | None = None

    @staticmethod
    def _coerce_float32_matrix(vectors) -> np.ndarray:
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError("Expected a 2D array of embeddings")
        if matrix.shape[0] == 0:
            raise ValueError("At least one embedding is required to build the index")
        return matrix

    @staticmethod
    def _coerce_float32_query(vector) -> np.ndarray:
        query = np.asarray(vector, dtype=np.float32)
        if query.ndim == 1:
            query = query.reshape(1, -1)
        if query.ndim != 2 or query.shape[0] != 1:
            raise ValueError("Expected a single embedding vector")
        return query

    @staticmethod
    def _normalise(vectors: np.ndarray) -> np.ndarray:
        output = np.array(vectors, dtype=np.float32, copy=True)
        faiss.normalize_L2(output)
        return output

    @staticmethod
    def _resolve_paths(vector_index_path: str | Path) -> tuple[Path, Path]:
        raw_path = Path(vector_index_path)

        if raw_path.suffix == ".faiss":
            index_path = raw_path
            metadata_path = raw_path.with_suffix(".json")
        elif raw_path.suffix == ".json":
            metadata_path = raw_path
            index_path = raw_path.with_suffix(".faiss")
        elif raw_path.exists() and raw_path.is_dir():
            index_path = raw_path / "columns.faiss"
            metadata_path = raw_path / "columns.json"
        elif raw_path.suffix:
            index_path = raw_path
            metadata_path = raw_path.with_suffix(".json")
        else:
            index_path = raw_path.with_suffix(".faiss")
            metadata_path = raw_path.with_suffix(".json")

        return index_path, metadata_path

    @staticmethod
    def _ensure_parent_exists(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_entries(entries: list[ColumnVectorIndexEntry], vector_count: int) -> None:
        if len(entries) != vector_count:
            raise ValueError("Number of entries must match the number of embeddings")

        entry_ids = [entry.entry_id for entry in entries]
        if len(set(entry_ids)) != len(entry_ids):
            raise ValueError("Each entry_id must be unique")

    @staticmethod
    def _serialise_entries(entries: Iterable[ColumnVectorIndexEntry]) -> list[dict]:
        return [entry.model_dump(mode="json") for entry in entries]

    def get_connection(self, vector_index_path: str | Path):
        index_path, metadata_path = self._resolve_paths(vector_index_path)
        self._index_path = index_path
        self._metadata_path = metadata_path

        if index_path.exists():
            self._index = faiss.read_index(str(index_path))
            self._dimension = self._index.d

        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self._entries = {
                item["entry_id"]: ColumnVectorIndexEntry.model_validate(item)
                for item in metadata
            }

        return self

    def build_index(
        self,
        entries: list[ColumnVectorIndexEntry],
        embeddings,
        vector_index_path: str | Path | None = None,
    ):
        if vector_index_path is not None:
            self.get_connection(vector_index_path)

        matrix = self._coerce_float32_matrix(embeddings)
        self._validate_entries(entries, matrix.shape[0])

        normalised_vectors = self._normalise(matrix)
        ids = np.asarray([entry.entry_id for entry in entries], dtype=np.int64)

        base_index = faiss.IndexFlatIP(normalised_vectors.shape[1])
        index = faiss.IndexIDMap2(base_index)
        index.add_with_ids(normalised_vectors, ids)

        self._index = index
        self._entries = {entry.entry_id: entry for entry in entries}
        self._dimension = normalised_vectors.shape[1]

        if self._index_path is not None and self._metadata_path is not None:
            self.persist()

        return self

    def persist(self) -> None:
        if self._index is None:
            raise RuntimeError("Build or load an index before persisting it")
        if self._index_path is None or self._metadata_path is None:
            raise RuntimeError("Call get_connection(path) before persisting the index")

        self._ensure_parent_exists(self._index_path)
        self._ensure_parent_exists(self._metadata_path)

        faiss.write_index(self._index, str(self._index_path))
        self._metadata_path.write_text(
            json.dumps(self._serialise_entries(self._entries.values()), indent=2),
            encoding="utf-8",
        )

    def search(self, query_embedding, k: int = 5, table_name: str | None = None) -> list[VectorSearchResult]:
        if self._index is None:
            raise RuntimeError("Build or load an index before searching")
        if k < 1:
            raise ValueError("k must be at least 1")

        query = self._coerce_float32_query(query_embedding)
        if self._dimension is not None and query.shape[1] != self._dimension:
            raise ValueError(
                f"Query dimension {query.shape[1]} does not match index dimension {self._dimension}"
            )

        query = self._normalise(query)
        candidate_count = min(max(k * 5, k), len(self._entries))
        scores, ids = self._index.search(query, candidate_count)

        results: list[VectorSearchResult] = []
        for score, entry_id in zip(scores[0], ids[0]):
            if entry_id < 0:
                continue

            entry = self._entries.get(int(entry_id))
            if entry is None:
                continue
            if table_name is not None and entry.table_name != table_name:
                continue

            results.append(VectorSearchResult(entry=entry, score=float(score)))
            if len(results) == k:
                break

        return results

    def close_connection(self):
        self._entries = {}
        self._index = None
        self._index_path = None
        self._metadata_path = None
        self._dimension = None


schema_index = VectorIndex()

