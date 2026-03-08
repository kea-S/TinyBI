import pandas as pd
from types import SimpleNamespace

import src.main as main_mod


class FakeExtractorRunnable:
    def invoke(self, *args, **kwargs):
        # Return an object with the attributes main.py expects:
        # - persona (used when building explainer input)
        return SimpleNamespace(persona="tester")


class FakeExplainerRunnable:
    def __init__(self):
        self.last_input = None

    def invoke(self, *args, **kwargs):
        # Record the single positional input (main invokes with a single string)
        if args:
            self.last_input = args[0]
        elif "input" in kwargs:
            self.last_input = kwargs["input"]
        else:
            self.last_input = str(kwargs)
        return "explained"


def test_main_end_to_end(monkeypatch, capsys):
    # Prepare a small DataFrame and SQL to be returned by the patched query_tool
    df = pd.DataFrame({"provider": ["p1", "p2"], "bwts": [10, 20]})
    sql = "SELECT provider, AVG(bwts) FROM test_csv GROUP BY provider"

    # Patch main's dependencies (main imports these at module level)
    monkeypatch.setattr(main_mod, "get_extractor", lambda: FakeExtractorRunnable())
    fake_explainer = FakeExplainerRunnable()
    monkeypatch.setattr(main_mod, "get_explainer", lambda: fake_explainer)
    # query_tool in main accepts a single argument (the extractor result)
    monkeypatch.setattr(main_mod, "query_tool", lambda extractor_results: (df, sql))

    # Run the main function (should use the patched pieces and print the DataFrame)
    main_mod.main()

    captured = capsys.readouterr()
    stdout = captured.out

    # Assert the printed output contains the DataFrame header and one of the values
    assert "provider" in stdout
    assert "bwts" in stdout
    assert "p1" in stdout or "10" in stdout

    # Assert explainer received the combined input that includes persona, SQL, and CSV snippet
    assert fake_explainer.last_input is not None
    assert "persona: tester" in fake_explainer.last_input
    assert sql in fake_explainer.last_input
    # CSV conversion of the top rows should include the column header "provider" or "bwts"
    assert "provider" in fake_explainer.last_input or "bwts" in fake_explainer.last_input
