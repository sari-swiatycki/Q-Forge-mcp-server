import json

from mcp_sql_agent.app.application import audit_log
from mcp_sql_agent.app.application import erd_rendering
from mcp_sql_agent.app.application import query_cache
from mcp_sql_agent.app.application import safety_policy


def test_query_cache_expires(monkeypatch):
    cache = query_cache.QueryCache(ttl_seconds=5)
    now = [100.0]
    monkeypatch.setattr(query_cache.time, "time", lambda: now[0])

    cache.set("k", "v")
    assert cache.get("k") == "v"

    now[0] = 106.0
    assert cache.get("k") is None


def test_build_cache_key_stable_for_schema_order():
    schema_a = {"tables": {"users": [{"name": "id"}]}, "foreign_keys": []}
    schema_b = {"foreign_keys": [], "tables": {"users": [{"name": "id"}]}}

    key_a = query_cache.build_cache_key("list users", schema_a)
    key_b = query_cache.build_cache_key("list users", schema_b)
    assert key_a == key_b


def test_write_event_uses_env_path(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(log_path))

    audit_log.write_event({"event": "ok"})

    payload = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "ok"
    assert "ts" in payload


def test_build_erd_mermaid_sanitizes_schema():
    schema = {
        "tables": {
            "Order Items": [{"name": "item id", "type": "int"}],
        },
        "foreign_keys": [
            {
                "table": "Order Items",
                "referred_table": "Users",
                "columns": ["user id"],
            }
        ],
    }

    diagram = erd_rendering.build_erd_mermaid(schema)
    assert diagram.startswith("erDiagram")
    assert "Order_Items" in diagram
    assert "int item_id" in diagram
    assert "Users ||--o{ Order_Items" in diagram
    assert "user_id" in diagram


def test_evaluate_policy_blocks_write():
    res = safety_policy.evaluate_policy("UPDATE users SET name='x'", {}, read_only=True)
    assert res["allowed"] is False
    assert res["policy"] == "READ_ONLY"


def test_evaluate_policy_blocks_multiple_statements():
    res = safety_policy.evaluate_policy("SELECT 1; SELECT 2", {}, read_only=True)
    assert res["allowed"] is False
    assert res["policy"] == "SINGLE_STATEMENT"


def test_evaluate_policy_blocks_join_complexity():
    sql = (
        "select * from a "
        "join b on a.id=b.a_id "
        "join c on b.id=c.b_id "
        "join d on c.id=d.c_id"
    )
    res = safety_policy.evaluate_policy(sql, {}, read_only=True)
    assert res["allowed"] is False
    assert res["policy"] == "JOIN_COMPLEXITY"


def test_evaluate_policy_allows_safe_limit_applied():
    plan = {"safe_sql": "select * from users limit 10", "risk_score": 0.1}
    res = safety_policy.evaluate_policy("select * from users", plan, read_only=True)
    assert res["allowed"] is True
    assert res["policy"] == "SAFE_LIMIT_APPLIED"


def test_evaluate_policy_blocks_unbounded_without_safe_limit():
    res = safety_policy.evaluate_policy("select * from users", {}, read_only=True)
    assert res["allowed"] is False
    assert res["policy"] == "UNBOUNDED_READ"


def test_evaluate_policy_blocks_high_risk():
    plan = {"risk_score": 0.9}
    res = safety_policy.evaluate_policy(
        "select * from users where id=1", plan, read_only=True
    )
    assert res["allowed"] is False
    assert res["policy"] == "RISK_THRESHOLD"
