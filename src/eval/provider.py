from src.llms.main_pipeline import run_pipeline
import json
from typing import Any


def _explainer_to_text(obj: Any) -> str:
    """
    Convert various possible langchain/agent return types into a plain string.
    Tries common shapes returned by chains/agents/LLM results and falls back to str().
    """
    if obj is None:
        return ""

    # Already a string
    if isinstance(obj, str):
        return obj

    # Mapping-like objects (dicts)
    if isinstance(obj, dict):
        # common keys used by chains/agents
        for key in ("output", "text", "result", "answer", "content", "response", "data", "return_values"):
            if key in obj:
                return _explainer_to_text(obj[key])
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return str(obj)

    # Sequence of results (list/tuple)
    if isinstance(obj, (list, tuple)):
        parts = [_explainer_to_text(i) for i in obj]
        return "\n\n".join([p for p in parts if p])

    # LangChain LLMResult-like: .generations -> list[list[Generation]] with .text
    if hasattr(obj, "generations"):
        try:
            gens = getattr(obj, "generations")
            if gens and isinstance(gens, list):
                first_gen_list = gens[0]
                if first_gen_list and hasattr(first_gen_list[0], "text"):
                    return first_gen_list[0].text
        except Exception:
            pass

    # AgentFinish-like: .return_values
    if hasattr(obj, "return_values"):
        try:
            return _explainer_to_text(getattr(obj, "return_values"))
        except Exception:
            pass

    # Chat/Message-like objects: .content or .text attributes
    if hasattr(obj, "content"):
        return getattr(obj, "content")
    if hasattr(obj, "text"):
        return getattr(obj, "text")

    # Fallback to string representation
    try:
        return str(obj)
    except Exception:
        return json.dumps(obj, default=str, ensure_ascii=False)


async def call_api(prompt, options, context):
    """
    Promptfoo entrypoint, the function must be called call_api
    """

    model_name = options.get('config').get('model_name')
    local = options.get('config').get('local')

    resulting_df, explainer_results = await run_pipeline(prompt, model_name, local)

    explainer_text = _explainer_to_text(explainer_results)

    return {
        "output": resulting_df.to_markdown() + "\n" + explainer_text
    }

