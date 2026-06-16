import json
import pytest
from unittest.mock import patch, MagicMock


class TestInsightScorer:
    def test_reads_reference_answer_from_vars(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({
            "output": "There are 4500 accounts in the database.",
            "sql": "SELECT COUNT(*) FROM account",
            "data": [{"count": 4500}],
        })
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        mock_score = 0.85

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=mock_score)
            MockMetric.return_value = mock_instance

            result = insight_scorer(output, context)

            mock_instance.score.assert_called_once_with(
                response="There are 4500 accounts in the database.",
                reference="There are 4500 accounts.",
            )
            assert result["score"] == mock_score

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

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=1.0)
            MockMetric.return_value = mock_instance

            insight_scorer(output, context)

            mock_instance.score.assert_called_once()
            call_kwargs = mock_instance.score.call_args.kwargs
            assert "DECOY" not in call_kwargs["response"]
            assert call_kwargs["response"] == "The answer is 13."

    def test_returns_named_scores_with_ragas_f1(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({"output": "There are 4500 accounts."})
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=0.85)
            MockMetric.return_value = mock_instance

            result = insight_scorer(output, context)

            assert "named_scores" in result
            assert "RAGAS F1" in result["named_scores"]
            assert result["named_scores"]["RAGAS F1"] == 0.85

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

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=1.0)
            MockMetric.return_value = mock_instance

            result = insight_scorer(output, context)

            assert result["score"] == 1.0
            assert result["pass"] is True
            assert result["named_scores"]["RAGAS F1"] == 1.0

    def test_pass_threshold_applied(self):
        from src.eval.insight_scorer import insight_scorer

        output = json.dumps({"output": "There are 3 accounts."})
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=0.3)
            MockMetric.return_value = mock_instance

            result = insight_scorer(output, context)

            assert result["score"] == 0.3
            assert result["pass"] is True
            assert result["named_scores"]["RAGAS F1"] == 0.3

    def test_handles_non_json_output(self):
        from src.eval.insight_scorer import insight_scorer

        output = "There are 4500 accounts."
        context = {
            "vars": {
                "id": "bird-89",
                "reference_answer": "There are 4500 accounts.",
            },
        }

        with patch("src.eval.insight_scorer.FactualCorrectness") as MockMetric:
            mock_instance = MagicMock()
            mock_instance.score.return_value = MagicMock(value=0.9)
            MockMetric.return_value = mock_instance

            result = insight_scorer(output, context)

            mock_instance.score.assert_called_once_with(
                response="There are 4500 accounts.",
                reference="There are 4500 accounts.",
            )
            assert result["score"] == 0.9
