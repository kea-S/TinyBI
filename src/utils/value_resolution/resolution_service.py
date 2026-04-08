import logging
import re
from difflib import SequenceMatcher

from src.utils.pydantic_models import FilterIntent, ColumnVectorIndexEntry

logger = logging.getLogger(__name__)


def _normalize_literal(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _as_list(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def _choose_fuzzy_match(
    normalized_value: str,
    candidates: dict[str, str],
    *,
    min_score: float = 0.9,
    min_margin: float = 0.08,
) -> tuple[str | None, float]:
    if not normalized_value:
        return None, 0.0

    scored = sorted(
        (
            (SequenceMatcher(None, normalized_value, candidate_key).ratio(), canonical_value)
            for candidate_key, canonical_value in candidates.items()
        ),
        reverse=True,
    )
    if not scored:
        return None, 0.0

    top_score, top_value = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if top_score < min_score or (top_score - second_score) < min_margin:
        return None, top_score

    return top_value, top_score


def resolve_filter_literals(
    filter_intent: FilterIntent,
    index_entry: ColumnVectorIndexEntry,
) -> FilterIntent | None:
    payload = index_entry.payload or {}
    is_categorical = bool(payload.get("is_categorical"))
    raw_values = _as_list(filter_intent.raw_value_text)

    if not is_categorical:
        return filter_intent

    canonical_values = payload.get("canonical_values") or []
    if not isinstance(canonical_values, list):
        raise ValueError("payload.canonical_values must be a list[str] when is_categorical is true")

    value_labels = payload.get("value_labels") or {}
    if not isinstance(value_labels, dict):
        raise ValueError("payload.value_labels must be a dict[str, str] when provided")

    normalized_canonical_map: dict[str, str] = {}
    normalized_label_map: dict[str, str] = {}

    for canonical_value in canonical_values:
        if not isinstance(canonical_value, str):
            raise ValueError("payload.canonical_values entries must be strings")

        normalized_canonical_map[_normalize_literal(canonical_value)] = canonical_value

        label = value_labels.get(canonical_value)
        if isinstance(label, str) and label.strip():
            normalized_label_map[_normalize_literal(label)] = canonical_value

    fuzzy_candidates = {**normalized_canonical_map, **normalized_label_map}
    resolved_values: list[str] = []
    unresolved_values: list[str] = []
    matches: list[dict[str, str | float | None]] = []

    for raw_value in raw_values:
        normalized_value = _normalize_literal(raw_value)
        resolved_value: str | None = None
        match_type = "none"
        score = 0.0

        if raw_value in canonical_values:
            resolved_value = raw_value
            match_type = "exact"
            score = 1.0
        elif normalized_value in normalized_canonical_map:
            resolved_value = normalized_canonical_map[normalized_value]
            match_type = "normalized"
            score = 1.0
        elif normalized_value in normalized_label_map:
            resolved_value = normalized_label_map[normalized_value]
            match_type = "label"
            score = 1.0
        else:
            resolved_value, score = _choose_fuzzy_match(normalized_value, fuzzy_candidates)
            if resolved_value is not None:
                match_type = "fuzzy"

        if resolved_value is None:
            unresolved_values.append(raw_value)
        else:
            resolved_values.append(resolved_value)

        matches.append(
            {
                "raw_value": raw_value,
                "resolved_value": resolved_value,
                "match_type": match_type,
                "score": round(score, 4),
            }
        )

    if unresolved_values:
        logger.info(
            "Filter literal resolution dropped unresolved values for %s: %s",
            index_entry.source_key,
            {
                "attribute_hint": filter_intent.attribute_hint,
                "raw_values": raw_values,
                "resolved_values": resolved_values,
                "unresolved_values": unresolved_values,
                "matches": matches,
            },
        )

    if not resolved_values:
        return None

    cleaned_value: str | list[str]
    if len(resolved_values) == 1:
        cleaned_value = resolved_values[0]
    else:
        cleaned_value = resolved_values

    cleaned_operator = filter_intent.operator
    if len(resolved_values) > 1 and cleaned_operator in (None, "="):
        cleaned_operator = "IN"

    return FilterIntent(
        attribute_hint=filter_intent.attribute_hint,
        operator=cleaned_operator,
        raw_value_text=cleaned_value,
        negated=filter_intent.negated,
    )

