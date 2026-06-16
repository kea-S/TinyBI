import json
from collections import defaultdict

TYPE_MAP = {
    "int64": "BIGINT",
    "float64": "DOUBLE",
    "str": "VARCHAR",
    "str64": "VARCHAR",
}


def _build_comment(col: dict) -> str:
    parts = [col["description"]]

    st = col.get("statistical_type")
    if st:
        parts.append(f"type: {st}")

    aliases = col.get("aliases", [])
    if aliases:
        parts.append(f"aliases: {', '.join(aliases)}")

    cat_values = col.get("categorical_values", {})
    if cat_values:
        mapping = ", ".join(
            f"{k}={v[0]}" if v else k
            for k, v in sorted(cat_values.items())
        )
        parts.append(f"values: {mapping}")

    samples = col.get("sample_values", [])
    if samples:
        parts.append(f"sample: {', '.join(samples[:5])}")

    return " | ".join(parts)


def generate_ddl(columns_path: str) -> str:
    with open(columns_path) as f:
        columns = json.load(f)

    if not columns:
        return ""

    tables = defaultdict(list)
    for col in columns:
        tables[col["table_name"]].append(col)

    lines = []
    for table_name, cols in tables.items():
        lines.append(f"CREATE TABLE {table_name} (")
        for col in cols:
            dtype = TYPE_MAP.get(col["data_format"], col["data_format"])
            col_def = f"    {col['column_name']} {dtype}"
            ref = col.get("references")
            if ref:
                table, column = ref.split(".")
                col_def += f" REFERENCES {table}({column})"
            col_def += f"  -- {_build_comment(col)}"
            lines.append(col_def)
        lines.append(");")
        lines.append("")

    return "\n".join(lines).rstrip("\n")
