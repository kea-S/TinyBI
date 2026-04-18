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


def _as_list(value: str | list[str] | tuple[str, ...]) -> list[str]:
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


def _get_resolution_context(index_entry: ColumnVectorIndexEntry):
    payload = index_entry.payload or {}
    is_categorical = bool(payload.get("is_categorical"))
    canonical_values = payload.get("canonical_values") or []
    value_labels = payload.get("value_labels") or {}

    normalized_canonical_map: dict[str, str] = {}
    normalized_label_map: dict[str, str] = {}

    for canonical_value in canonical_values:
        normalized_canonical_map[_normalize_literal(canonical_value)] = canonical_value
        label = value_labels.get(canonical_value)
        if isinstance(label, str) and label.strip():
            normalized_label_map[_normalize_literal(label)] = canonical_value

    fuzzy_candidates = {**normalized_canonical_map, **normalized_label_map}

    return is_categorical, canonical_values, normalized_canonical_map, normalized_label_map, fuzzy_candidates


def can_resolve_value(
    filter_intent: FilterIntent,
    index_entry: ColumnVectorIndexEntry,
) -> bool:
    is_categorical, canonical_values, norm_map, label_map, fuzzy_candidates = _get_resolution_context(index_entry)

    if not is_categorical:
        return True

    if not canonical_values:
        return False

    raw_values = _as_list(filter_intent.raw_value_text)

    for raw_value in raw_values:
        normalized_value = _normalize_literal(raw_value)
        if (
            raw_value in canonical_values
            or normalized_value in norm_map
            or normalized_value in label_map
            or _choose_fuzzy_match(normalized_value, fuzzy_candidates)[0] is not None
        ):
            return True

    return False


def resolve_filter_literals(
    filter_intent: FilterIntent,
    index_entry: ColumnVectorIndexEntry,
) -> FilterIntent:
    is_categorical, canonical_values, norm_map, label_map, fuzzy_candidates = _get_resolution_context(index_entry)
    raw_values = _as_list(filter_intent.raw_value_text)

    if not is_categorical:
        return filter_intent

    resolved_values: list[str] = []
    unresolved_values: list[str] = []

    for raw_value in raw_values:
        normalized_value = _normalize_literal(raw_value)
        resolved_value: str | None = None

        if raw_value in canonical_values:
            resolved_value = raw_value
        elif normalized_value in norm_map:
            resolved_value = norm_map[normalized_value]
        elif normalized_value in label_map:
            resolved_value = label_map[normalized_value]
        else:
            resolved_value, _ = _choose_fuzzy_match(normalized_value, fuzzy_candidates)

        if resolved_value is None:
            unresolved_values.append(raw_value)
        else:
            resolved_values.append(resolved_value)

    if unresolved_values:
        logger.info(
            "Filter literal resolution dropped unresolved values for %s: %s",
            index_entry.source_key,
            {
                "attribute_hint": filter_intent.attribute_hint,
                "raw_values": raw_values,
                "resolved_values": resolved_values,
                "unresolved_values": unresolved_values,
            },
        )

    if not resolved_values:
        return None

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
