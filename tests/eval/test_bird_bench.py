import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from src.eval.bird_bench import check_execution_accuracy

def test_check_execution_accuracy_matches(monkeypatch):
    # Setup
    df_output = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    gold_df = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    
    mock_db = MagicMock()
    mock_db.query.return_value = gold_df
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "SELECT * FROM gold")
    assert result is True
    assert mock_db.query.called

def test_check_execution_accuracy_mismatch_content(monkeypatch):
    # Setup
    df_output = pd.DataFrame({"id": [1, 2], "val": ["A", "C"]}) # Different value
    gold_df = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    
    mock_db = MagicMock()
    mock_db.query.return_value = gold_df
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "SELECT * FROM gold")
    assert result is False

def test_check_execution_accuracy_mismatch_length(monkeypatch):
    # Setup
    df_output = pd.DataFrame({"id": [1]}) # Different length
    gold_df = pd.DataFrame({"id": [1, 2]})
    
    mock_db = MagicMock()
    mock_db.query.return_value = gold_df
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "SELECT * FROM gold")
    assert result is False

def test_check_execution_accuracy_empty_matches(monkeypatch):
    # Setup
    df_output = pd.DataFrame()
    gold_df = pd.DataFrame()
    
    mock_db = MagicMock()
    mock_db.query.return_value = gold_df
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "SELECT * FROM gold")
    assert result is True

def test_check_execution_accuracy_robust_to_column_order(monkeypatch):
    # Setup
    df_output = pd.DataFrame({"val": ["A", "B"], "id": [1, 2]}) # Swapped columns
    gold_df = pd.DataFrame({"id": [1, 2], "val": ["A", "B"]})
    
    mock_db = MagicMock()
    mock_db.query.return_value = gold_df
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "SELECT * FROM gold")
    # Note: Current implementation in bird_bench.py uses df.columns for sorting.
    # If columns differ in order, sort_values(by=list(df.columns)) might produce different results
    # unless we sort columns themselves first.
    # Let's see if it passes.
    assert result is True

def test_check_execution_accuracy_gold_fails(monkeypatch):
    # Setup
    df_output = pd.DataFrame({"id": [1]})
    
    mock_db = MagicMock()
    mock_db.query.side_effect = Exception("SQL Error")
    monkeypatch.setattr("src.eval.bird_bench.global_database", mock_db)
    
    # Test
    result = check_execution_accuracy(df_output, "BAD SQL")
    assert result is False
