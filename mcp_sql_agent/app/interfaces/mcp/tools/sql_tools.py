import logging

from mcp.server.fastmcp import FastMCP

from mcp_sql_agent.app.app_container import build_sql_agent_service
from mcp_sql_agent.app.application.sql_agent_service import SqlAgentService


logger = logging.getLogger(__name__)

mcp = FastMCP("sql")
_service: SqlAgentService | None = None


def _get_service() -> SqlAgentService:
    # Lazy init to avoid loading OpenAI client unless a tool is actually used.
    global _service
    if _service is None:
        _service = build_sql_agent_service()
    return _service


def _set_service(service: SqlAgentService) -> None:
    # Testing hook to inject a fake service without touching globals elsewhere.
    global _service
    _service = service


@mcp.resource(
    "resource://db/schema",
    name="db_schema",
    title="Database schema",
    description="Current database schema (tables, columns, relationships).",
    mime_type="application/json",
)
def resource_db_schema() -> dict:
    """Return the current database schema for the default DB URL."""
    try:
        return _get_service().get_schema()
    except Exception as exc:
        logger.exception("resource_db_schema failed")
        return {"error": str(exc)}


@mcp.resource(
    "resource://db/erd",
    name="db_erd",
    title="Database ERD",
    description="Mermaid ER diagram for the current database.",
    mime_type="application/json",
)
def resource_db_erd() -> dict:
    """Return an ER diagram payload for the default DB URL."""
    try:
        return _get_service().get_erd()
    except Exception as exc:
        logger.exception("resource_db_erd failed")
        return {"error": str(exc)}


@mcp.prompt(
    name="nl_to_sql",
    title="NL to SQL",
    description="Translate a natural language request into SQL using the current schema.",
)
def prompt_nl_to_sql(nl_query: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "You are a SQL assistant. Use the provided schema. Return only SQL.",
        },
        {
            "role": "user",
            "content": {"type": "resource", "resource": {"uri": "resource://db/schema"}},
        },
        {"role": "user", "content": f"Request: {nl_query}"},
    ]


@mcp.prompt(
    name="sql_safety_check",
    title="SQL safety check",
    description="Review a SQL query for safety and suggest improvements.",
)
def prompt_sql_safety_check(sql: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": "Review the SQL for safety and performance risks. Suggest improvements.",
        },
        {
            "role": "user",
            "content": {"type": "resource", "resource": {"uri": "resource://db/schema"}},
        },
        {"role": "user", "content": f"SQL:\n{sql}"},
    ]


@mcp.tool()
def ping() -> str:
    """Health check tool. Returns 'pong'."""
    return "pong"


@mcp.tool()
def get_schema(db_url: str | None = None) -> dict:
    """Return database schema for the configured or provided DB URL."""
    try:
        return _get_service().get_schema(db_url=db_url)
    except Exception as exc:
        logger.exception("get_schema failed")
        return {"error": str(exc)}


@mcp.tool()
def nl_to_sql(
    nl_query: str,
    db_url: str | None = None,
    include_plan: bool = True,
    safe_limit: int = 1000,
) -> dict:
    """Translate natural language into SQL, optionally including a plan."""
    try:
        if include_plan:
            return _get_service().plan_query(
                nl_query, db_url=db_url, safe_limit=safe_limit
            )
        sql = _get_service().translate(nl_query, db_url=db_url)
        return {"nl_query": nl_query, "sql": sql}
    except Exception as exc:
        logger.exception("nl_to_sql failed")
        return {"error": str(exc), "nl_query": nl_query}


@mcp.tool()
def run_sql(
    sql: str,
    format_table: bool = False,
    table_style: str = "simple",
    db_url: str | None = None,
    safe: bool = True,
    safe_limit: int = 1000,
    mode: str = "execute",
    preview_limit: int = 50,
    output_format: str = "json",
) -> dict:
    """Execute a SELECT/CTE query with optional safety checks and formatting."""
    try:
        return _get_service().run_sql(
            sql,
            format_table_result=format_table,
            table_style=table_style,
            db_url=db_url,
            safe=safe,
            safe_limit=safe_limit,
            mode=mode,
            preview_limit=preview_limit,
            output_format=output_format,
        )
    except Exception as exc:
        logger.exception("run_sql failed")
        return {"error": str(exc)}


@mcp.tool()
def db_debug() -> dict:
    """Return process and DB connection debug metadata."""
    return _get_service().db_debug()


@mcp.tool()
def run_sql_write(sql: str, db_url: str | None = None) -> dict:
    """
    Execute INSERT/UPDATE/DELETE statements only.
    """
    try:
        return _get_service().run_sql_write(sql, db_url=db_url, allow_write=False)
    except Exception as exc:
        logger.exception("run_sql_write failed")
        return {"error": str(exc)}


@mcp.tool()
def run_sql_write_approved(sql: str, db_url: str | None = None) -> dict:
    """
    Execute INSERT/UPDATE/DELETE with explicit approval.
    """
    try:
        return _get_service().run_sql_write(sql, db_url=db_url, allow_write=True)
    except Exception as exc:
        logger.exception("run_sql_write_approved failed")
        return {"error": str(exc)}


@mcp.tool()
def list_tables(db_url: str | None = None) -> dict:
    """List available table names for the configured or provided DB URL."""
    try:
        return _get_service().list_tables(db_url=db_url)
    except Exception as exc:
        logger.exception("list_tables failed")
        return {"error": str(exc)}


@mcp.tool()
def get_erd(db_url: str | None = None) -> dict:
    """Return a Mermaid ER diagram for the configured or provided DB URL."""
    try:
        return _get_service().get_erd(db_url=db_url)
    except Exception as exc:
        logger.exception("get_erd failed")
        return {"error": str(exc)}


@mcp.tool()
def ask_db(
    nl_query: str,
    execute: bool = True,
    format_table: bool = False,
    table_style: str = "simple",
    db_url: str | None = None,
    safe: bool = True,
    safe_limit: int = 1000,
    mode: str = "execute",
    preview_limit: int = 50,
    output_format: str = "json",
) -> dict:
    """
    One tool: NL -> SQL -> optional execute -> return.
    """
    return _get_service().ask_db(
        nl_query,
        execute=execute,
        format_table_result=format_table,
        table_style=table_style,
        db_url=db_url,
        safe=safe,
        safe_limit=safe_limit,
        mode=mode,
        preview_limit=preview_limit,
        output_format=output_format,
    )


@mcp.tool()
def explain_sql(sql: str, db_url: str | None = None, safe_limit: int = 1000) -> dict:
    """Return EXPLAIN-based plan without executing the query."""
    try:
        return _get_service().run_sql(
            sql,
            db_url=db_url,
            safe=True,
            safe_limit=safe_limit,
            mode="explain",
        )
    except Exception as exc:
        logger.exception("explain_sql failed")
        return {"error": str(exc)}


@mcp.tool()
def set_db_url(db_url: str) -> dict:
    """
    Update the default DB URL for this process.
    """
    try:
        return _get_service().set_db_url(db_url)
    except Exception as exc:
        logger.exception("set_db_url failed")
        return {"error": str(exc)}


@mcp.tool()
def plan_query(
    nl_query: str,
    db_url: str | None = None,
    safe_limit: int = 1000,
) -> dict:
    """
    Plan a query without executing it. Returns SQL, EXPLAIN, and risk signals.
    """
    try:
        return _get_service().plan_query(nl_query, db_url=db_url, safe_limit=safe_limit)
    except Exception as exc:
        logger.exception("plan_query failed")
        return {"error": str(exc), "nl_query": nl_query}
