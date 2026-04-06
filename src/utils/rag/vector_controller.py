from pathlib import Path

from src.utils.rag.vector_index import VectorIndex
from src.utils.models import get_embedding_model

from src.utils.pydantic_models import (
    BatchColumnVectorIndexResponse,
    ColumnVectorIndexEntry,
)
from src.config import VECTOR_INDEX_PATH


class VectorController:
    def __init__(self, embedding_model: str, vector_index_path: str | Path = VECTOR_INDEX_PATH):
        self._vector_index = VectorIndex()
        self._embedding_model_name = embedding_model
        self._embedding_model = get_embedding_model(embedding_model)
        self._vector_index_path = Path(vector_index_path)

    def batch_insert_index_entries(
        self,
        entries: list[ColumnVectorIndexEntry],
    ) -> BatchColumnVectorIndexResponse:
        if not entries:
            raise ValueError("At least one ColumnVectorIndexEntry is required to build the index")

        entry_texts = [entry.to_embedding_text() for entry in entries]
        embedded_docs = self._embedding_model.embed_documents(entry_texts)

        self._vector_index.build_index(
            entries,
            embedded_docs,
            self._vector_index_path,
        )

        index_path, metadata_path = VectorIndex.resolve_paths(self._vector_index_path)
        table_names = sorted({entry.table_name for entry in entries})

        return BatchColumnVectorIndexResponse(
            embedding_model=self._embedding_model_name,
            entry_count=len(entries),
            table_names=table_names,
            vector_index_path=str(index_path),
            metadata_path=str(metadata_path),
        )

    def get_current_index_entries(self) -> list[ColumnVectorIndexEntry]:
        index_path, metadata_path = VectorIndex.resolve_paths(self._vector_index_path)
        if not index_path.exists() and not metadata_path.exists():
            return []

        self._vector_index.get_connection(self._vector_index_path)
        return self._vector_index.list_entries()

    def run(self, structured_query):
        if self._vector_index._index is None:
            self._vector_index.get_connection(self._vector_index_path)

        # TODO: Extract structured query and inject more knowledge from
        # the structure, fow now just
        query = structured_query

        query_embedding = self._embedding_model.embed_query(query)

        retrievals = self._vector_index.search(query_embedding, k=5)

        # TODO: do postprocessing to return structured result output
        # that will be ingested by the deterministic SQL builder, for now
        post_processed = {
            "retrievals": retrievals
        }

        return post_processed

