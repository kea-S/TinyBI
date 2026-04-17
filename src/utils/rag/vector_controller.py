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
    CandidateTables,
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

        # map subject to potential ColumnVectorIndexEntry entities
        subject = structured_query.subject
        subject_embedding = self._embedding_model.embed_query(subject)

        subject_results: list[VectorSearchResult] = \
            self._vector_index.search(subject_embedding, k=3)

        # map metric to potential ColumnVectorIndexEntry entities
        metric = structured_query.metric_hint
        metric_embedding = self._embedding_model.embed_query(metric)

        metric_results: list[VectorSearchResult] = \
            self._vector_index.search(metric_embedding, k=3)

        # map filters to the ground truth columns
        filters: list[FilterIntent] = structured_query.filters
        filter_candidates: list[list[VectorSearchResult]] = []

        for filter in filters:

            # search just using column hint for now, can make better
            # using raw_value_text?
            attribute_hint = filter.attribute_hint
            raw_value_text = filter.raw_value_text

            filter_query = f"""Attribute {attribute_hint} with
                            value {raw_value_text}"""

            filter_embedding = self._embedding_model.embed_query(filter_query)

            attribute_results: list[VectorSearchResult] = \
                self._vector_index.search(filter_embedding, k=3)

            if not attribute_results:
                raise ValueError("No relevant columns found")

            # ideally handle confidence/ logprops cut off inside search
            # select relevant candidates
            filter_group: list[ColumnVectorIndexEntry] = []
            for result in attribute_results:
                index_entry: ColumnVectorIndexEntry = result.entry

                if resolve_filter_literals(filter, index_entry):
                    # if inside the thing
                    filter_group.append(result)

                filter_candidates.append(filter_group)

        # once we've received all the tables that we might need to build
        # the query, we pass responsibility to the query builder tool

        return CandidateTables(
            subject_entries=subject_results,
            metric_entries=metric_results,
            filter_tables=filter_candidates
        )
