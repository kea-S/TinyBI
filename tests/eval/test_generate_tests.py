import json
import yaml
import subprocess
from pathlib import Path
import pytest

def test_generate_tests_cli(tmp_path):
    input_data = [
        {
            "question_id": 1,
            "question": "How many users?",
            "SQL": "SELECT count(*) FROM users",
            "difficulty": "simple"
        }
    ]
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(input_data))
    
    output_file = tmp_path / "tests.yaml"
    
    script_path = Path("src/eval/generate_tests.py")
    result = subprocess.run(
        ["python", str(script_path), "--input", str(input_file), "--output", str(output_file)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert output_file.exists()
    
    with open(output_file, "r") as f:
        generated_tests = yaml.safe_load(f)
        
    assert len(generated_tests) == 1
    assert generated_tests[0]["vars"]["query"] == "How many users?"
    assert generated_tests[0]["vars"]["expected_sql"] == "SELECT count(*) FROM users"
    assert generated_tests[0]["vars"]["id"] == "bird-1"


def test_generate_tests_cli_samples_flag(tmp_path):
    input_data = [
        {"question_id": i, "question": f"Q{i}", "SQL": f"SELECT {i}", "difficulty": "simple"}
        for i in range(1, 11)
    ]
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(input_data))

    output_file = tmp_path / "tests.yaml"

    script_path = Path("src/eval/generate_tests.py")
    result = subprocess.run(
        ["python", str(script_path), "--input", str(input_file), "--output", str(output_file), "--samples", "5"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    with open(output_file, "r") as f:
        generated_tests = yaml.safe_load(f)

    assert len(generated_tests) == 5
    assert generated_tests[0]["vars"]["id"] == "bird-1"
    assert generated_tests[4]["vars"]["id"] == "bird-5"
