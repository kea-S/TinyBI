import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from src.agent import run_agent
from src.tools.query_tool import query_tool
from src.utils.prompts import EXTRACTOR_PROMPT
from src.utils.models import get_local_llm, get_remote_llm, REMOTE_LLAMA_8B, LOCAL_GRANITE4

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    local: bool = False


class QueryResponse(BaseModel):
    message: str
    sql: Optional[str] = None
    data: Optional[List[dict]] = None


@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_endpoint(request: QueryRequest):
    try:
        if request.local:
            llm = get_local_llm(request.model or LOCAL_GRANITE4)
        else:
            llm = get_remote_llm(request.model or REMOTE_LLAMA_8B)

        # Convert history to LangChain messages
        messages = []
        for msg in request.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))

        result = await run_agent(
            messages,
            llm,
            tools=[query_tool],
            system_prompt=EXTRACTOR_PROMPT
        )

        return QueryResponse(
            message=result["output"],
            sql=result.get("sql"),
            data=result.get("data")
        )

    except Exception as exc:
        logger.exception("Failed to process agentic query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {exc}",
        )

