import json
import logging
import re

from mcp_sql_agent.app.domain.ports import SqlAdapter
from mcp_sql_agent.app.application.dto import QueryPlanDto
from mcp_sql_agent.app.application.sql_validation import (
    apply_limit,
    has_limit,
    strip_trailing_semicolon,
)


logger = logging.getLogger(__name__)


def _build_explain_sql(sql: str, dialect: str) -> str:
    # Normalize EXPLAIN shape per dialect so downstream parsing stays simple.
    base, _ = strip_trailing_semicolon(sql)
    if dialect == "sqlite":
        return f"EXPLAIN QUERY PLAN {base}"
    if dialect in {"postgresql", "postgres"}:
        return f"EXPLAIN (FORMAT JSON) {base}"
    return f"EXPLAIN {base}"


def _run_explain(sql: str, adapter: SqlAdapter) -> dict:
    dialect = adapter.get_dialect()
    explain_sql = _build_explain_sql(sql, dialect)
    try:
        rows = adapter.query(explain_sql)
        return {"dialect": dialect, "explain_sql": explain_sql, "rows": rows}
    except Exception as exc:
        logger.exception("explain failed")
        return {"dialect": dialect, "error": str(exc), "explain_sql": explain_sql}


def _extract_postgres_plan(rows: list[dict]) -> dict:
    if not rows:
        return {}
    first = rows[0]
    plan_value = None
    for key in first.keys():
        if key.lower().replace("_", " ") == "query plan":
            plan_value = first[key]
            break
    if isinstance(plan_value, str):
        try:
            plan_value = json.loads(plan_value)
        except json.JSONDecodeError:
            return {}
    if isinstance(plan_value, list) and plan_value:
        plan_value = plan_value[0]
    if isinstance(plan_value, dict) and "Plan" in plan_value:
        return plan_value.get("Plan", {})
    if isinstance(plan_value, dict):
        return plan_value
    return {}


def _extract_tables(sql: str) -> list[str]:
    text = sql.lower()
    tables = re.findall(r"from\\s+([a-z0-9_\\.]+)", text)
    tables += re.findall(r"join\\s+([a-z0-9_\\.]+)", text)
    cleaned = [t.split(".")[-1] for t in tables]
    return list(dict.fromkeys(cleaned))


def _extract_joins(sql: str) -> list[str]:
    text = sql.lower()
    return re.findall(r"join\\s+([a-z0-9_\\.]+)", text)


def _extract_filters(sql: str) -> list[str]:
    text = sql.lower()
    where_match = re.search(r"where\\s+(.*?)(group\\s+by|order\\s+by|limit|$)", text)
    if not where_match:
        return []
    clause = where_match.group(1).strip()
    return [clause] if clause else []


def _extract_group_by(sql: str) -> list[str]:
    text = sql.lower()
    match = re.search(r"group\\s+by\\s+(.*?)(order\\s+by|limit|$)", text)
    if not match:
        return []
    return [s.strip() for s in match.group(1).split(",") if s.strip()]


def _extract_order_by(sql: str) -> list[str]:
    text = sql.lower()
    match = re.search(r"order\\s+by\\s+(.*?)(limit|$)", text)
    if not match:
        return []
    return [s.strip() for s in match.group(1).split(",") if s.strip()]


def _extract_limit(sql: str) -> int | None:
    match = re.search(r"\\blimit\\s+(\\d+)", sql.lower())
    if not match:
        return None
    return int(match.group(1))


def _extract_aggregations(sql: str) -> list[str]:
    text = sql.lower()
    aggs = []
    for fn in ["count", "sum", "avg", "min", "max"]:
        if f"{fn}(" in text:
            aggs.append(fn)
    return aggs


def _build_schema_graph(schema: dict) -> dict:
    graph: dict[str, set[str]] = {}
    for fk in schema.get("foreign_keys", []):
        src = fk.get("table")
        dst = fk.get("referred_table")
        if not src or not dst:
            continue
        graph.setdefault(src, set()).add(dst)
        graph.setdefault(dst, set()).add(src)
    return {k: sorted(v) for k, v in graph.items()}


def _find_join_path(graph: dict, start: str, end: str) -> list[str]:
    if start == end:
        return [start]
    queue = [(start, [start])]
    visited = {start}
    while queue:
        node, path = queue.pop(0)
        for neighbor in graph.get(node, []):
            if neighbor in visited:
                continue
            if neighbor == end:
                return path + [neighbor]
            visited.add(neighbor)
            queue.append((neighbor, path + [neighbor]))
    return []


def _build_plan_json(sql: str, schema: dict | None = None) -> dict:
    tables = _extract_tables(sql)
    joins = _extract_joins(sql)
    filters = _extract_filters(sql)
    group_by = _extract_group_by(sql)
    order_by = _extract_order_by(sql)
    limit_value = _extract_limit(sql)
    aggregations = _extract_aggregations(sql)
    intent = "read"
    if sql.strip().lower().startswith(("insert", "update", "delete")):
        intent = "write"
    confidence = 0.6
    if tables:
        confidence += 0.2
    if filters or limit_value is not None:
        confidence += 0.1
    if joins:
        confidence += 0.1
    confidence = min(confidence, 1.0)

    join_paths = []
    if schema:
        graph = _build_schema_graph(schema)
        for i, left in enumerate(tables):
            for right in tables[i + 1 :]:
                path = _find_join_path(graph, left, right)
                if path:
                    join_paths.append({"from": left, "to": right, "path": path})

    return {
        "intent": intent,
        "tables": tables,
        "joins": joins,
        "filters": filters,
        "aggregations": aggregations,
        "group_by": group_by,
        "order_by": order_by,
        "limit": limit_value,
        "confidence": round(confidence, 2),
        "join_paths": join_paths,
    }


def _walk_plan_nodes(plan: dict) -> list[dict]:
    if not plan:
        return []
    nodes = [plan]
    for child in plan.get("Plans", []) or []:
        nodes.extend(_walk_plan_nodes(child))
    return nodes


def _estimate_from_plan(dialect: str, explain_rows: list[dict]) -> dict:
    estimate = {"estimate_ms": None, "plan_rows": None, "total_cost": None}
    if dialect in {"postgresql", "postgres"}:
        plan = _extract_postgres_plan(explain_rows)
        if not plan:
            return estimate
        total_cost = plan.get("Total Cost")
        plan_rows = plan.get("Plan Rows")
        estimate["total_cost"] = total_cost
        estimate["plan_rows"] = plan_rows
        if isinstance(total_cost, (int, float)):
            estimate["estimate_ms"] = round(float(total_cost), 2)
    return estimate


def _detect_plan_risks(dialect: str, explain_rows: list[dict]) -> list[str]:
    risks = []
    if dialect in {"postgresql", "postgres"}:
        plan = _extract_postgres_plan(explain_rows)
        for node in _walk_plan_nodes(plan):
            if node.get("Node Type") == "Seq Scan":
                rel = node.get("Relation Name") or "table"
                risks.append(f"Sequential scan on {rel}.")
            if node.get("Node Type") == "Nested Loop":
                plan_rows = node.get("Plan Rows")
                if isinstance(plan_rows, (int, float)) and plan_rows > 5000:
                    risks.append("Large nested loop join detected.")
    if dialect == "sqlite":
        for row in explain_rows:
            detail = str(row.get("detail", ""))
            if "SCAN" in detail.upper():
                risks.append("Full table scan detected.")
    return risks


def _suggest_indexes_from_sql(sql: str) -> list[str]:
    """Return naive index suggestions derived from SQL text."""
    text = sql.lower()
    suggestions = []
    join_matches = re.findall(
        r"join\\s+([a-z0-9_]+)\\s+on\\s+([a-z0-9_]+)\\.([a-z0-9_]+)",
        text,
    )
    for _, table, column in join_matches:
        suggestions.append(f"Consider index on {table}.{column}.")

    where_matches = re.findall(r"where\\s+([a-z0-9_]+)\\.([a-z0-9_]+)", text)
    for table, column in where_matches:
        suggestions.append(f"Consider index on {table}.{column}.")

    order_matches = re.findall(r"order\\s+by\\s+([a-z0-9_]+)\\.([a-z0-9_]+)", text)
    for table, column in order_matches:
        suggestions.append(f"Consider index on {table}.{column} for ORDER BY.")

    return list(dict.fromkeys(suggestions))


def _assess_query_risk(sql: str, plan_meta: dict) -> dict:
    # Lightweight heuristics to flag common slow-query patterns.
    text = sql.strip().lower()
    risks = []
    improvements = []
    score = 0.0

    if " where " not in f" {text} " and not has_limit(text):
        risks.append("SELECT without WHERE or LIMIT.")
        improvements.append("Add WHERE filters to reduce scanned rows.")
        score += 0.3

    if " join " in f" {text} ":
        risks.append("JOIN detected; ensure indexed join keys.")
        improvements.append("Add indexes on JOIN columns if missing.")
        score += 0.1

    if re.search(r"like\\s+'%.*%'", text):
        risks.append("Leading wildcard LIKE can be slow.")
        improvements.append("Prefer prefix search or use a trigram/full-text index.")
        score += 0.2

    if " order by " in f" {text} " and not has_limit(text):
        risks.append("ORDER BY without LIMIT can be expensive.")
        improvements.append("Add LIMIT when ordering large tables.")
        score += 0.1

    if re.search(r"\\bselect\\s+\\*\\b", text):
        risks.append("SELECT * can fetch unnecessary columns.")
        improvements.append("Select only the columns you need.")
        score += 0.05

    total_cost = plan_meta.get("total_cost")
    if isinstance(total_cost, (int, float)) and total_cost > 10000:
        risks.append("High planner cost detected.")
        improvements.append("Consider adding WHERE filters or indexes.")
        score += 0.2

    risks.extend(plan_meta.get("plan_risks", []))
    if plan_meta.get("plan_risks"):
        score += 0.2

    improvements.extend(_suggest_indexes_from_sql(text))

    if not improvements:
        improvements.append("Query looks reasonable; no obvious improvements detected.")

    score = min(score, 1.0)
    return {
        "risk_score": round(score, 2),
        "risky_reasons": risks,
        "improvements": improvements,
    }


def build_query_plan(
    sql: str, adapter: SqlAdapter, safe_limit: int, schema: dict | None = None
) -> dict:
    explain = _run_explain(sql, adapter)
    plan_rows = explain.get("rows", [])
    plan_meta = _estimate_from_plan(explain.get("dialect", "sql"), plan_rows)
    plan_meta["plan_risks"] = _detect_plan_risks(
        explain.get("dialect", "sql"), plan_rows
    )
    risk = _assess_query_risk(sql, plan_meta)
    plan_json = _build_plan_json(sql, schema=schema)
    risk_level = "low"
    if risk["risk_score"] >= 0.7:
        risk_level = "high"
    elif risk["risk_score"] >= 0.4:
        risk_level = "medium"

    # Enforce a safety LIMIT when the query does not specify one.
    safe_sql, limit_added = apply_limit(sql, safe_limit)
    notes = []
    if limit_added:
        notes.append(f"Added LIMIT {safe_limit} for safety.")
    if plan_meta.get("estimate_ms") is not None:
        notes.append("Runtime estimate is based on EXPLAIN cost (rough estimate).")
    else:
        notes.append("Runtime estimate unavailable for this dialect.")

    plan = {
        "explain": explain,
        "estimate_ms": plan_meta.get("estimate_ms"),
        "plan_rows": plan_meta.get("plan_rows"),
        "total_cost": plan_meta.get("total_cost"),
        "risk_score": risk["risk_score"],
        "risk_level": risk_level,
        "risky_reasons": risk["risky_reasons"],
        "improvements": risk["improvements"],
        "plan_json": plan_json,
        "safe_sql": safe_sql,
        "notes": notes,
    }
    return QueryPlanDto.from_dict(plan).to_dict()
