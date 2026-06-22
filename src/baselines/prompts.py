from pathlib import Path

def build_schema_dump_prompt(ddl_schema: str) -> str:
    path = Path(__file__).resolve().parents[1] / "utils" / "prompts" / "baseline_schema_dump_v3.txt"
    template = path.read_text(encoding="utf-8").strip()
    return template.format(ddl_schema=ddl_schema)
