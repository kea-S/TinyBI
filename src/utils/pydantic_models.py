from typing import Any, List, Literal, Optional
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SINGLE_VALUE_OPERATORS = {"=", "<", "<=", ">", ">=", "CONTAINS"}
ORDERED_OPERATORS = {"<", "<=", ">", ">="}

# Statistical taxonomy constants
CATEGORICAL_TYPES = {"nominal", "ordinal", "categorical"}
QUANTITATIVE_TYPES = {"continuous", "discrete", "quantitative"}
TEMPORAL_TYPES = {"temporal"}


class FilterIntent(BaseModel):
    """
    Representations of the user's constraints in the natural language question.
    To be mapped into actual SQL WHERE clauses.

    IMPORTANT: constraints regarding the number of rows to return shouldn't be
    included as a filter intent. It should instead be included under the limit
    attribute
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

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

    raw_value_text: tuple[str, ...] = Field(
        ...,
        description="""
            Literal, concrete values copied from the user request. Do NOT
            include relative or comparative terms (e.g. "oldest",
            "latest", "cheapest", "fastest") — those are ordering or
            aggregation hints, not column values. Always a tuple.
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
            v = [v]

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
            return tuple(cleaned_items)

        raise ValueError("raw_value_text must be a list or tuple of strings")

    @model_validator(mode="before")
    @classmethod
    def _normalise_operator_value_consistency(cls, data):
        if not isinstance(data, dict):
            return data

        raw_value_text = data.get("raw_value_text")
        operator = data.get("operator")

        if raw_value_text is None:
            return data

        if isinstance(raw_value_text, str):
            raw_value_text = [raw_value_text]
            data = {**data, "raw_value_text": raw_value_text}

        if isinstance(raw_value_text, (list, tuple)):
            n = len(raw_value_text)
        else:
            return data

        if operator == "BETWEEN":
            if n != 2:
                raise ValueError(
                    f"operator 'BETWEEN' requires exactly 2 values, got {n}"
                )
            return data

        if operator == "=" and n > 1:
            data = {**data, "operator": "IN"}
            return data

        if operator is None:
            if n == 1:
                data = {**data, "operator": "="}
            else:
                data = {**data, "operator": "IN"}
            return data

        if operator in SINGLE_VALUE_OPERATORS and n > 1:
            if operator in ORDERED_OPERATORS:
                values = sorted(raw_value_text, reverse=(operator in (">", ">=")))
                data = {**data, "raw_value_text": (values[0],)}
            else:
                data = {**data, "raw_value_text": (raw_value_text[0],)}
            return data

        return data


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

    aggregation: Optional[Literal["avg", "sum", "count", "count_distinct", "min", "max"]] = \
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
        IMPORTANT: You MUST ONLY use 'subject' or 'metric_hint'. 
        Use 'subject' to sort the main subject of analysis (e.g. region, dates).
        Use 'metric_hint' to sort the analysed measure (e.g. count, sum).

        To be mapped to the SQL SORT BY clause
        """
              )

    ordering: Literal["asc", "desc"] = \
        Field(
        "asc",
        description="""
        Which direction to sort_on. 
        IMPORTANT: You MUST ONLY use 'asc' or 'desc'.
        Default to ascending, but questions with 'top' generally would fall under desc.
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
    statistical_type: Literal[
        "nominal", "ordinal", "categorical", 
        "continuous", "discrete", "quantitative", 
        "temporal", "identifier"
    ] = Field(
        ...,
        description="The statistical nature of the data, used to determine resolution strategies."
    )
    categorical_values: dict[str, List[str]] = Field(
        default_factory=dict,
        description="Maps raw database values to lists of human-friendly synonyms. Only for categorical data."
    )
    aliases: List[str] = Field(default_factory=list)
    sample_values: List[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    references: Optional[str] = Field(default=None, description="FK reference to another column's source_key.")

    @model_validator(mode="before")
    @classmethod
    def _migrate_metadata_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Ensure payload is a dict we can modify
        payload = data.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        else:
            # Create a copy to avoid side effects if necessary, 
            # but usually modifying in-place is expected in 'before' validators for dicts
            payload = dict(payload)

        # 1. Migrate data_type to data_format
        if data.get("data_format") is None:
            legacy_data_type = payload.pop("data_type", None)
            if isinstance(legacy_data_type, str) and legacy_data_type.strip():
                data["data_format"] = legacy_data_type.strip()
        else:
            payload.pop("data_type", None)

        # 2. Migrate is_categorical / statistical_type
        if data.get("statistical_type") is None:
            # Check payload
            st = payload.pop("statistical_type", None)
            if st:
                data["statistical_type"] = st
            else:
                is_cat = payload.pop("is_categorical", None)
                if is_cat is True:
                    data["statistical_type"] = "categorical"
                elif is_cat is False:
                    # Smart default for non-categorical data
                    fmt = (data.get("data_format") or "").lower()
                    col_name = (data.get("column_name") or "").lower()
                    
                    if "date" in fmt or "time" in fmt:
                        data["statistical_type"] = "temporal"
                    elif col_name.endswith("_id") or col_name == "id" or "_id_" in col_name:
                        data["statistical_type"] = "identifier"
                    else:
                        data["statistical_type"] = "quantitative"
                else:
                    # Unclear legacy data, default to nominal
                    data["statistical_type"] = "nominal"
        else:
            payload.pop("statistical_type", None)
            payload.pop("is_categorical", None)

        # 3. Legacy migration into unified categorical_values
        if data.get("categorical_values") is None:
            categorical_values = {}
            
            # Start with categories / canonical_values
            categories = payload.pop("categories", None) or payload.pop("canonical_values", None)
            if isinstance(categories, list):
                for cat in categories:
                    cat_str = str(cat)
                    categorical_values[cat_str] = []

            # Add value_mappings / value_labels
            value_mappings = payload.pop("value_mappings", None) or payload.pop("value_labels", None)
            if isinstance(value_mappings, dict):
                for k, v in value_mappings.items():
                    k_str = str(k)
                    if isinstance(v, str):
                        categorical_values[k_str] = [v]
                    elif isinstance(v, list):
                        categorical_values[k_str] = [str(i) for i in v]
            
            if categorical_values:
                data["categorical_values"] = categorical_values
        else:
            # Clean up payload even if categorical_values is present
            payload.pop("categories", None)
            payload.pop("canonical_values", None)
            payload.pop("value_mappings", None)
            payload.pop("value_labels", None)

        data["payload"] = payload
        return data

    @model_validator(mode="after")
    def _validate_categorical_values(self) -> Self:
        categorical_types = {"nominal", "ordinal", "categorical"}
        is_categorical = self.statistical_type in categorical_types
        
        if not is_categorical and self.categorical_values:
            raise ValueError(
                f"Categorical values can only be provided for nominal, ordinal, or categorical types. "
                f"Current type: {self.statistical_type}"
            )
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
        if self.statistical_type:
            lines.append(f"Statistical type: {self.statistical_type}")
        if self.categorical_values:
            for db_value, synonyms in self.categorical_values.items():
                parts = [db_value] + (synonyms or [])
                lines.append(f"Category: {', '.join(parts)}")

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


class CandidateEntries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_entries: List[VectorSearchResult]
    metric_entries: List[VectorSearchResult]
    filter_entries: dict[FilterIntent, List[VectorSearchResult]]

    def to_log_dict(self) -> dict:
        return {
            "subject_entries": [r.model_dump(mode="json") for r in self.subject_entries],
            "metric_entries": [r.model_dump(mode="json") for r in self.metric_entries],
            "filter_entries": [
                {
                    "intent": fi.model_dump(mode="json"),
                    "results": [r.model_dump(mode="json") for r in group],
                }
                for fi, group in self.filter_entries.items()
            ],
        }


class FinalEntries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_entries: List[ColumnVectorIndexEntry]
    metric_entry: Optional[ColumnVectorIndexEntry]
    filter_entries: dict[FilterIntent, ColumnVectorIndexEntry]

    def to_log_dict(self) -> dict:
        return {
            "subject_entries": [e.model_dump(mode="json") for e in self.subject_entries],
            "metric_entry": self.metric_entry.model_dump(mode="json") if self.metric_entry else None,
            "filter_entries": [
                {
                    "intent": fi.model_dump(mode="json"),
                    "column": entry.model_dump(mode="json"),
                }
                for fi, entry in self.filter_entries.items()
            ],
        }


# join tree data structure
class JoinStep(BaseModel):
    """
    Represents tables
    """
    table: str
    parent: str
    on_clause: str


class FinalJoins(BaseModel):
    """
    Represents final joins needed for sql
    """
    from_table: str
    joins: list[JoinStep]
