import json
import pytest
from unittest.mock import patch, MagicMock


class TestInsightScorer:
    def test_reads_reference_answer_and_query_from_vars(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({
            "output": "There are 4500 accounts in the database.",
            "sql": "SELECT COUNT(*) FROM account",
            "data": [{"count": 4500}],
        })
        context = {
            "vars": {
                "id": "bird-89",
                "query": "How many accounts are in East Bohemia?",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=0.85)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=1.0)
            MockAccuracy.return_value = accuracy_mock

            result = insight_scorer(output, context)

            factual_mock.score.assert_called_once_with(
                response="There are 4500 accounts in the database.",
                reference="There are 4500 accounts.",
            )
            accuracy_mock.score.assert_called_once_with(
                user_input="How many accounts are in East Bohemia?",
                response="There are 4500 accounts in the database.",
                reference="There are 4500 accounts.",
            )
            assert result["score"] == 1.0

    def test_ignores_sql_and_data_fields(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({
            "output": "The answer is 13.",
            "sql": "DECOY SQL TEXT THAT MUST NOT BE SCORED",
            "data": [{"decoy": "DECOY DATA THAT MUST NOT BE SCORED"}],
        })
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "The answer is 13.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=1.0)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=1.0)
            MockAccuracy.return_value = accuracy_mock

            insight_scorer(output, context)

            call_kwargs = factual_mock.score.call_args.kwargs
            assert "DECOY" not in call_kwargs["response"]
            assert call_kwargs["response"] == "The answer is 13."

    def test_returns_both_named_scores(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({"output": "There are 4500 accounts."})
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=0.85)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=0.75)
            MockAccuracy.return_value = accuracy_mock

            result = insight_scorer(output, context)

            assert "named_scores" in result
            assert result["named_scores"]["RAGAS Precision"] == 0.85
            assert result["named_scores"]["Answer Accuracy"] == 0.75
            assert result["score"] == 0.75

    def test_raises_on_missing_reference_answer(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({"output": "Some answer."})
        context = {
            "vars": {"id": "bird-99"},
        }

        with pytest.raises(KeyError, match="reference_answer not found"):
            insight_scorer(output, context)

    def test_handles_identical_answers(self):
        from src.eval.insight_scorer import insight_scorer

        answer = "There are 4500 accounts in East Bohemia region."
        output = json.dumps({"output": answer})
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": answer,
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=1.0)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=1.0)
            MockAccuracy.return_value = accuracy_mock

            result = insight_scorer(output, context)

            assert result["score"] == 1.0
            assert result["pass"] is True
            assert result["named_scores"]["RAGAS Precision"] == 1.0
            assert result["named_scores"]["Answer Accuracy"] == 1.0

    def test_low_answer_accuracy_flows_to_score(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({"output": "There are 3 accounts."})
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=0.5)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=0.25)
            MockAccuracy.return_value = accuracy_mock

            result = insight_scorer(output, context)

            assert result["score"] == 0.25
            assert result["pass"] is True
            assert result["named_scores"]["RAGAS Precision"] == 0.5
            assert result["named_scores"]["Answer Accuracy"] == 0.25

    def test_handles_non_json_output(self):
        from src.eval.insight_scorer import insight_scorer

        output = "There are 4500 accounts."
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockFactual, \
             patch("src.eval.insight_scorer.AnswerAccuracy") as MockAccuracy:
            factual_mock = MagicMock()
            factual_mock.score.return_value = MagicMock(value=0.9)
            MockFactual.return_value = factual_mock

            accuracy_mock = MagicMock()
            accuracy_mock.score.return_value = MagicMock(value=0.9)
            MockAccuracy.return_value = accuracy_mock

            result = insight_scorer(output, context)

            factual_mock.score.assert_called_once_with(
                response="There are 4500 accounts.",
                reference="There are 4500 accounts.",
            )
            assert result["score"] == 0.9
            assert result["named_scores"]["Answer Accuracy"] == 0.9
