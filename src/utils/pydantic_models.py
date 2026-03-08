from typing import List, Literal, Optional
from typing_extensions import Self
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_START = date(2025, 1, 1)
DEFAULT_END = date(2025, 6, 30)


class QuerySchema(BaseModel):
    # if the query should include valid/invalid rows
    validity_filter: Literal["Valid Only", "Anomalies Only", "All Data"] = Field(
        "Valid Only",
        description="""
        'Valid Only' filters for records where is_valid_pdt is True.
        'Anomalies Only' isolates rows where tracking failed (e.g., APT > BWT).
        'All Data' includes everything for a complete volume audit.
        """
    )

    subject: Literal["logistics_provider", "country", "route", "global", "time_series"] = Field(
        ..., description="The primary dimension for grouping (e.g., 'route' for seller->buyer)."
    )

    metric: Literal["avg_bwt", "avg_apt", "total_parcel_qty", "avg_parcel_qty"] = Field(
        ..., description="""
       The KPI requested. avg_bwt (buyer waiting time),
       avg_apt (average preparation time), total parcel quantity and
       average parcel quantity.
       """
    )

    # filter logic (mapped to SQL 'IN' clauses)
    seller_countries: List[str] = Field(
        default_factory=list,
        description=(
            "Seller countries (list). Regions are more granular than countries: "
            "if a region is supplied, you do not need to supply the country for that region "
            "UNLESS the region is 'Unknown' (which requires an explicit country). "
            "If buyer/seller are not differentiated, the same countries will be applied to both sides."
        ),
    )
    buyer_countries: List[str] = Field(
        default_factory=list,
        description=(
            "Buyer countries (list). Regions are more granular than countries: "
            "if a region is supplied, you do not need to supply the country for that region "
            "UNLESS the region is 'Unknown' (which requires an explicit country). "
            "If buyer/seller are not differentiated, the same countries will be applied to both sides."
        ),
    )
    seller_regions: List[str] = Field(
        default_factory=list,
        description=(
            "Seller regions (list). Regions are more granular than countries — specifying a region "
            "is sufficient to target that area and you typically do not need to also list a country "
            "for that region, except when the region is 'Unknown'."
        ),
    )
    buyer_regions: List[str] = Field(
        default_factory=list,
        description=(
            "Buyer regions (list). Regions are more granular than countries — specifying a region "
            "is sufficient to target that area and you typically do not need to also list a country "
            "for that region, except when the region is 'Unknown'."
        ),
    )
    logistics_providers: List[str] = Field(default_factory=list, description="Specific logistic providers.")

    # temporal logic, inclusive - use date type for strict validation; allow Optional so validators can set sentinel None
    start_date: Optional[date] = Field(DEFAULT_START, description="ISO format start date.")
    end_date: Optional[date] = Field(DEFAULT_END, description="ISO format end date.")
    time_granularity: Literal["day", "week", "month"] = Field("month", description="How specific metrics should be grouped by")

    # order by logic
    sort_on: Literal["subject", "metric"] = \
        Field("subject", description="""
        The column to rank results by.
        Use 'subject' to sort by the grouping (e.g., provider names, dates).
        Use 'metric_value' to sort by the calculated performance score (e.g., speed, volume).
        """)
    ordering: Literal["asc", "desc"] = \
        Field("desc", description="'desc' for 'slowest/highest', 'asc' for 'fastest/lowest'.")

    # limit logic
    limit: Optional[int] = Field(
        None,
        description="The number of rows to return (e.g., 'top 5' -> 5).",
        ge=1, le=100  # Guardrail: prevent massive data dumps to the LLM
    )

    # final insights
    persona: Literal["Operational", "Management", "BI"] = Field(..., description="The stakeholder audience for this query.")
    plot_type: Literal["bar", "line", "none"] = Field("none")

    # --- Normalization validators for datetimes ---

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _parse_date_strings(cls, v):
        """
        Accept ISO date strings or date/datetime objects.
        Treat None / empty string / 'today' / a date equal to today as sentinel None
        so the model_validator can replace it with the Field default.
        """
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if s == "" or s.lower() == "today":
                return None
            try:
                return date.fromisoformat(s)
            except Exception:
                try:
                    return datetime.fromisoformat(s).date()
                except Exception:
                    raise ValueError(f"Invalid date format: {v!r}")
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            # treat today's date (LLM heuristics) as sentinel None
            if v == date.today():
                return None
            return v
        raise ValueError(f"Unsupported type for date field: {type(v)}")

    @model_validator(mode="after")
    def _fill_defaults_and_validate(self) -> Self:
        """
        Replace sentinel None with configured defaults and enforce start_date <= end_date.
        """
        sd = self.start_date
        ed = self.end_date

        if sd is None:
            object.__setattr__(self, "start_date", DEFAULT_START)
            sd = DEFAULT_START
        if ed is None:
            object.__setattr__(self, "end_date", DEFAULT_END)
            ed = DEFAULT_END

        if sd > ed:
            raise ValueError("start_date must be on or before end_date")

        return self

    # --- Normalization validators for country/region lists ---

    @field_validator("buyer_countries", "seller_countries", "buyer_regions", "seller_regions", mode="before")
    @classmethod
    def _normalize_str_or_list(cls, v):
        """
        Accepts: list[str], single str, empty str, or None.
        Normalizes:
          - None or empty -> []
          - single string -> [string]
          - strips whitespace from each entry
          - normalizes 'unknown' -> 'Unknown' (case-insensitive)
        """
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return []
            return [s]
        if isinstance(v, (list, tuple)):
            out: List[str] = []
            for item in v:
                if item is None:
                    continue
                if not isinstance(item, str):
                    raise ValueError("country/region list must contain strings")
                s = item.strip()
                if not s:
                    continue
                if s.lower() == "unknown":
                    s = "Unknown"
                out.append(s)
            return out
        raise ValueError("buyer_countries/seller_countries/buyer_regions/seller_regions must be list[str] or str")

    # --- Cross-field business logic ---

    @model_validator(mode="after")
    def _apply_region_country_logic(self) -> Self:
        """
        Business rules:
        1) Regions are more granular than countries. If regions are provided, country is not required
           for those regions unless a region value is 'Unknown' -> in that case the corresponding
           country must be provided (we raise a friendly validation error).
        2) If buyer_* and seller_* are not differentiated (i.e., one side is empty while the other side
           is provided), copy the provided side to the empty side so both sides are set the same.
        """
        # 1) Ensure 'Unknown' region requires explicit country
        for side in ("buyer", "seller"):
            regs = getattr(self, f"{side}_regions")
            ctys = getattr(self, f"{side}_countries")
            # if region list contains 'Unknown' but no country specified => instruct caller/LLM
            if any(r == "Unknown" for r in regs) and not ctys:
                raise ValueError(
                    f"{side}_regions contains 'Unknown' — please specify {side}_countries as well "
                    "because an 'Unknown' region requires country-level disambiguation."
                )

        # 2) If one side's countries/regions are empty and the other side has them, copy across.
        if not self.buyer_countries and self.seller_countries:
            object.__setattr__(self, "buyer_countries", list(self.seller_countries))
        elif not self.seller_countries and self.buyer_countries:
            object.__setattr__(self, "seller_countries", list(self.buyer_countries))

        if not self.buyer_regions and self.seller_regions:
            object.__setattr__(self, "buyer_regions", list(self.seller_regions))
        elif not self.seller_regions and self.buyer_regions:
            object.__setattr__(self, "seller_regions", list(self.buyer_regions))

        return self
