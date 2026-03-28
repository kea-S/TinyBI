from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SUPERMARKET_ALIASES = {
    "fairprice": "FairPrice",
    "ntuc": "FairPrice",
    "ntuc fairprice": "FairPrice",
    "cold storage": "Cold Storage",
    "coldstorage": "Cold Storage",
    "sheng siong": "Sheng Siong",
    "shengsiong": "Sheng Siong",
}


class QuerySchema(BaseModel):
    supermarkets: list[str] = Field(
        default_factory=list,
        description=(
            "Canonical supermarket filters. Allowed values are FairPrice, Cold Storage, and Sheng Siong. "
            "Leave empty for all supermarkets."
        ),
    )
    on_sale_filter: Literal["any", "on_sale_only", "not_on_sale_only"] = Field(
        "any",
        description="Sale-state filter for products.",
    )
    quantity_g_op: Literal["none", "gt", "gte", "lt", "lte", "eq"] = Field(
        "none",
        description="Comparison operator for quantity_g.",
    )
    quantity_g_value: int | None = Field(
        None,
        description="Quantity threshold in grams. Required when quantity_g_op is not 'none'.",
        ge=0,
    )
    sort_by: Literal["price", "original_price", "quantity_g", "name", "supermarket"] = Field(
        "price",
        description="Column used to rank or order products.",
    )
    ordering: Literal["asc", "desc"] = Field(
        "asc",
        description="Sort direction. Cheapest means price ascending.",
    )
    limit: int = Field(
        1,
        description="Maximum number of rows to return. Use 1 for singular requests like 'the cheapest'.",
        ge=1,
        le=100,
    )
    persona: Literal["Shopper", "Operations", "BI"] = Field(
        "Shopper",
        description="Audience for downstream explanation.",
    )

    @field_validator("supermarkets", mode="before")
    @classmethod
    def _normalize_supermarkets(cls, value):
        if value is None:
            return []

        if isinstance(value, str):
            raw_values = [value]
        elif isinstance(value, (list, tuple)):
            raw_values = list(value)
        else:
            raise ValueError("supermarkets must be a string or list of strings")

        normalized: list[str] = []
        seen: set[str] = set()

        for item in raw_values:
            if item is None:
                continue
            if not isinstance(item, str):
                raise ValueError("supermarkets must contain only strings")

            cleaned = " ".join(item.strip().lower().split())
            if not cleaned:
                continue

            canonical = SUPERMARKET_ALIASES.get(cleaned)
            if canonical and canonical not in seen:
                normalized.append(canonical)
                seen.add(canonical)

        return normalized

    @model_validator(mode="after")
    def _validate_quantity_filter(self):
        if self.quantity_g_op == "none":
            object.__setattr__(self, "quantity_g_value", None)
            return self

        if self.quantity_g_value is None:
            raise ValueError("quantity_g_value is required when quantity_g_op is not 'none'")

        return self

