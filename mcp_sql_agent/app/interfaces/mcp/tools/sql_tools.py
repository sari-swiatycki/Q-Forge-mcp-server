import logging

from mcp.server.fastmcp import FastMCP

from mcp_sql_agent.app.app_container import build_sql_agent_service
from mcp_sql_agent.app.application.sql_agent_service import SqlAgentService


logger = logging.getLogger(__name__)

mcp = FastMCP("sql")
_service: SqlAgentService | None = None


def _get_service() -> SqlAgentService:
    """Return the singleton SqlAgentService, lazily initialized.

    Side Effects:
        May construct the DI container and instantiate the service on first use.
    """
    # Lazy init to avoid loading OpenAI client unless a tool is actually used.
    global _service
    if _service is None:
        _service = build_sql_agent_service()
    return _service


def _set_service(service: SqlAgentService) -> None:
    """Override the singleton service instance (test helper).

    Side Effects:
        Replaces the process-global service instance used by MCP tools.
    """
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
async def resource_db_schema() -> dict:
    """Return schema metadata for the active database.

    Returns:
        JSON-serializable dict with tables, columns, and relationships.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().get_schema()
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
async def resource_db_erd() -> dict:
    """Return an ER diagram payload for the active database.

    Returns:
        JSON-serializable dict, typically containing Mermaid ER diagram text.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().get_erd()
    except Exception as exc:
        logger.exception("resource_db_erd failed")
        return {"error": str(exc)}


@mcp.prompt(
    name="nl_to_sql",
    title="NL to SQL",
    description="Translate a natural language request into SQL using the current schema.",
)
async def prompt_nl_to_sql(nl_query: str) -> list[dict]:
    """Build the prompt sequence for NL -> SQL translation.

    Args:
        nl_query: Natural language request from the user.
    Returns:
        List of MCP prompt messages including the current schema resource.
    """
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
async def prompt_sql_safety_check(sql: str) -> list[dict]:
    """Build the prompt sequence for SQL safety review.

    Args:
        sql: SQL to review.
    Returns:
        List of MCP prompt messages including the current schema resource.
    """
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
async def ping() -> str:
    """Health check tool.

    Returns:
        "pong" if the server is reachable.
    """
    return "pong"


@mcp.tool()
async def get_schema(db_url: str | None = None) -> dict:
    """Return database schema for the configured or provided DB URL.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        JSON-serializable dict of schema metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().get_schema(db_url=db_url)
    except Exception as exc:
        logger.exception("get_schema failed")
        return {"error": str(exc)}


@mcp.tool()
async def nl_to_sql(
    nl_query: str,
    db_url: str | None = None,
    include_plan: bool = True,
    safe_limit: int = 1000,
) -> dict:
    """Translate natural language into SQL.

    Args:
        nl_query: Natural language request.
        db_url: Optional override for the default DB URL.
        include_plan: When True, returns a plan with risk signals and EXPLAIN.
        safe_limit: Max rows used for safety checks and planning.
    Returns:
        Dict with SQL (and optionally plan metadata).
    Errors:
        Returns {"error": "<message>", "nl_query": "<input>"} on failure.
    """
    try:
        if include_plan:
            return await _get_service().plan_query(
                nl_query, db_url=db_url, safe_limit=safe_limit
            )
        sql = await _get_service().translate(nl_query, db_url=db_url)
        return {"nl_query": nl_query, "sql": sql}
    except Exception as exc:
        logger.exception("nl_to_sql failed")
        return {"error": str(exc), "nl_query": nl_query}


@mcp.tool()
async def run_sql(
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
    """Execute a SELECT/CTE query with optional safety checks and formatting.

    Args:
        sql: SQL to run.
        format_table: When True, returns a formatted table string.
        table_style: Table style for formatted output (e.g., "simple").
        db_url: Optional override for the default DB URL.
        safe: When True, enforce read-only safety policy and row limits.
        safe_limit: Max rows to return/preview when safety is enabled.
        mode: "execute" (default) or "preview"/"explain" behavior.
        preview_limit: Row cap for preview mode.
        output_format: Output format (e.g., "json", "csv", "table").
    Returns:
        Dict with result rows and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().run_sql(
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
async def db_debug() -> dict:
    """Return process and DB connection debug metadata.

    Returns:
        JSON-serializable dict with process, DB, and config hints.
    """
    return await _get_service().db_debug()


@mcp.tool()
async def run_sql_write(sql: str, db_url: str | None = None) -> dict:
    """
    Execute INSERT/UPDATE/DELETE statements only.

    Args:
        sql: Write statement to execute.
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with write outcome and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().run_sql_write(
            sql, db_url=db_url, allow_write=False
        )
    except Exception as exc:
        logger.exception("run_sql_write failed")
        return {"error": str(exc)}


@mcp.tool()
async def run_sql_write_approved(sql: str, db_url: str | None = None) -> dict:
    """
    Execute INSERT/UPDATE/DELETE with explicit approval.

    Args:
        sql: Write statement to execute.
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with write outcome and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().run_sql_write(
            sql, db_url=db_url, allow_write=True
        )
    except Exception as exc:
        logger.exception("run_sql_write_approved failed")
        return {"error": str(exc)}


@mcp.tool()
async def list_tables(db_url: str | None = None) -> dict:
    """List available table names for the configured or provided DB URL.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with table name list and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().list_tables(db_url=db_url)
    except Exception as exc:
        logger.exception("list_tables failed")
        return {"error": str(exc)}


@mcp.tool()
async def get_erd(db_url: str | None = None) -> dict:
    """Return a Mermaid ER diagram for the configured or provided DB URL.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with Mermaid ER diagram text and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().get_erd(db_url=db_url)
    except Exception as exc:
        logger.exception("get_erd failed")
        return {"error": str(exc)}


@mcp.tool()
async def ask_db(
    nl_query: str,
    execute: bool = False,
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

    Args:
        nl_query: Natural language request.
        execute: When True, run the SQL and return results.
        format_table: When True, return a formatted table string.
        table_style: Table style for formatted output (e.g., "simple").
        db_url: Optional override for the default DB URL.
        safe: When True, enforce read-only safety policy and row limits.
        safe_limit: Max rows to return/preview when safety is enabled.
        mode: "execute" (default) or "preview"/"explain" behavior.
        preview_limit: Row cap for preview mode.
        output_format: Output format (e.g., "json", "csv", "table").
    Returns:
        Dict with SQL, recommended SQL, plan metadata, and optional results.
    """
    return await _get_service().ask_db(
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
async def explain_sql(
    sql: str, db_url: str | None = None, safe_limit: int = 1000
) -> dict:
    """Return EXPLAIN-based plan without executing the query.

    Args:
        sql: SQL to explain.
        db_url: Optional override for the default DB URL.
        safe_limit: Max rows used for safety checks.
    Returns:
        Dict with EXPLAIN plan and metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().run_sql(
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
async def set_db_url(db_url: str) -> dict:
    """
    Update the default DB URL for this process.

    Args:
        db_url: New default DB URL for subsequent tool calls.
    Returns:
        Dict with updated configuration metadata.
    Errors:
        Returns {"error": "<message>"} on failure.
    """
    try:
        return await _get_service().set_db_url(db_url)
    except Exception as exc:
        logger.exception("set_db_url failed")
        return {"error": str(exc)}


@mcp.tool()
async def plan_query(
    nl_query: str,
    db_url: str | None = None,
    safe_limit: int = 1000,
) -> dict:
    """
    Plan a query without executing it. Returns SQL, EXPLAIN, and risk signals.

    Args:
        nl_query: Natural language request.
        db_url: Optional override for the default DB URL.
        safe_limit: Max rows used for safety checks and planning.
    Returns:
        Dict with SQL, EXPLAIN, and risk metadata.
    Errors:
        Returns {"error": "<message>", "nl_query": "<input>"} on failure.
    """
    try:
        return await _get_service().plan_query(
            nl_query, db_url=db_url, safe_limit=safe_limit
        )
    except Exception as exc:
        logger.exception("plan_query failed")
        return {"error": str(exc), "nl_query": nl_query}
