from typing import Any, List, Literal, Optional
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FilterIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute_hint: str = Field(
        ...,
        description="Coarse semantic hint for the filter target, such as country, provider, date, or route.",
        min_length=1,
    )
    operator: Optional[Literal["=", "IN", "<", "<=", ">", ">=", "BETWEEN", "CONTAINS"]] = Field(
        default=None,
        description="Coarse filter operator classification. Leave null when the user intent is unclear.",
    )
    raw_value_text: str | List[str] = Field(
        ...,
        description="Literal value span copied from the user request before canonicalization or database grounding.",
    )
    negated: bool = Field(
        default=False,
        description="Whether the user intended this filter as an exclusion, such as 'except gold'.",
    )

    @field_validator("attribute_hint", mode="before")
    @classmethod
    def _normalise_attribute_hint(cls, v):
        if not isinstance(v, str):
            raise ValueError("attribute_hint must be a string")

        cleaned = v.strip()
        if not cleaned:
            raise ValueError("attribute_hint must not be empty")
        return cleaned

    @field_validator("operator", mode="before")
    @classmethod
    def _normalise_operator(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("operator must be a string")

        cleaned = v.strip().upper()
        if cleaned == "==":
            return "="
        return cleaned

    @field_validator("raw_value_text", mode="before")
    @classmethod
    def _normalise_raw_value_text(cls, v):
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("raw_value_text must not be empty")
            return cleaned

        if isinstance(v, (list, tuple)):
            cleaned_items: List[str] = []
            for item in v:
                if not isinstance(item, str):
                    raise ValueError("raw_value_text list entries must be strings")
                cleaned = item.strip()
                if cleaned:
                    cleaned_items.append(cleaned)

            if not cleaned_items:
                raise ValueError("raw_value_text list must contain at least one non-empty string")
            return cleaned_items

        raise ValueError("raw_value_text must be a string or a list of strings")


class QuerySchema(BaseModel):
    subject: str = Field(
        ..., description="""
        The primary dimension the user asks for
        (e.g., 'account_id' for user accounts).
        """
    )

    metric_hint: str = Field(
        ...,
        min_length=1,
        description="""
            Measure the user wants to analyse e.g. number of accounts.
        """
    )

    aggregation: Optional[Literal["avg", "sum", "count", "min", "max"]] = \
        Field(
            default=None,
            description="""
                The analytic transformation requested for the metric.
                Use null when the user does not clearly specify an aggregation.
            """
    )

    filters: List[FilterIntent] = Field(
        default_factory=list,
        description=(
            """
            Coarse unresolved filter intents extracted from the user request.
            These are later grounded to concrete columns, tables, and canonical
            values.
            """
        ),
    )

    sort_on: Literal["subject", "metric"] = \
        Field("subject", description="""
        The column to rank results by.
        Use 'subject' to sort by the grouping (e.g., region, dates).
        Use 'metric' to sort by the calculated result (count, sum, max).
        """
              )

    ordering: Literal["asc", "desc"] = \
        Field(
        "desc",
        description="'desc' for 'slowest/highest', 'asc' for 'fastest/lowest'."
             )

    limit: Optional[int] = Field(
        None,
        description="The number of rows to return (e.g., 'top 5' -> 5).",
        ge=1, le=100
    )


class ColumnVectorIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: int = Field(..., ge=0, description="Stable FAISS id used to hydrate search results.")
    table_name: str
    column_name: str
    source_key: str = Field(..., description="Stable unique identifier, typically table.column.")
    description: Optional[str] = None
    data_format: Optional[str] = Field(
        default=None,
        description="Semantic format descriptor such as date, currency, percentage, or iso_country_code.",
    )
    aliases: List[str] = Field(default_factory=list)
    sample_values: List[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalise_legacy_data_type(self) -> Self:
        legacy_data_type = self.payload.pop("data_type", None)
        if self.data_format is None and isinstance(legacy_data_type, str):
            trimmed_legacy_data_type = legacy_data_type.strip()
            if trimmed_legacy_data_type:
                self.data_format = trimmed_legacy_data_type
        return self

    def to_embedding_text(self) -> str:
        lines = [
            f"Table: {self.table_name}",
            f"Column: {self.column_name}",
        ]

        if self.description:
            lines.append(f"Description: {self.description}")
        if self.data_format:
            lines.append(f"Data format: {self.data_format}")
        if self.aliases:
            lines.append(f"Aliases: {', '.join(self.aliases)}")
        if self.sample_values:
            lines.append(f"Sample values: {', '.join(self.sample_values)}")

        for key, value in self.payload.items():
            if value is None:
                continue

            if isinstance(value, list):
                rendered_value = ", ".join(str(item) for item in value)
            else:
                rendered_value = str(value)

            lines.append(f"{key.replace('_', ' ').title()}: {rendered_value}")

        return "\n".join(lines)


class VectorSearchResult(BaseModel):
    entry: ColumnVectorIndexEntry
    score: float


class BatchColumnVectorIndexEntriesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: List[ColumnVectorIndexEntry] = Field(
        ...,
        min_length=1,
        description="Complete batch of column metadata entries to embed and persist as the active index.",
    )


class BatchColumnVectorIndexResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_model: str
    entry_count: int = Field(..., ge=1)
    table_names: List[str] = Field(default_factory=list)
    vector_index_path: str
    metadata_path: str
