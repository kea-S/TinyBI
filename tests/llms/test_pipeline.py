import pandas as pd

import src.main as main_mod


def test_main_end_to_end(monkeypatch, capsys):
    df = pd.DataFrame({"provider": ["p1", "p2"], "bwts": [10, 20]})
    captured_call = {}
    prompts = iter(["Show provider BWTS", "quit"])

    async def fake_run_pipeline(question, model, local):
        captured_call["question"] = question
        captured_call["model"] = model
        captured_call["local"] = local
        return df, "explained"

    monkeypatch.setattr(main_mod, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr("builtins.input", lambda _: next(prompts))

    main_mod.main()

    captured = capsys.readouterr()
    stdout = captured.out

    assert "provider" in stdout
    assert "bwts" in stdout
    assert "p1" in stdout or "10" in stdout
    assert "explained" in stdout
    assert "Goodbye." in stdout
    assert captured_call["question"] == "Show provider BWTS"
    assert captured_call["model"] == main_mod.DEFAULT_MODEL
    assert captured_call["local"] == main_mod.DEFAULT_LOCAL
