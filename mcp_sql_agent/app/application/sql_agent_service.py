from collections.abc import Callable

from mcp_sql_agent.app.application.audit_log import write_event
from mcp_sql_agent.app.application.query_cache import QueryCache
from mcp_sql_agent.app.application.use_cases.ask_db import AskDbUseCase
from mcp_sql_agent.app.application.use_cases.get_erd import GetErdUseCase
from mcp_sql_agent.app.application.use_cases.plan_query import PlanQueryUseCase
from mcp_sql_agent.app.application.use_cases.run_sql import RunSqlUseCase
from mcp_sql_agent.app.application.use_cases.run_sql_write import RunSqlWriteUseCase
from mcp_sql_agent.app.application.use_cases.translate import TranslateUseCase
from mcp_sql_agent.app.domain.ports import LlmTranslator, SqlAdapterProvider


class SqlAgentService:
    """Facade that coordinates SQL agent use cases and audit logging."""
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translator_provider: Callable[[], LlmTranslator],
    ):
        """Initialize the service with adapter and translator providers."""
        self._adapter_provider = adapter_provider
        self._translator_provider = translator_provider
        self._translator: LlmTranslator | None = None
        self._query_cache = QueryCache()
        # Use cases capture business workflows; this service is a thin facade.
        self._translate_use_case = TranslateUseCase(
            adapter_provider, self._get_translator, cache=self._query_cache
        )
        self._plan_query_use_case = PlanQueryUseCase(
            adapter_provider, self._translate_use_case
        )
        self._run_sql_use_case = RunSqlUseCase(adapter_provider)
        self._run_sql_write_use_case = RunSqlWriteUseCase(adapter_provider)
        self._ask_db_use_case = AskDbUseCase(
            adapter_provider, self._translate_use_case, self._run_sql_use_case
        )
        self._get_erd_use_case = GetErdUseCase(adapter_provider)

    def _get_translator(self) -> LlmTranslator:
        """Return a lazily constructed translator instance."""
        # Lazily build the translator to avoid OpenAI setup on cold paths.
        if self._translator is None:
            self._translator = self._translator_provider()
        return self._translator

    async def get_schema(self, db_url: str | None = None) -> dict:
        """Return schema metadata for the configured or provided DB URL.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict with tables, columns, and relationship metadata.
        """
        return await self._adapter_provider.get_schema(db_url)

    async def list_tables(self, db_url: str | None = None) -> dict:
        """Return table names for the configured or provided DB URL.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict with a "tables" list.
        """
        return await self._adapter_provider.list_tables(db_url)

    async def get_erd(self, db_url: str | None = None) -> dict:
        """Return a Mermaid ER diagram for the configured or provided DB URL.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict containing Mermaid ER diagram text.
        """
        return await self._get_erd_use_case.execute(db_url=db_url)

    async def translate(self, nl_query: str, db_url: str | None = None) -> str:
        """Translate a natural language request to SQL.

        Args:
            nl_query: Natural language request from the caller.
            db_url: Optional override for the default DB URL.
        Returns:
            SQL string only, without metadata.
        """
        return await self._translate_use_case.execute(nl_query, db_url=db_url)

    async def plan_query(
        self, nl_query: str, db_url: str | None = None, safe_limit: int = 1000
    ) -> dict:
        """Plan a query without executing it and record audit metadata.

        Args:
            nl_query: Natural language request from the caller.
            db_url: Optional override for the default DB URL.
            safe_limit: Max rows used for safety checks and planning.
        Returns:
            Dict with SQL, EXPLAIN, risk signals, and metrics.
        Side Effects:
            Appends an audit event to the configured audit log.
        """
        result = await self._plan_query_use_case.execute(
            nl_query, db_url=db_url, safe_limit=safe_limit
        )
        await write_event(
            {
                "event": "plan_query",
                "nl_query": nl_query,
                "db_url": db_url,
                "plan": result.get("plan", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    async def run_sql(
        self,
        sql: str,
        format_table_result: bool = False,
        table_style: str = "simple",
        db_url: str | None = None,
        safe: bool = True,
        safe_limit: int = 1000,
        mode: str = "execute",
        preview_limit: int = 50,
        output_format: str = "json",
    ) -> dict:
        """Execute a read query with safety checks, metrics, and audit logging.

        Args:
            sql: SQL statement to execute (SELECT/CTE only).
            format_table_result: When True, include a formatted table string.
            table_style: Table formatting style for table output.
            db_url: Optional override for the default DB URL.
            safe: When True, enforce read-only policy and safe LIMITs.
            safe_limit: Max rows used for safety checks and planning.
            mode: "execute" (default), "preview", or "explain".
            preview_limit: Row cap for preview mode.
            output_format: Output format (e.g., "json", "csv", "table").
        Returns:
            Dict with rows, policy metadata, and optional formatting.
        Side Effects:
            Appends an audit event to the configured audit log.
        """
        metrics = {
            "schema_ms": None,
            "llm_ms": None,
            "compile_sql_ms": None,
            "db_exec_ms": None,
            "rows_returned": None,
            "cache_hit": None,
        }
        result = await self._run_sql_use_case.execute(
            sql,
            format_table_result=format_table_result,
            table_style=table_style,
            db_url=db_url,
            safe=safe,
            safe_limit=safe_limit,
            mode=mode,
            preview_limit=preview_limit,
            output_format=output_format,
            metrics=metrics,
        )
        await write_event(
            {
                "event": "run_sql",
                "sql": sql,
                "db_url": db_url,
                "policy": result.get("policy", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    async def run_sql_write(
        self, sql: str, db_url: str | None = None, allow_write: bool = False
    ) -> dict:
        """Execute a write query subject to safety policy and audit logging.

        Args:
            sql: INSERT/UPDATE/DELETE statement to execute.
            db_url: Optional override for the default DB URL.
            allow_write: When True, allow writes through policy checks.
        Returns:
            Dict with affected row count and policy metadata.
        Side Effects:
            Appends an audit event to the configured audit log.
        """
        result = await self._run_sql_write_use_case.execute(
            sql, db_url=db_url, allow_write=allow_write
        )
        await write_event(
            {
                "event": "run_sql_write",
                "sql": sql,
                "db_url": db_url,
                "policy": result.get("policy", {}),
            }
        )
        return result

    async def ask_db(
        self,
        nl_query: str,
        execute: bool = False,
        format_table_result: bool = False,
        table_style: str = "simple",
        db_url: str | None = None,
        safe: bool = True,
        safe_limit: int = 1000,
        mode: str = "execute",
        preview_limit: int = 50,
        output_format: str = "json",
    ) -> dict:
        """Translate NL to SQL, optionally execute, and record audit metadata.

        Args:
            nl_query: Natural language request from the caller.
            execute: When True, run the SQL and return results.
            format_table_result: When True, include a formatted table string.
            table_style: Table formatting style for table output.
            db_url: Optional override for the default DB URL.
            safe: When True, enforce read-only policy and safe LIMITs.
            safe_limit: Max rows used for safety checks and planning.
            mode: "execute" (default), "preview", or "explain".
            preview_limit: Row cap for preview mode.
            output_format: Output format (e.g., "json", "csv", "table").
        Returns:
            Dict with SQL, recommended SQL, plan metadata, and optional results.
        Side Effects:
            Appends an audit event to the configured audit log.
        """
        result = await self._ask_db_use_case.execute(
            nl_query,
            execute=execute,
            format_table_result=format_table_result,
            table_style=table_style,
            db_url=db_url,
            safe=safe,
            safe_limit=safe_limit,
            mode=mode,
            preview_limit=preview_limit,
            output_format=output_format,
        )
        await write_event(
            {
                "event": "ask_db",
                "nl_query": nl_query,
                "db_url": db_url,
                "policy": result.get("policy", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    async def set_db_url(self, db_url: str) -> dict:
        """Update the default DB URL for subsequent operations.

        Args:
            db_url: New default DB URL for subsequent calls.
        Returns:
            Dict containing updated configuration metadata.
        """
        return await self._adapter_provider.set_db_url(db_url)

    async def db_debug(self) -> dict:
        """Return process and DB connection debug metadata.

        Returns:
            Dict with process, DB, and config hints.
        """
        return await self._adapter_provider.db_debug()
