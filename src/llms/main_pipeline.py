from src.utils.pydantic_models import QuerySchema

from src.llms.explainer import get_explainer
from src.llms.extractor import get_extractor
from src.tools.query_tool import query_tool


def run_pipeline(question):
    extractor = get_extractor()
    extractor_results: QuerySchema = extractor.invoke(question)

    resulting_df, resulting_sql_query = query_tool(extractor_results)

    explainer = get_explainer()

    explainer_input = (
        f"user_message: {question}\n\n"
        f"executed_sql: {resulting_sql_query}\n\n"
        f"data_result: {resulting_df.to_markdown()}\n\n"
        f"persona: {extractor_results.persona}\n\n"
    )

    explainer_results = explainer.invoke(explainer_input)

    return resulting_df, explainer_results
