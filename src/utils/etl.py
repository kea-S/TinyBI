import csv
import json
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tinyfish import TinyFish

from src.utils.prompts import TINYFISH_PROMPT


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "data" / "raw" / "noodle_database.csv"
DEBUG_DIR = REPO_ROOT / "data" / "raw" / "tinyfish_debug"
CSV_FIELDS = [
    "name",
    "price",
    "original_price",
    "on_sale",
    "quantity_g",
    "supermarket",
]
SUPERMARKETS = [
    {
        "name": "FairPrice",
        "url": "https://www.fairprice.com.sg/",
        "goal": (
            "Navigate to the instant noodles listings on FairPrice Singapore. "
            "Do not stop at the homepage. "
            + TINYFISH_PROMPT
        ),
    },
    {
        "name": "Cold Storage",
        "url": "https://coldstorage.com.sg/d/B1iThLsltXy.html",
        "goal": (
            "Extract all visible instant noodle listings from this Cold Storage page. "
            "If this page is not already the product listing page, navigate to the instant noodles listings first. "
            + TINYFISH_PROMPT
        ),
    },
    {
        "name": "Sheng Siong",
        "url": "https://shengsiong.com.sg/",
        "goal": (
            "Navigate from the Sheng Siong homepage to the online grocery instant noodles listings before extracting products. "
            + TINYFISH_PROMPT
        ),
    },
]


def _extract_products(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, str):
        parsed = _parse_jsonish(result)
        if parsed is not None:
            return _extract_products(parsed)
        return []

    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]

    if not isinstance(result, dict):
        return []

    if "name" in result and any(key in result for key in ("price", "original_price", "on_sale", "quantity_g")):
        return [result]

    for key in ("products", "items", "results", "data", "noodles"):
        value = result.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for value in result.values():
        nested = _extract_products(value)
        if nested:
            return nested

    return []


def _parse_jsonish(value: str) -> Any | None:
    text = value.strip()
    if not text:
        return None

    fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _normalize_number(value: Any) -> float | int | None:
    if value in (None, ""):
        return None

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(",", "")
        if not cleaned:
            return None

        try:
            number = float(cleaned)
        except ValueError:
            return None

        return int(number) if number.is_integer() else number

    return None


def _normalize_bool(value: Any) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False

    return None


def _normalize_record(product: dict[str, Any], supermarket: str) -> dict[str, Any]:
    quantity = _normalize_number(product.get("quantity_g"))
    if isinstance(quantity, float):
        quantity = int(quantity) if quantity.is_integer() else quantity

    return {
        "name": product.get("name"),
        "price": _normalize_number(product.get("price")),
        "original_price": _normalize_number(product.get("original_price")),
        "on_sale": _normalize_bool(product.get("on_sale")),
        "quantity_g": quantity,
        "supermarket": supermarket,
    }


def _debug_filename(supermarket_name: str) -> Path:
    slug = supermarket_name.lower().replace(" ", "_")
    return DEBUG_DIR / f"{slug}.json"


def _write_debug_payload(
    supermarket_name: str,
    *,
    status: str,
    result: Any,
    error: Any,
) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _debug_filename(supermarket_name)
    payload = {
        "supermarket": supermarket_name,
        "status": status,
        "error": None if error is None else getattr(error, "model_dump", lambda: str(error))(),
        "result": result,
    }
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return output_path


def _run_supermarket_etl(client: TinyFish, supermarket: dict[str, str]) -> list[dict[str, Any]]:
    response = client.agent.run(
        url=supermarket["url"],
        goal=supermarket["goal"],
        browser_profile="stealth",
    )
    debug_path = _write_debug_payload(
        supermarket["name"],
        status=str(response.status),
        result=response.result,
        error=response.error,
    )

    if response.status != "COMPLETED":
        error_message = response.error.message if response.error else "Unknown TinyFish error"
        raise RuntimeError(
            f"{supermarket['name']} extraction failed: {error_message}. Debug payload: {debug_path}"
        )

    products = _extract_products(response.result)
    normalized_rows = [
        _normalize_record(product, supermarket["name"])
        for product in products
        if isinstance(product, dict)
    ]
    normalized_rows = [row for row in normalized_rows if row["name"] and row["price"] is not None]
    deduped_rows = list({(row["name"], row["supermarket"]): row for row in normalized_rows}.values())

    if not deduped_rows:
        raise RuntimeError(
            f"{supermarket['name']} completed but extracted 0 usable rows. Debug payload: {debug_path}"
        )

    return deduped_rows


def _write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    load_dotenv()
    client = TinyFish()

    all_rows: list[dict[str, Any]] = []
    failures: list[str] = []

    for supermarket in SUPERMARKETS:
        print(f"Running TinyFish for {supermarket['name']}...")

        try:
            rows = _run_supermarket_etl(client, supermarket)
        except Exception as exc:
            failures.append(f"{supermarket['name']}: {exc}")
            print(f"Failed: {exc}")
            continue

        all_rows.extend(rows)
        print(f"Collected {len(rows)} rows from {supermarket['name']}.")

    _write_csv(all_rows, OUTPUT_PATH)

    print(f"Wrote {len(all_rows)} rows to {OUTPUT_PATH}")

    if failures:
        print("Completed with failures:")
        for failure in failures:
            print(f"- {failure}")

    print(f"Debug payloads saved to {DEBUG_DIR}")

    preview = all_rows[:3]
    if preview:
        print("Preview:")
        print(json.dumps(preview, indent=2))


if __name__ == "__main__":
    main()

