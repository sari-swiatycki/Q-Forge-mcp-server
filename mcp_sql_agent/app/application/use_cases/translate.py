from collections.abc import Callable
import time

from mcp_sql_agent.app.application.query_cache import QueryCache, build_cache_key
from mcp_sql_agent.app.domain.ports import LlmTranslator, SqlAdapterProvider


class TranslateUseCase:
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translator_provider: Callable[[], LlmTranslator],
        cache: QueryCache | None = None,
    ) -> None:
        self._adapter_provider = adapter_provider
        self._translator_provider = translator_provider
        self._cache = cache or QueryCache()

    def execute(self, nl_query: str, db_url: str | None = None) -> str:
        result = self.execute_with_meta(nl_query, db_url=db_url)
        return result["sql"]

    def execute_with_meta(self, nl_query: str, db_url: str | None = None) -> dict:
        adapter = self._adapter_provider.get_adapter(db_url)
        schema_start = time.perf_counter()
        schema = adapter.get_schema()
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
        sql = translator.translate(nl_query, tables, dialect)
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
