from fastapi import APIRouter, HTTPException, status

from src.utils.models import (
    DEFAULT_EMBEDDING_MODEL,
    get_embedding_model_name_from_key,
)
from src.utils.pydantic_models import (
    BatchColumnVectorIndexEntriesRequest,
    BatchColumnVectorIndexResponse,
)
from src.utils.rag.vector_controller import VectorController

router = APIRouter(prefix="/vector", tags=["vector"])


def _build_index(
    entries_request: BatchColumnVectorIndexEntriesRequest,
    embedding_model: str,
) -> BatchColumnVectorIndexResponse:
    try:
        controller = VectorController(embedding_model)
        return controller.batch_insert_index_entries(entries_request.entries)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/index-entries/batch",
    response_model=BatchColumnVectorIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Build the active vector index with the default embedding model",
)
def batch_insert_index_entries_default(
    request: BatchColumnVectorIndexEntriesRequest,
) -> BatchColumnVectorIndexResponse:
    return _build_index(request, DEFAULT_EMBEDDING_MODEL)


@router.post(
    "/index-entries/batch/by-model/{embedding_model_key}",
    response_model=BatchColumnVectorIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Build the active vector index with a specific embedding model",
)
def batch_insert_index_entries_by_model(
    embedding_model_key: str,
    request: BatchColumnVectorIndexEntriesRequest,
) -> BatchColumnVectorIndexResponse:
    try:
        embedding_model = get_embedding_model_name_from_key(embedding_model_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _build_index(request, embedding_model)
