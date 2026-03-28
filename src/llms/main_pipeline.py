from src.utils.pydantic_models import QuerySchema

from src.llms.explainer import get_explainer
from src.llms.extractor import get_extractor
from src.tools.query_tool import query_tool


async def run_pipeline(question, model, local):
    result = await run_pipeline_with_details(question, model, local)
    return result["dataframe"], result["explanation"]


async def run_pipeline_with_details(question, model, local):
    extractor = get_extractor(model, local)
    extractor_results: QuerySchema = await extractor.ainvoke(question)

    resulting_df, resulting_sql_query = query_tool(extractor_results)

    explainer = get_explainer(model, local)

    explainer_input = (
        f"user_message: {question}\n\n"
        f"executed_sql: {resulting_sql_query}\n\n"
        f"data_result: {resulting_df.to_markdown()}\n\n"
        f"persona: {extractor_results.persona}\n\n"
    )

    explainer_results = await explainer.ainvoke(explainer_input)

    return {
        "dataframe": resulting_df,
        "sql": resulting_sql_query,
        "explanation": explainer_results,
        "query_schema": extractor_results,
    }
