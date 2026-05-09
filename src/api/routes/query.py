import logging

from fastapi import APIRouter, HTTPException, status
# from langchain_core.messages import AIMessage
from pydantic import BaseModel

# from src.llms.explainer import get_explainer
from src.llms.extractor import get_extractor
from src.tools.query_tool import query_tool
from src.utils.models import LOCAL_GRANITE4
from src.utils.pydantic_models import QuerySchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    model: str | None = None
    local: bool = False


class QueryResponse(BaseModel):
    sql: str
    data: list[dict]
    explanation: str | None = None


@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_endpoint(request: QueryRequest):
    try:
        extractor = get_extractor(LOCAL_GRANITE4, True)
        query_schema: QuerySchema = await extractor.ainvoke(request.question)
        logger.info("Extracted schema: %s", query_schema.model_dump(mode="json"))
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

    # -------------------------------------------------------
    # Explainer disabled.
    # try:
    #     explainer = get_explainer(LOCAL_GRANITE4, True)
    #     explainer_input = (
    #         f"user_message: {request.question}\n\n"
    #         f"executed_sql: {sql}\n\n"
    #         f"data_result: {df.to_markdown()}\n\n"
    #     )
    #     explanation = await explainer.ainvoke(explainer_input)
    #     if isinstance(explanation, AIMessage):
    #         explanation = explanation.content
    # except Exception as exc:
    #     logger.warning("Explainer failed — returning result without explanation: %s", exc)
    #     explanation = None
    # -------------------------------------------------------
    explanation = None

    return QueryResponse(sql=sql, data=df.to_dict(orient="records"), explanation=explanation)
