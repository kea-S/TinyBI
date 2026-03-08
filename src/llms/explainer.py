from src.utils.prompts import EXPLAINER_PROMPT

from src.utils.models import REMOTE_OPENAI
from src.utils.models import get_remote_llm

from langchain_core.prompts import ChatPromptTemplate


def get_explainer():
    model = get_remote_llm(REMOTE_OPENAI)

    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAINER_PROMPT),
        ("user", "{input}")
    ])

    chain = prompt | model

    return chain
