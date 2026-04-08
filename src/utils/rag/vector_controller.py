from pathlib import Path

from src.utils.rag.vector_index import VectorIndex
from src.utils.models import get_embedding_model
from src.utils.value_resolution.resolution_service import resolve_filter_literals

from src.utils.pydantic_models import (
    BatchColumnVectorIndexResponse,
    ColumnVectorIndexEntry,
    QuerySchema,
    FilterIntent,
    VectorSearchResult,
)
from src.config import APP_DATA_PATH


class VectorController:
    def __init__(self, embedding_model: str, vector_index_path: str | Path = APP_DATA_PATH):
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

    def run(self, structured_query: QuerySchema):
        if self._vector_index._index is None:
            self._vector_index.get_connection(self._vector_index_path)

        # maps filters to the ground truth columns
        filters: list[FilterIntent] = structured_query.filters
        filter_index_entries: ColumnVectorIndexEntry = []

        for filter in filters:
            # search just using column hint for now, can make better
            # using raw_value_text?
            attribute_hint = filter.attribute_hint

            embedding = self._embedding_model.embed_query(attribute_hint)

            search_result = self._vector_index.search(embedding, k=1)

            if not search_result:
                raise ValueError("No relevant columns found")

            search_result: VectorSearchResult = search_result[0]

            index_entry = search_result.entry

            filter_index_entries.append(index_entry)

        # entity match canonical entries in the filters
        resolved_filters: list[FilterIntent] = []
        for filter, index_entry in zip(filters, filter_index_entries):
            resolved_filters.append(
                resolve_filter_literals(filter, index_entry)
            )

        # TODO: run the other schema linking steps that will eventually
        # be passed to the sql builder, including
        # tables for joins
        # columns for selection and metric
        # whatever kind of aggregation you need to do
        # and I think handle filter values better, handle IN and like
        # dates and stuff aswell
        retrievals = self._vector_index.search(
            self.embedding_model.embed_query(structured_query),
            k=5)

        # TODO: do postprocessing to return structured result output
        # that will be ingested by the deterministic SQL builder, for now
        post_processed = {
            "retrievals": retrievals
        }

        return post_processed
