import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.prompts import EXTRACTOR_PROMPT
from src.utils.models import get_local_llm, get_remote_llm
from src.utils.pydantic_models import QuerySchema


def _get_llm(model_name: str, local: bool):
    return get_local_llm(model_name) if local else get_remote_llm(model_name)


async def call_api(prompt, options, context):
    """
    Promptfoo entrypoint, the function must be called call_api.
    This experiment invokes the model directly with nested structured output.
    """

    config = options.get("config", {})
    model_name = config.get("model_name")
    local = config.get("local", False)

    llm = _get_llm(model_name, local)
    structured_llm = llm.with_structured_output(QuerySchema)
    result = await structured_llm.ainvoke([
        SystemMessage(content=EXTRACTOR_PROMPT),
        HumanMessage(content=prompt),
    ])

    return {
        "output": result.model_dump_json(indent=2),
        "metadata": {
            "model_name": model_name,
            "local": local,
            "parsed": json.loads(result.model_dump_json()),
        },
    }

