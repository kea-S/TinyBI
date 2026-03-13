from src.utils.prompts import EXPLAINER_PROMPT

from src.utils.models import get_remote_llm, get_local_llm

from langchain_core.prompts import ChatPromptTemplate


def get_explainer(model, local):
    model = get_remote_llm(model) if not local else get_local_llm(model)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAINER_PROMPT),
        ("user", "{input}")
    ])

    chain = prompt | model

    return chain
