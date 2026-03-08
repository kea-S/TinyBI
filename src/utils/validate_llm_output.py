from typing import Dict, List, Optional, Tuple
import re

# Canonical country map: canonical_key -> label
CANONICAL_COUNTRIES: Dict[str, str] = {
    "TH": "Thailand",
    "MY": "Malaysia",
    "SG": "Singapore",
    "ID": "Indonesia",
    "PH": "Philippines",
}

# Canonical regions: canonical_region_key -> (label, country_key or None)
# Keys are the canonical region keys we will accept from the LLM (or the human-friendly labels).
CANONICAL_REGIONS: Dict[str, Tuple[str, Optional[str]]] = {
    "West Java": ("West Java", "ID"),
    "Johor": ("Johor", "MY"),
    "Selangor": ("Selangor", "MY"),
    "Songkhla": ("Songkhla", "TH"),
    "Sarawak": ("Sarawak", "MY"),
    "Banten": ("Banten", "ID"),
    "Ilocos Region": ("Ilocos Region", "PH"),
    "Chiang Mai": ("Chiang Mai", "TH"),
    "Korat": ("Korat", "TH"),
    "Kedah": ("Kedah", "MY"),
    "East Java": ("East Java", "ID"),
    "Central Java": ("Central Java", "ID"),
    "Unknown": ("Unknown", None),
    "Nonthaburi": ("Nonthaburi", "TH"),
    "Nakhon Sawan": ("Nakhon Sawan", "TH"),
    "SOCCSKSARGEN": ("SOCCSKSARGEN", "PH"),
    "West Visayas": ("West Visayas", "PH"),
    "North Sumatra": ("North Sumatra", "ID"),
    "BKK": ("BKK", "TH"),
    "Jakarta": ("Jakarta", "ID"),
    "NCR": ("NCR", "PH"),  # National Capital Region (Philippines)
    "Surat Thani": ("Surat Thani", "TH"),
    "Bicol Region": ("Bicol Region", "PH"),
    "Kuala Lumpur": ("Kuala Lumpur", "MY"),
    "Sabah": ("Sabah", "MY"),
    "Central Visayas": ("Central Visayas", "PH"),
    "South Sulawesi": ("South Sulawesi", "ID"),
    "Khon Kaen": ("Khon Kaen", "TH"),
    "Negeri Sembilan": ("Negeri Sembilan", "MY"),
    "Pahang": ("Pahang", "MY"),
    "Penang": ("Penang", "MY"),
    "Bali": ("Bali", "ID"),
    "Calabarzon": ("Calabarzon", "PH"),
    "Phuket": ("Phuket", "TH"),
    "Central Luzon": ("Central Luzon", "PH"),
    "Northern Mindanao": ("Northern Mindanao", "PH"),
    "Chonburi": ("Chonburi", "TH"),
    "Riau": ("Riau", "ID"),
    "SG": ("SG", "SG"),  # Singapore shorthand included as a region token in the data
    "Perak": ("Perak", "MY"),
}


# Normalization helper used to build reverse lookup maps for label->key (exact label matches only)
def _normalize(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


# build reverse lookup: normalized label -> canonical key
_COUNTRY_LABEL_TO_KEY: Dict[str, str] = {}
for k, label in CANONICAL_COUNTRIES.items():
    _COUNTRY_LABEL_TO_KEY[_normalize(label)] = k
    _COUNTRY_LABEL_TO_KEY[_normalize(k)] = k  # allow code input normalized

_REGION_LABEL_TO_KEY: Dict[str, str] = {}
for rk, (label, _) in CANONICAL_REGIONS.items():
    _REGION_LABEL_TO_KEY[_normalize(label)] = rk
    _REGION_LABEL_TO_KEY[_normalize(rk)] = rk  # allow region-key input normalized


def resolve_locations_postvalidated(llm_output: Dict) -> Dict:
    """
    Map llm_output lists to canonical keys using only exact matches (keys or normalized labels).
    Assumes llm_output fields are already lists of strings (validated by pydantic).
    """
    out = {
        "buyer_countries": [],
        "seller_countries": [],
        "buyer_regions": [],
        "seller_regions": [],
        "candidates": {},
        "needs_review": False,
    }

    # simple type checks to avoid silent mistakes
    for field in ("buyer_countries", "seller_countries", "buyer_regions", "seller_regions"):
        val = llm_output.get(field, [])
        if not isinstance(val, (list, tuple)):
            raise TypeError(f"Expected {field} to be list[str] (validated by pydantic); got {type(val)}")

    # map countries (exact key or normalized label match only)
    for side in ("buyer", "seller"):
        src = llm_output.get(f"{side}_countries", [])
        mapped: List[str] = []
        candidates: List[Tuple[str, Optional[str], str, None]] = []
        for item in src:
            # direct canonical key match
            if item in CANONICAL_COUNTRIES:
                mapped.append(item)
                candidates.append((item, item, "key", None))
                continue

            # normalized label -> key lookup (no fuzzy)
            key = _COUNTRY_LABEL_TO_KEY.get(_normalize(item))
            if key:
                mapped.append(key)
                candidates.append((item, key, "label", None))
            else:
                candidates.append((item, None, "no_match", None))
                out["needs_review"] = True
        out[f"{side}_countries"] = mapped
        out["candidates"][f"{side}_countries"] = candidates

    # map regions (exact key or normalized label match only)
    for side in ("buyer", "seller"):
        src = llm_output.get(f"{side}_regions", [])
        mapped: List[str] = []
        candidates: List[Tuple[str, Optional[str], str, None]] = []
        for item in src:
            # direct canonical region key match
            if item in CANONICAL_REGIONS:
                mapped.append(item)
                candidates.append((item, item, "key", None))
                continue

            # normalized label -> region key lookup (no fuzzy)
            key = _REGION_LABEL_TO_KEY.get(_normalize(item))
            if key:
                mapped.append(key)
                candidates.append((item, key, "label", None))
            else:
                candidates.append((item, None, "no_match", None))
                out["needs_review"] = True
        out[f"{side}_regions"] = mapped
        out["candidates"][f"{side}_regions"] = candidates

    return out
