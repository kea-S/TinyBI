import pandas as pd
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool

from src.baselines.raw_query_tool import execute_raw_query, raw_query_tool


class TestExecuteRawQuery:
    def test_valid_select_returns_df_and_sql(self, monkeypatch):
        expected_df = pd.DataFrame({"provider": ["SPX", "DB Schenker"], "total": [100, 200]})
        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            lambda sql: expected_df,
        )

        sql = 'SELECT provider, SUM(order_value) AS total FROM orders GROUP BY provider'
        df, returned_sql = execute_raw_query(sql)

        assert returned_sql == sql
        assert df.equals(expected_df)

    def test_limit_preserved(self, monkeypatch):
        captured_sql = {}
        def mock_query(sql):
            captured_sql["sql"] = sql
            return pd.DataFrame()

        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            mock_query,
        )

        execute_raw_query("SELECT a FROM t LIMIT 5")
        assert captured_sql["sql"] == "SELECT a FROM t LIMIT 5"

    def test_non_select_raises(self, monkeypatch):
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_raw_query("DROP TABLE orders")

    def test_insert_rejected(self, monkeypatch):
        with pytest.raises(ValueError, match="Only SELECT"):
            execute_raw_query("INSERT INTO t VALUES (1)")

    def test_with_cte_allowed(self, monkeypatch):
        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            lambda sql: pd.DataFrame(),
        )

        df, sql = execute_raw_query("WITH cte AS (SELECT 1) SELECT * FROM cte")
        assert sql == "WITH cte AS (SELECT 1) SELECT * FROM cte"

    def test_explain_allowed(self, monkeypatch):
        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            lambda sql: pd.DataFrame(),
        )

        df, sql = execute_raw_query("EXPLAIN SELECT 1")
        assert sql == "EXPLAIN SELECT 1"

    def test_db_error_propagates(self, monkeypatch):
        def raise_error(sql):
            raise RuntimeError("Table does not exist")

        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            raise_error,
        )

        with pytest.raises(RuntimeError, match="Table does not exist"):
            execute_raw_query("SELECT * FROM nonexistent")


class TestRawQueryToolLangChain:
    def test_tool_has_correct_name(self):
        assert raw_query_tool.name == "raw_query_tool"

    def test_invoke_returns_content_string(self, monkeypatch):
        df = pd.DataFrame({"provider": ["SPX"], "total": [100]})
        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            lambda sql: df,
        )

        sql = "SELECT provider, SUM(order_value) FROM orders GROUP BY provider"
        content = raw_query_tool.invoke({"sql": sql})

        assert isinstance(content, str)
        assert sql in content
        assert "|" in content  # markdown table

    def test_invoke_empty_result(self, monkeypatch):
        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            lambda sql: pd.DataFrame(),
        )

        content = raw_query_tool.invoke({"sql": "SELECT a FROM t WHERE 1=0"})
        assert "No data found" in content

    def test_invoke_non_select_error(self, monkeypatch):
        content = raw_query_tool.invoke({"sql": "DROP TABLE orders"})
        assert "error" in content.lower()

    def test_invoke_db_error(self, monkeypatch):
        def raise_error(sql):
            raise RuntimeError("Table does not exist")

        monkeypatch.setattr(
            "src.baselines.raw_query_tool.global_database.query",
            raise_error,
        )

        content = raw_query_tool.invoke({"sql": "SELECT * FROM nonexistent"})
        assert "error" in content.lower()
        assert "Table does not exist" in content



