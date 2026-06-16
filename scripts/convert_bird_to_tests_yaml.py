"""
Convert a BIRD benchmark JSON file to promptfoo tests.yaml format.

Usage:
    uv run python scripts/convert_bird_to_tests_yaml.py <bird_json_path> [--output OUTPUT_YAML]
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def convert(bird_json: Path, existing_yaml: Path | None) -> list[dict]:
    with open(bird_json) as f:
        bird_cases = json.load(f)

    existing_ids: set[str] = set()
    if existing_yaml and existing_yaml.exists():
        existing = yaml.safe_load(existing_yaml.read_text()) or []
        for tc in existing:
            vid = tc.get("vars", {}).get("id", "")
            if vid:
                existing_ids.add(vid)

    cases = []
    for item in bird_cases:
        qid = item["question_id"]
        vid = f"bird-{qid}"
        if vid in existing_ids:
            continue
        cases.append({
            "vars": {
                "id": vid,
                "query": item["question"].strip(),
                "expected_sql": item["SQL"].strip(),
                "reference_answer": None,
                "difficulty": item.get("difficulty", ""),
            }
        })

    return cases


def main():
    parser = argparse.ArgumentParser(description="Convert BIRD JSON to tests.yaml format")
    parser.add_argument("bird_json", type=Path, help="Path to BIRD benchmark JSON file")
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Append to existing tests.yaml (skips duplicates by id)",
    )
    args = parser.parse_args()

    existing_path = args.output if args.output else None
    cases = convert(args.bird_json, existing_path)

    if not cases:
        print("No new test cases to add (all already present).", file=sys.stderr)
        return

    yaml_output = yaml.dump(cases, default_flow_style=False, allow_unicode=True, sort_keys=False)

    if args.output:
        with open(args.output, "a") as f:
            f.write(yaml_output)
        print(f"Appended {len(cases)} test cases to {args.output}")
    else:
        print(yaml_output)


if __name__ == "__main__":
    main()
