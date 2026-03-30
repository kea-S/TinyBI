import sys
from pathlib import Path

# promptfoo loads this file as a direct module, so add the repo root explicitly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.llms.extractor import get_extractor
from src.utils.pydantic_models import QuerySchema
from src.tools.query_tool import query_tool


async def call_api(prompt, options, context):
    """
    Promptfoo entrypoint, the function must be called call_api
    """

    model_name = options.get('config').get('model_name')
    local = options.get('config').get('local')

    extractor = get_extractor(model_name, local)
    extractor_results: QuerySchema = await extractor.ainvoke(prompt)

    resulting_df, resulting_sql_query = query_tool(extractor_results)

    return {
        "output": resulting_sql_query
    }
