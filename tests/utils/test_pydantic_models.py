from datetime import date
from pydantic import ValidationError
import pytest

from src.utils.pydantic_models import QuerySchema, DEFAULT_START, DEFAULT_END


def _base_kwargs():
    # required fields for QuerySchema
    return {"subject": "route", "metric": "avg_bwt", "persona": "Operational"}


def test_region_only_no_country_allowed():
    """Providing a region (granular) without a country should be valid."""
    q = QuerySchema(**_base_kwargs(), buyer_regions=["Kuala Lumpur"])
    assert q.buyer_regions == ["Kuala Lumpur"]
    assert q.buyer_countries == []


def test_unknown_region_requires_country():
    """'Unknown' region must be accompanied by an explicit country for that side."""
    with pytest.raises(ValueError) as exc:
        QuerySchema(**_base_kwargs(), buyer_regions=["Unknown"])
    msg = str(exc.value)
    assert "Unknown" in msg
    assert "buyer_countries" in msg


def test_copy_countries_when_not_differentiated():
    """If buyer_countries is empty and seller_countries provided, copy seller -> buyer."""
    q = QuerySchema(**_base_kwargs(), seller_countries=["Malaysia"])
    assert q.seller_countries == ["Malaysia"]
    assert q.buyer_countries == ["Malaysia"]


def test_copy_regions_when_not_differentiated_single_string():
    """Accept single-string region and copy seller_regions -> buyer_regions when appropriate."""
    q = QuerySchema(**_base_kwargs(), seller_regions="Kuala Lumpur")
    assert q.seller_regions == ["Kuala Lumpur"]
    assert q.buyer_regions == ["Kuala Lumpur"]


# hm business logic problem: if no intersect should I throw a tantrum or leave
# it to user?
def test_no_copy_if_both_sides_provided():
    """If both buyer and seller values are provided, nothing should be copied/overwritten."""
    q = QuerySchema(
        **_base_kwargs(),
        seller_countries=["A"],
        buyer_countries=["B"],
        seller_regions=["X"],
        buyer_regions=["Y"],
    )
    assert q.seller_countries == ["A"]
    assert q.buyer_countries == ["B"]
    assert q.seller_regions == ["X"]
    assert q.buyer_regions == ["Y"]


def test_non_string_in_list_raises():
    """Non-string entries in country/region lists should be rejected."""
    with pytest.raises(ValueError):
        QuerySchema(**_base_kwargs(), seller_countries=[123])


def test_default_dates_when_empty_strings():
    """Empty-string dates from the LLM should revert to configured defaults."""
    q = QuerySchema(**_base_kwargs(), start_date="", end_date="")
    assert q.start_date == DEFAULT_START
    assert q.end_date == DEFAULT_END


def test_today_string_uses_defaults():
    """The string 'today' should be treated as sentinel and use defaults."""
    q = QuerySchema(**_base_kwargs(), start_date="today", end_date="today")
    assert q.start_date == DEFAULT_START
    assert q.end_date == DEFAULT_END


def test_today_date_obj_uses_defaults():
    """A date object equal to today's date should be treated as sentinel and use defaults."""
    today = date.today()
    q = QuerySchema(**_base_kwargs(), start_date=today, end_date=today)
    assert q.start_date == DEFAULT_START
    assert q.end_date == DEFAULT_END


def test_valid_iso_dates_parsed():
    """ISO date strings should be parsed into date objects and preserved."""
    q = QuerySchema(**_base_kwargs(), start_date="2024-01-01", end_date="2024-12-31")
    assert q.start_date == date(2024, 1, 1)
    assert q.end_date == date(2024, 12, 31)


def test_invalid_date_raises_validation_error():
    """Non-parseable date strings should raise a pydantic ValidationError."""
    with pytest.raises(ValidationError):
        QuerySchema(**_base_kwargs(), start_date="not-a-date", end_date="2024-01-01")


def test_start_after_end_raises():
    """Start date after end date should raise a ValueError from model validation."""
    with pytest.raises(ValueError):
        QuerySchema(**_base_kwargs(), start_date="2025-07-01", end_date="2025-06-30")
