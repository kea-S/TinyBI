import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pandas as pd

from src.api.main import create_app
from src.api.routes import query as query_routes
from src.utils.pydantic_models import (
    ColumnVectorIndexEntry,
    FinalAttributes,
    FilterIntent,
    QuerySchema,
)


class FakeExtractor:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, question):
        return self._result


def _fake_final_attrs():
    return (
        FinalAttributes(
            subject_entries=[
                ColumnVectorIndexEntry(
                    entry_id=0,
                    table_name="orders",
                    column_name="provider",
                    source_key="orders.provider",
                )
            ],
            metric_entry=ColumnVectorIndexEntry(
                entry_id=1,
                table_name="orders",
                column_name="order_value",
                source_key="orders.order_value",
            ),
            filter_entries={},
        ),
        "orders",
    )


def test_query_endpoint_returns_sql_and_data(monkeypatch):
    expected_schema = QuerySchema(
        subject="provider",
        metric_hint="order value",
        aggregation="sum",
    )

    fake_df = pd.DataFrame({"provider": ["SPX"], "total": [100]})

    monkeypatch.setattr(
        query_routes, "get_extractor",
        lambda model, local: FakeExtractor(expected_schema),
    )
    monkeypatch.setattr(
        query_routes, "query_tool",
        lambda structured_query, dataset_path=None: (fake_df, "SELECT provider FROM orders"),
    )

    client = TestClient(create_app())
    response = client.post("/query", json={"question": "show me providers by order value"})

    assert response.status_code == 200
    body = response.json()
    assert "sql" in body
    assert body["sql"] == "SELECT provider FROM orders"
    assert "data" in body
    assert len(body["data"]) == 1


def test_query_endpoint_with_filters(monkeypatch):
    fi = FilterIntent(
        attribute_hint="provider",
        operator="IN",
        raw_value_text=("DB Schenker", "SPX"),
    )
    expected_schema = QuerySchema(
        subject="provider",
        metric_hint="order value",
        aggregation="sum",
        filters=[fi],
    )

    fake_df = pd.DataFrame({"provider": ["DB Schenker", "SPX"], "total": [50, 150]})

    monkeypatch.setattr(
        query_routes, "get_extractor",
        lambda model, local: FakeExtractor(expected_schema),
    )
    monkeypatch.setattr(
        query_routes, "query_tool",
        lambda structured_query, dataset_path=None: (
            fake_df,
            "SELECT provider, SUM(order_value) FROM orders WHERE provider IN ('DB Schenker', 'SPX') GROUP BY provider",
        ),
    )

    client = TestClient(create_app())
    response = client.post("/query", json={"question": "show DB Schenker and SPX order values"})

    assert response.status_code == 200
    body = response.json()
    assert "WHERE" in body["sql"]
    assert len(body["data"]) == 2


def test_query_endpoint_handles_extractor_error(monkeypatch):
    class FailingExtractor:
        async def ainvoke(self, question):
            raise RuntimeError("LLM service unavailable")

    monkeypatch.setattr(
        query_routes, "get_extractor",
        lambda model, local: FailingExtractor(),
    )

    client = TestClient(create_app())
    response = client.post("/query", json={"question": "anything"})

    assert response.status_code == 500