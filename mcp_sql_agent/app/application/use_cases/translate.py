from collections.abc import Callable
import time

from mcp_sql_agent.app.application.query_cache import QueryCache, build_cache_key
from mcp_sql_agent.app.domain.ports import LlmTranslator, SqlAdapterProvider


class TranslateUseCase:
    """Translate natural language requests to SQL with caching."""
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translator_provider: Callable[[], LlmTranslator],
        cache: QueryCache | None = None,
    ) -> None:
        """Create the use case with adapter and translator providers."""
        self._adapter_provider = adapter_provider
        self._translator_provider = translator_provider
        self._cache = cache or QueryCache()

    async def execute(self, nl_query: str, db_url: str | None = None) -> str:
        """Translate a natural language query into SQL only.

        Args:
            nl_query: Natural language request from the caller.
            db_url: Optional override for the default DB URL.
        Returns:
            SQL string only, without metadata.
        """
        result = await self.execute_with_meta(nl_query, db_url=db_url)
        return result["sql"]

    async def execute_with_meta(self, nl_query: str, db_url: str | None = None) -> dict:
        """Translate a query and return SQL with schema and timing metadata.

        Args:
            nl_query: Natural language request from the caller.
            db_url: Optional override for the default DB URL.
        Returns:
            Dict with SQL, schema, dialect, timing metrics, and cache status.
        """
        adapter = self._adapter_provider.get_adapter(db_url)
        schema_start = time.perf_counter()
        schema = await adapter.get_schema()
        schema_ms = round((time.perf_counter() - schema_start) * 1000, 2)
        dialect = schema.get("dialect", "sql")
        tables = schema.get("tables", {})
        cache_key = build_cache_key(nl_query, schema)
        cached = self._cache.get(cache_key)
        if cached:
            return {
                "sql": cached,
                "schema": schema,
                "dialect": dialect,
                "schema_ms": schema_ms,
                "llm_ms": 0.0,
                "cache_hit": True,
            }

        llm_start = time.perf_counter()
        translator = self._translator_provider()
        sql = await translator.translate(nl_query, tables, dialect)
        llm_ms = round((time.perf_counter() - llm_start) * 1000, 2)
        self._cache.set(cache_key, sql)
        return {
            "sql": sql,
            "schema": schema,
            "dialect": dialect,
            "schema_ms": schema_ms,
            "llm_ms": llm_ms,
            "cache_hit": False,
        }
