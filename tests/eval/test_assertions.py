import pytest
from src.eval.assertions import promptfoo_execution_accuracy
import pandas as pd
from unittest.mock import patch, MagicMock

def test_promptfoo_execution_accuracy_pass():
    output = '{"metadata": {"parsed_sql": "SELECT * FROM users"}}'
    context = {"vars": {"expected_sql": "SELECT * FROM users"}, "prompt": "how many users"}

    with patch("src.eval.assertions.get_df_from_output") as mock_get_df:
        mock_get_df.return_value = pd.DataFrame({"id": [1]})

        with patch("src.eval.assertions.check_execution_accuracy") as mock_check:
            mock_check.return_value = True

            result = promptfoo_execution_accuracy(output, context)

            assert result["pass"] is True
            assert result["score"] == 1.0

def test_promptfoo_execution_accuracy_fail():
    output = '{"metadata": {"parsed_sql": "SELECT * FROM users"}}'
    context = {"vars": {"expected_sql": "SELECT * FROM admins"}, "prompt": "list admins"}

    with patch("src.eval.assertions.get_df_from_output") as mock_get_df:
        mock_get_df.return_value = pd.DataFrame({"id": [1]})

        with patch("src.eval.assertions.check_execution_accuracy") as mock_check:
            mock_check.return_value = False

            result = promptfoo_execution_accuracy(output, context)

            assert result["pass"] is False
            assert result["score"] == 0.0
