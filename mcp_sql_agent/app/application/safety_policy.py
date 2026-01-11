import re

from mcp_sql_agent.app.application.sql_validation import has_limit


def evaluate_policy(sql: str, plan: dict, read_only: bool = True) -> dict:
    """Evaluate a safety policy and return an allow/deny decision.

    Args:
        sql: SQL statement to evaluate.
        plan: Planning metadata (risk score, safe_sql, etc).
        read_only: When True, reject write operations.
    Returns:
        Dict with policy decision and suggested remediation.
    """
    text = sql.strip().lower()
    if read_only and not (text.startswith("select") or text.startswith("with")):
        return {
            "allowed": False,
            "policy": "READ_ONLY",
            "reason": "WRITE_OPERATION_DETECTED",
            "suggested_fix": "Use SELECT or switch to a write tool with explicit approval.",
        }

    if ";" in text[:-1]:
        return {
            "allowed": False,
            "policy": "SINGLE_STATEMENT",
            "reason": "MULTIPLE_STATEMENTS_DETECTED",
            "suggested_fix": "Send a single statement per request.",
        }

    join_count = len(re.findall(r"\bjoin\b", text))
    if join_count >= 3:
        return {
            "allowed": False,
            "policy": "JOIN_COMPLEXITY",
            "reason": "TOO_MANY_JOINS",
            "suggested_fix": "Reduce joins or add filters and indexes.",
        }

    if " where " not in f" {text} " and not has_limit(text):
        safe_sql = plan.get("safe_sql", "")
        if safe_sql and safe_sql.strip().lower() != text:
            return {
                "allowed": True,
                "policy": "SAFE_LIMIT_APPLIED",
                "reason": "NO_WHERE_OR_LIMIT",
                "suggested_fix": "Add WHERE filters or a LIMIT clause.",
            }
        return {
            "allowed": False,
            "policy": "UNBOUNDED_READ",
            "reason": "NO_WHERE_OR_LIMIT",
            "suggested_fix": "Add WHERE filters or a LIMIT clause.",
        }

    if plan.get("risk_score", 0) >= 0.7:
        return {
            "allowed": False,
            "policy": "RISK_THRESHOLD",
            "reason": "HIGH_RISK_SCORE",
            "suggested_fix": "Apply filters, add LIMIT, or optimize indexes.",
        }

    return {"allowed": True, "policy": "ALLOW", "reason": "", "suggested_fix": ""}
