from src.utils.prompts import EXTRACTOR_PROMPT

from src.utils.models import get_remote_llm, get_local_llm

from src.utils.pydantic_models import QuerySchema

from langchain_core.prompts import ChatPromptTemplate


def get_extractor(model, local):
    model = get_remote_llm(model) if not local else get_local_llm(model)

    model_with_structure = model.with_structured_output(QuerySchema)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACTOR_PROMPT),
        ("user", "{user_message}")
    ])

    chain = prompt | model_with_structure

    return chain
