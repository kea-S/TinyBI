from typing import Any, List, Literal, Optional
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FilterIntent(BaseModel):
    """
    Representations of the user's constraints in the natural language question.
    To be mapped into actual SQL WHERE clauses.

    IMPORTANT: constraints regarding the number of rows to return shouldn't be
    included as a filter intent. It should instead be included under the limit
    attribute
    """
    model_config = ConfigDict(extra="forbid")

    attribute_hint: str = Field(
        ...,
        description="""
            Semantic hint for the kind of field the natural language query
            intends to filter on. Prefer a richer business-facing descriptor
            over a guessed schema column name.

            Good examples:
            - "buyer country"
            - "order status"
            - "shipment creation month"

            Avoid under-specified labels like "country" when the user wording
            supports a clearer role distinction such as buyer vs seller, order
            vs payment, creation date vs delivery date.
        """,
        min_length=1,
    )

    operator: Optional[Literal["=", "IN", "<", "<=", ">", ">=", "BETWEEN", "CONTAINS"]] = Field(
        default=None,
        description="""
            Coarse filter operator classification. Leave null when the user
            intent is unclear
        """,
    )

    raw_value_text: str | List[str] = Field(
        ...,
        description="""
            Literal values copied from the user request detailing what the user
            intends to filter for in the target field
        """,
    )

    negated: bool = Field(
        default=False,
        description="""
            Whether the user intended this filter as an exclusion, such as
            'except gold', 'other than january', 'without males'
        """,
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
        ...,
        min_length=1,
        description="""
        Semantic descriptor for what each result row is about, and usually the
        thing results are grouped by.

        Prefer a richer business-facing descriptor over a guessed schema
        column name. The goal is to preserve meaning for downstream schema
        linking, not to predict the exact database field name.

        To be mapped into actual sql SELECT clauses and potentially GROUP BY

        Good examples:
        - 'buyer country'
        - 'logistical provider'
        - 'shipment creation month'
        """
    )

    metric_hint: str = Field(
        ...,
        min_length=1,
        description="""
        Semantic descriptor for the measure or outcome the user wants to
        analyze for each subject.

        Prefer the business meaning of the requested measure over a guessed
        schema column name so downstream retrieval can resolve the best field.

        To be mapped into actual sql SELECT clauses and potentially aggregation
        functions

        Good examples:
        - 'order value'
        - 'buyer waiting time'
        - 'parcel volume'
        """
    )

    aggregation: Optional[Literal["avg", "sum", "count", "min", "max"]] = \
        Field(
            default=None,
            description="""
            The analytic transformation requested for the metric_hint.
            Use null when not confident on an existing aggregation.

            To be mapped into actual SQL aggregate functions
            """
    )

    filters: List[FilterIntent] = Field(
        default_factory=list,
        description=(
            """
            List of FilterIntents, representations of the user's constraints
            in the natural language question.

            To be mapped into actual SQL WHERE clauses.

            IMPORTANT: constraints regarding the number of rows to return
            shouldn't be included as a filter intent. It should instead be
            included under the limit attribute
            """
        ),
    )

    sort_on: Literal["subject", "metric_hint"] = \
        Field("subject", description="""
        The dimension to sort the final output table by.
        Use 'subject' to sort the main subject of analysis (e.g. region, dates).
        Use 'metric_hint' to sort the analysed measure (e.g. count, sum).

        To be mapped to the SQL SORT BY clause
        """
              )

    ordering: Literal["asc", "desc"] = \
        Field(
        "asc",
        description="""
        Which direction to sort_on. Default to ascending, but questions with
        'top' generally would fall under desc.
        """
            )

    limit: Optional[int] = Field(
        None,
        description="""
        The number of rows to return (e.g., 'top 5' -> 5).

        To be mapped to the SQL LIMIT clause
        """,
        ge=1, le=100
    )

    limit: Optional[int] = Field(
        None,
        description="""
        The number of rows to return (e.g., 'top 5' -> 5).

        To be mapped to the SQL LIMIT clause
        """,
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


class CandidateAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_entries: List[VectorSearchResult]
    metric_entries: List[VectorSearchResult]
    filter_entries: List[List[VectorSearchResult]]


class FinalAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_entries: List[ColumnVectorIndexEntry]
    metric_entries: ColumnVectorIndexEntry
    filter_entries: List[ColumnVectorIndexEntry]
