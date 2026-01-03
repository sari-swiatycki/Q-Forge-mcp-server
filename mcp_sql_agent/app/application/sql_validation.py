def validate_sql_select(sql: str) -> tuple[bool, str]:
    text = sql.strip().lower()
    if not text:
        return False, "SQL is empty."

    if not (text.startswith("select") or text.startswith("with")):
        return False, "Only SELECT queries are allowed."

    # Disallow multiple statements (a trailing semicolon is OK).
    if ";" in text[:-1]:
        return False, "Multiple statements are not allowed."

    blocked = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
        "copy",
    ]
    for word in blocked:
        if f" {word} " in f" {text} ":
            return False, f"Blocked keyword: {word}."

    return True, ""


def validate_sql_write(sql: str) -> tuple[bool, str]:
    text = sql.strip().lower()
    if not text:
        return False, "SQL is empty."

    if not (
        text.startswith("insert")
        or text.startswith("update")
        or text.startswith("delete")
    ):
        return False, "Only INSERT/UPDATE/DELETE are allowed."

    # Disallow multiple statements (a trailing semicolon is OK).
    if ";" in text[:-1]:
        return False, "Multiple statements are not allowed."

    blocked = ["drop", "alter", "truncate", "create", "grant", "revoke", "copy"]
    for word in blocked:
        if f" {word} " in f" {text} ":
            return False, f"Blocked keyword: {word}."

    return True, ""


def strip_trailing_semicolon(sql: str) -> tuple[str, str]:
    text = sql.rstrip()
    if text.endswith(";"):
        return text[:-1], ";"
    return text, ""


def has_limit(sql: str) -> bool:
    return re.search(r"\blimit\b", sql, re.IGNORECASE) is not None


def apply_limit(sql: str, limit: int) -> tuple[str, bool]:
    if has_limit(sql):
        return sql, False
    base, semi = strip_trailing_semicolon(sql)
    return f"{base} LIMIT {limit}{semi}", True
import re
