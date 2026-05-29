import json
import math
from datetime import date, datetime

import pandas as pd
import pytest

from src.eval.provider import BenchmarkEncoder as ProviderEncoder
from src.eval.extractor_provider import BenchmarkEncoder as ExtractorEncoder

ENCODERS = [
    ("provider", ProviderEncoder),
    ("extractor", ExtractorEncoder),
]


def _assert_serializes(expected_val, obj, encoder_cls):
    result = json.loads(json.dumps(obj, cls=encoder_cls))
    assert result == expected_val, (
        f"{encoder_cls.__module__}: expected {expected_val!r}, got {result!r}"
    )


# --- NaN / Inf floats ---

@pytest.mark.parametrize("name,cls", ENCODERS)
def test_nan_float_serializes_to_null(name, cls):
    _assert_serializes({"val": None}, {"val": float("nan")}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_inf_float_serializes_to_null(name, cls):
    _assert_serializes({"val": None}, {"val": float("inf")}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_neg_inf_float_serializes_to_null(name, cls):
    _assert_serializes({"val": None}, {"val": float("-inf")}, cls)


# --- pd.NA ---

@pytest.mark.parametrize("name,cls", ENCODERS)
def test_pd_na_serializes_to_null(name, cls):
    _assert_serializes({"val": None}, {"val": pd.NA}, cls)


# --- pd.NaT ---

@pytest.mark.parametrize("name,cls", ENCODERS)
def test_pd_nat_serializes_to_null(name, cls):
    _assert_serializes({"val": None}, {"val": pd.NaT}, cls)


# --- Regular values ---

@pytest.mark.parametrize("name,cls", ENCODERS)
def test_regular_float_passes_through(name, cls):
    _assert_serializes({"val": 3.14}, {"val": 3.14}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_date_serializes_to_isoformat(name, cls):
    _assert_serializes({"val": "2024-01-15"}, {"val": date(2024, 1, 15)}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_datetime_serializes_to_isoformat(name, cls):
    _assert_serializes(
        {"val": "2024-01-15T10:30:00"},
        {"val": datetime(2024, 1, 15, 10, 30, 0)},
        cls,
    )


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_pd_timestamp_serializes_to_isoformat(name, cls):
    ts = pd.Timestamp("2024-01-15T10:30:00")
    result = json.loads(json.dumps({"val": ts}, cls=cls))
    assert result == {"val": ts.isoformat()}


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_none_passes_through(name, cls):
    _assert_serializes({"val": None}, {"val": None}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_integer_passes_through(name, cls):
    _assert_serializes({"val": 42}, {"val": 42}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_string_passes_through(name, cls):
    _assert_serializes({"val": "hello"}, {"val": "hello"}, cls)


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_bool_passes_through(name, cls):
    _assert_serializes({"val": True}, {"val": True}, cls)


# --- Nested structures ---

@pytest.mark.parametrize("name,cls", ENCODERS)
def test_nested_dict_with_nan(name, cls):
    _assert_serializes(
        {"outer": {"inner": None}},
        {"outer": {"inner": float("nan")}},
        cls,
    )


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_list_with_nan(name, cls):
    _assert_serializes(
        {"vals": [1.0, None, 2.0]},
        {"vals": [1.0, float("nan"), 2.0]},
        cls,
    )


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_nested_dict_with_pd_na(name, cls):
    _assert_serializes(
        {"outer": {"inner": None}},
        {"outer": {"inner": pd.NA}},
        cls,
    )


@pytest.mark.parametrize("name,cls", ENCODERS)
def test_mixed_nested_structure(name, cls):
    _assert_serializes(
        {
            "a": 1,
            "b": None,
            "c": {"d": None, "e": "ok"},
            "f": [None, 2.5, None],
        },
        {
            "a": 1,
            "b": float("nan"),
            "c": {"d": pd.NA, "e": "ok"},
            "f": [float("inf"), 2.5, float("-inf")],
        },
        cls,
    )
