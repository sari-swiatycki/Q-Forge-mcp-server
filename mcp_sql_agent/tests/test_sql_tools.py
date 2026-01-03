from pathlib import Path

from mcp_sql_agent.app.application.sql_agent_service import SqlAgentService  # noqa: E402
from mcp_sql_agent.app.infrastructure.db.sqlalchemy_adapter import (  # noqa: E402
    SQLAlchemyAdapter,
)
from mcp_sql_agent.app.interfaces.mcp.tools import sql_tools  # noqa: E402
from mcp_sql_agent.app.infrastructure import db_context  # noqa: E402
from mcp_sql_agent.app.application.sql_formatting import format_table  # noqa: E402
from mcp_sql_agent.app.application.sql_validation import validate_sql_select  # noqa: E402


def _make_sqlite_adapter(tmp_path: Path) -> SQLAlchemyAdapter:
    db_path = tmp_path / "test.db"
    adapter = SQLAlchemyAdapter(f"sqlite:///{db_path}")
    with adapter.engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        conn.exec_driver_sql(
            "INSERT INTO users (id, name) VALUES (1, 'Alice'), (2, 'Bob')"
        )
    return adapter


class _FakeTranslator:
    def translate(self, nl_query: str, schema: dict, dialect: str) -> str:
        return "SELECT 1"


def _set_test_service(tmp_path, monkeypatch, adapter: SQLAlchemyAdapter | None = None):
    context = db_context.DbContext(f"sqlite:///{tmp_path / 'test.db'}")
    if adapter is not None:
        monkeypatch.setattr(context, "_adapter", adapter)
    sql_tools._set_service(SqlAgentService(context, lambda: _FakeTranslator()))


def test_validate_sql_select_allows_select():
    ok, err = validate_sql_select("SELECT * FROM users")
    assert ok is True
    assert err == ""


def test_validate_sql_select_blocks_write():
    ok, err = validate_sql_select("DELETE FROM users")
    assert ok is False
    assert err == "Only SELECT queries are allowed."


def test_validate_sql_select_blocks_multiple_statements():
    ok, err = validate_sql_select("SELECT 1; SELECT 2")
    assert ok is False
    assert "Multiple statements" in err


def test_format_table_returns_aligned_table():
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    table = format_table(rows)
    lines = table.splitlines()
    assert lines[0].startswith("id")
    assert "name" in lines[0]
    assert lines[1].startswith("-")
    assert "Alice" in lines[2]
    assert "Bob" in lines[3]


def test_run_sql_executes_select_on_sqlite(tmp_path, monkeypatch):
    adapter = _make_sqlite_adapter(tmp_path)
    _set_test_service(tmp_path, monkeypatch, adapter)

    res = sql_tools.run_sql("SELECT name FROM users ORDER BY id")
    assert res["row_count"] == 2
    assert res["rows"] == [{"name": "Alice"}, {"name": "Bob"}]


def test_run_sql_write_updates_rows(tmp_path):
    adapter = _make_sqlite_adapter(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'test.db'}"

    sql_tools._set_service(
        SqlAgentService(db_context.DbContext(db_url), lambda: _FakeTranslator())
    )
    res = sql_tools.run_sql_write_approved(
        "UPDATE users SET name='Dana' WHERE id=2", db_url=db_url
    )
    assert res["row_count"] == 1

    rows = adapter.query("SELECT name FROM users WHERE id=2")
    assert rows == [{"name": "Dana"}]


def test_run_sql_write_blocks_select():
    sql_tools._set_service(
        SqlAgentService(
            db_context.DbContext("sqlite:///:memory:"), lambda: _FakeTranslator()
        )
    )
    res = sql_tools.run_sql_write("SELECT * FROM users")
    assert "error" in res
