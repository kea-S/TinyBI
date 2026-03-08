from src.utils.models import REMOTE_OPENAI
from src.utils.models import get_remote_llm

from src.utils.pydantic_models import QuerySchema

model = get_remote_llm(REMOTE_OPENAI)

model_with_structure = model.with_structured_output(QuerySchema)

response = model_with_structure.invoke("What is the average BWT amongst the logistics providers in Malaysia?")

print(response)
