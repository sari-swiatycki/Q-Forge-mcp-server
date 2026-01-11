def _format_table_grid(headers: list[str], rows: list[dict], col_widths: dict) -> str:
    """Render rows into an ASCII grid table."""
    def _border() -> str:
        parts = ["+" + "-" * (col_widths[h] + 2) for h in headers]
        return "".join(parts) + "+"

    def _row(values: list[str]) -> str:
        parts = [f"| {str(v).ljust(col_widths[h])} " for h, v in zip(headers, values)]
        return "".join(parts) + "|"

    lines = [_border(), _row(headers), _border()]
    for row in rows:
        lines.append(_row([row.get(h, "") for h in headers]))
    lines.append(_border())
    return "\n".join(lines)


def format_table(rows: list[dict], style: str = "simple") -> str:
    """Format rows as a simple or grid ASCII table."""
    if not rows:
        return ""

    headers = list(rows[0].keys())
    col_widths = {h: len(str(h)) for h in headers}
    for row in rows:
        for h in headers:
            col_widths[h] = max(col_widths[h], len(str(row.get(h, ""))))

    def _line(values: list[str]) -> str:
        parts = []
        for h, v in zip(headers, values):
            parts.append(str(v).ljust(col_widths[h]))
        return " | ".join(parts)

    if style == "grid":
        return _format_table_grid(headers, rows, col_widths)

    header_line = _line(headers)
    sep_line = "-+-".join("-" * col_widths[h] for h in headers)
    body_lines = [_line([row.get(h, "") for h in headers]) for row in rows]
    return "\n".join([header_line, sep_line, *body_lines])


def format_csv(rows: list[dict]) -> str:
    """Format rows as CSV with minimal quoting."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        values = []
        for h in headers:
            value = str(row.get(h, ""))
            if "," in value or "\"" in value:
                value = value.replace("\"", "\"\"")
                value = f"\"{value}\""
            values.append(value)
        lines.append(",".join(values))
    return "\n".join(lines)
