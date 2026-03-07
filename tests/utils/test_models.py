import pytest

from src.utils.models import (
    REMOTE_QWEN,
    REMOTE_LLAMA3,
    REMOTE_OPENAI,
    LOCAL_LLAMA3,
)

from src.utils.models import get_remote_llm, get_local_llm

from dotenv import load_dotenv


load_dotenv()


@pytest.mark.parametrize("model_name, local", [
    (REMOTE_LLAMA3, False),
    (REMOTE_QWEN, False),
    (REMOTE_OPENAI, False),
    (LOCAL_LLAMA3, True),
])
def test_langchain_llm_call(model_name, local: bool):
    llm = (get_local_llm(model_name)
           if local else get_remote_llm(model_name))

    try:
        response = llm.invoke("Hello").text
        assert response is not None and len(str(response)) > 0
    except Exception as e:
        pytest.fail(f"LANGCHAIN model '{model_name}' call failed: {e}")
