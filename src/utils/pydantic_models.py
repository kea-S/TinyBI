from typing import List, Literal
from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    # if the query should include valid/invalid rows
    validity_filter: Literal["Valid Only", "ANomalies Only", "All Data"] = Field(
        "Valid Only",
        description="""
        'Valid Only' filters for records where is_valid_pdt is True.
        'Anomalies Only' isolates rows where tracking failed (e.g., APT > BWT).
        'All Data' includes everything for a complete volume audit.
        """
    )

    subject: Literal["logistics_provider", "country", "route", "global", "time_series"] \
        = Field(
           ..., description="The primary dimension for grouping (e.g., 'route' for seller->buyer)."
        )

    metric: Literal["avg_bwt", "avg_apt", "total_parcel_qty", "avg_parcel_qty", "All"] \
        = Field(
       ..., description="""
       The KPI requested. 'All' will trigger avg_bwt (buyer waiting time),
       avg_apt (average preparation time), total parcel quantity and average parcel quantity.
       """
    )

    # filter logic (mapped to SQL 'IN' clauses), no intercountry routes,
    # but for extendability keep as business logic may call for it
    seller_countries: List[str] = Field(default_factory=list, description="Seller countries.")
    buyer_countries: List[str] = Field(default_factory=list, description="Buyer countries.")
    seller_regions: List[str] = Field(default_factory=list, description="Seller regions.")
    buyer_regions: List[str] = Field(default_factory=list, description="Buyer regions.")
    logistics_providers: List[str] = Field(default_factory=list, description="Specific logistic providers.")

    # temporal logic, inclusive
    start_date: str = Field("2025-01-01", description="ISO format start date.")
    end_date: str = Field("2025-06-30", description="ISO format end date.")
    time_granularity: Literal["day", "week", "month"] \
        = Field("month", description="How specific metrics should be grouped by")

    # final insights
    persona: Literal["Operational", "Management", "BI"] = Field(
       ..., description="The stakeholder audience for this query."
    )
    plot_type: Literal["bar", "line", "none"] = Field("none")
