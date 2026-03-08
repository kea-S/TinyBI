import pytest

from src.utils.validate_llm_output import resolve_locations_postvalidated


def test_country_mapping_and_needs_review():
    """
    Verify country mapping behavior and needs_review flag.

    - Provide buyer_countries containing:
      - a canonical key ("TH"),
      - a human-friendly label ("Thailand"),
      - an unknown label ("FooLand").
    - Provide seller_countries containing a canonical key and a label that should map.

    Assertions:
    - buyer_countries maps "TH" and "Thailand" both to "TH".
    - seller_countries maps the key and label to "MY".
    - needs_review is True because "FooLand" had no match.
    - candidates entries reflect whether each item was matched by key, by label, or not matched.
    """
    llm_output = {
        "buyer_countries": ["TH", "Thailand", "FooLand"],
        "seller_countries": ["MY", "Malaysia"],
        "buyer_regions": [],
        "seller_regions": [],
    }

    res = resolve_locations_postvalidated(llm_output)

    # mapped keys
    assert res["buyer_countries"] == ["TH", "TH"]
    assert res["seller_countries"] == ["MY", "MY"]

    # needs_review because FooLand didn't match
    assert res["needs_review"] is True

    # candidates include original, mapped key (or None), reason, None
    buyer_cands = res["candidates"]["buyer_countries"]
    assert buyer_cands[0] == ("TH", "TH", "key", None)
    assert buyer_cands[1] == ("Thailand", "TH", "label", None)
    assert buyer_cands[2][0] == "FooLand"
    assert buyer_cands[2][1] is None
    assert buyer_cands[2][2] == "no_match"


def test_region_mapping_and_normalization():
    """
    Verify region mapping, normalization, and handling of typos.

    - Provide buyer_regions with:
      - a label requiring normalization ("  central  java!!") that should map to "Central Java",
      - a direct canonical region key ("Banten"),
      - a common-typo "Unkown" that should NOT match.
    - Provide seller_regions with canonical tokens ("SG", "BKK").

    Assertions:
    - Normalized input maps to the canonical region key "Central Java".
    - Direct keys map through unchanged.
    - Unknown/typo entry does not match and sets needs_review True.
    - candidates reflect label/key/no_match reasons.
    """
    llm_output = {
        "buyer_countries": [],
        "seller_countries": [],
        "buyer_regions": ["  central  java!!", "Banten", "Unkown"],
        "seller_regions": ["SG", "BKK"],
    }

    res = resolve_locations_postvalidated(llm_output)

    # normalized label "  central  java!!" should map to canonical "Central Java"
    assert res["buyer_regions"] == ["Central Java", "Banten"]
    assert res["seller_regions"] == ["SG", "BKK"]

    # "Unkown" (typo) should not match and should trigger review
    buyer_region_cands = res["candidates"]["buyer_regions"]
    assert buyer_region_cands[0] == ("  central  java!!", "Central Java", "label", None)
    assert buyer_region_cands[1] == ("Banten", "Banten", "key", None)
    assert buyer_region_cands[2][0] == "Unkown"
    assert buyer_region_cands[2][1] is None
    assert buyer_region_cands[2][2] == "no_match"
    assert res["needs_review"] is True


def test_all_matched_no_review():
    """
    Ensure that when all inputs match canonical keys/labels, needs_review remains False.

    - buyer_countries uses a canonical code ("ID").
    - seller_countries uses a human-friendly label ("Philippines") which should map to "PH".
    - buyer_regions and seller_regions use canonical region tokens ("Bali", "NCR").

    Assertions:
    - All outputs are the expected canonical keys.
    - needs_review is False.
    """
    llm_output = {
        "buyer_countries": ["ID"],
        "seller_countries": ["Philippines"],
        "buyer_regions": ["Bali"],
        "seller_regions": ["NCR"],
    }

    res = resolve_locations_postvalidated(llm_output)

    assert res["buyer_countries"] == ["ID"]
    assert res["seller_countries"] == ["PH"]
    assert res["buyer_regions"] == ["Bali"]
    assert res["seller_regions"] == ["NCR"]
    assert res["needs_review"] is False


def test_invalid_type_raises_type_error():
    """
    Confirm that passing non-list types for list-expected fields raises TypeError.

    - Provide buyer_countries as a string (invalid type).
    - The function should raise TypeError because it asserts those fields are lists/tuples.
    """
    llm_output = {
        "buyer_countries": "TH",  # wrong type
        "seller_countries": [],
        "buyer_regions": [],
        "seller_regions": [],
    }

    with pytest.raises(TypeError):
        resolve_locations_postvalidated(llm_output)
