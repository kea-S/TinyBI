import json
import yaml
import argparse
from pathlib import Path

def generate_promptfoo_tests(input_path: str, output_path: str, samples: int | None = None):
    data_path = Path(input_path)
    output_path = Path(output_path)

    if not data_path.exists():
        raise FileNotFoundError(f"Input file not found: {data_path}")

    with open(data_path, "r") as f:
        data = json.load(f)

    if samples is not None:
        data = data[:samples]

    tests = []
    for item in data:
        tests.append({
            "vars": {
                "id": f"bird-{item['question_id']}",
                "description": f"Difficulty: {item['difficulty']}",
                "query": item["question"],
                "expected_sql": item["SQL"],
                "difficulty": item["difficulty"]
            }
        })

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(tests, f, sort_keys=False)

    print(f"Successfully generated {len(tests)} tests in {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Promptfoo tests from BIRD benchmark JSON.")
    parser.add_argument("--input", required=True, help="Path to input BIRD JSON file.")
    parser.add_argument("--output", required=True, help="Path to output YAML file.")
    parser.add_argument("--samples", type=int, default=None, help="Limit to first N samples.")
    
    args = parser.parse_args()
    generate_promptfoo_tests(args.input, args.output, args.samples)
