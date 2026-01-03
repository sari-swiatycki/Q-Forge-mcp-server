import re


def _sanitize_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", value or "")
    return cleaned or "unknown"


def build_erd_mermaid(schema: dict) -> str:
    tables = schema.get("tables", {})
    foreign_keys = schema.get("foreign_keys", [])

    lines = ["erDiagram"]
    for table_name, columns in tables.items():
        safe_table = _sanitize_identifier(str(table_name))
        lines.append(f"  {safe_table} {{")
        for column in columns:
            col_type = _sanitize_identifier(str(column.get("type", "")))
            col_name = _sanitize_identifier(str(column.get("name", "")))
            lines.append(f"    {col_type} {col_name}")
        lines.append("  }")

    for fk in foreign_keys:
        table = _sanitize_identifier(str(fk.get("table", "")))
        ref_table = _sanitize_identifier(str(fk.get("referred_table", "")))
        cols = ", ".join(_sanitize_identifier(c) for c in fk.get("columns", []))
        label = cols or "fk"
        if table and ref_table:
            lines.append(f"  {ref_table} ||--o{{ {table} : \"{label}\"")

    return "\n".join(lines)
