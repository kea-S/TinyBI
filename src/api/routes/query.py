from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from src.utils.models import LOCAL_GRANITE4

from src.llms.extractor import get_extractor
from src.tools.query_tool import query_tool
from src.utils.pydantic_models import QuerySchema

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    model: str | None = None
    local: bool = False


class QueryResponse(BaseModel):
    sql: str
    data: list[dict]


@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_endpoint(request: QueryRequest):
    try:
        extractor = get_extractor(LOCAL_GRANITE4, True)
        query_schema: QuerySchema = await extractor.ainvoke(request.question)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract query schema: {exc}",
        )

    try:
        df, sql = query_tool(query_schema)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute query: {exc}",
        )

    return QueryResponse(sql=sql, data=df.to_dict(orient="records"))
