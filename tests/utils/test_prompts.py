from src.utils.prompts import EXTRACTOR_PROMPT


def test_extractor_prompt_directs_post_tool_answer():
    assert "After calling the tool" in EXTRACTOR_PROMPT
    assert "natural-language answer" in EXTRACTOR_PROMPT


def test_extractor_prompt_grounds_answer_in_data():
    assert "based on" in EXTRACTOR_PROMPT.lower()
    assert "data" in EXTRACTOR_PROMPT.lower()
