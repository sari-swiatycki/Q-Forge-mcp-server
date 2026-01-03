from pathlib import Path

from mcp_sql_agent.app.application.sql_agent_service import SqlAgentService
from mcp_sql_agent.app.infrastructure.db.sqlalchemy_adapter import SQLAlchemyAdapter
from mcp_sql_agent.app.infrastructure import db_context
from mcp_sql_agent.app.application.sql_formatting import format_table
from mcp_sql_agent.app.application.sql_planning import build_query_plan
from mcp_sql_agent.app.application.sql_validation import (
    apply_limit,
    has_limit,
    validate_sql_select,
)


def _make_sqlite_adapter(tmp_path: Path) -> SQLAlchemyAdapter:
    db_path = tmp_path / "test.db"
    adapter = SQLAlchemyAdapter(f"sqlite:///{db_path}")
    with adapter.engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER)"
        )
        conn.exec_driver_sql(
            "INSERT INTO orders (id, user_id) VALUES (1, 10), (2, 11)"
        )
    return adapter


class _FakeTranslator:
    def __init__(self):
        self.calls = []

    def translate(self, nl_query: str, schema: dict, dialect: str) -> str:
        self.calls.append((nl_query, schema, dialect))
        return "SELECT * FROM orders"


def test_validate_sql_select_allows_with_cte():
    ok, err = validate_sql_select("WITH x AS (SELECT 1) SELECT * FROM x")
    assert ok is True
    assert err == ""


def test_has_limit_detects_limit_any_case():
    assert has_limit("select * from t limit 1") is True
    assert has_limit("select * from t LiMiT 1") is True


def test_apply_limit_adds_when_missing():
    sql, added = apply_limit("select * from t", 25)
    assert added is True
    assert sql.endswith("LIMIT 25")


def test_format_table_grid_has_borders():
    rows = [{"id": 1, "name": "Alice"}]
    table = format_table(rows, style="grid")
    lines = table.splitlines()
    assert lines[0].startswith("+")
    assert lines[0].endswith("+")
    assert "Alice" in table


def test_build_query_plan_sqlite(tmp_path):
    adapter = _make_sqlite_adapter(tmp_path)
    plan = build_query_plan("SELECT * FROM orders", adapter, safe_limit=5)
    assert "explain" in plan
    assert "safe_sql" in plan
    assert plan["safe_sql"].endswith("LIMIT 5")


def test_translate_uses_schema(monkeypatch, tmp_path):
    adapter = _make_sqlite_adapter(tmp_path)
    context = db_context.DbContext(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(context, "_adapter", adapter)
    translator = _FakeTranslator()
    service = SqlAgentService(context, lambda: translator)
    sql = service.translate("all orders")
    assert sql == "SELECT * FROM orders"
    assert translator.calls[0][0] == "all orders"
    assert "orders" in translator.calls[0][1]
    assert translator.calls[0][2] == "sqlite"
