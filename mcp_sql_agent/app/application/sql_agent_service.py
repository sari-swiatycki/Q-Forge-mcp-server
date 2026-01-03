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
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translator_provider: Callable[[], LlmTranslator],
    ):
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
        # Lazily build the translator to avoid OpenAI setup on cold paths.
        if self._translator is None:
            self._translator = self._translator_provider()
        return self._translator

    def get_schema(self, db_url: str | None = None) -> dict:
        return self._adapter_provider.get_schema(db_url)

    def list_tables(self, db_url: str | None = None) -> dict:
        return self._adapter_provider.list_tables(db_url)

    def get_erd(self, db_url: str | None = None) -> dict:
        return self._get_erd_use_case.execute(db_url=db_url)

    def translate(self, nl_query: str, db_url: str | None = None) -> str:
        return self._translate_use_case.execute(nl_query, db_url=db_url)

    def plan_query(
        self, nl_query: str, db_url: str | None = None, safe_limit: int = 1000
    ) -> dict:
        result = self._plan_query_use_case.execute(
            nl_query, db_url=db_url, safe_limit=safe_limit
        )
        write_event(
            {
                "event": "plan_query",
                "nl_query": nl_query,
                "db_url": db_url,
                "plan": result.get("plan", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    def run_sql(
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
        metrics = {
            "schema_ms": None,
            "llm_ms": None,
            "compile_sql_ms": None,
            "db_exec_ms": None,
            "rows_returned": None,
            "cache_hit": None,
        }
        result = self._run_sql_use_case.execute(
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
        write_event(
            {
                "event": "run_sql",
                "sql": sql,
                "db_url": db_url,
                "policy": result.get("policy", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    def run_sql_write(
        self, sql: str, db_url: str | None = None, allow_write: bool = False
    ) -> dict:
        result = self._run_sql_write_use_case.execute(
            sql, db_url=db_url, allow_write=allow_write
        )
        write_event(
            {
                "event": "run_sql_write",
                "sql": sql,
                "db_url": db_url,
                "policy": result.get("policy", {}),
            }
        )
        return result

    def ask_db(
        self,
        nl_query: str,
        execute: bool = True,
        format_table_result: bool = False,
        table_style: str = "simple",
        db_url: str | None = None,
        safe: bool = True,
        safe_limit: int = 1000,
        mode: str = "execute",
        preview_limit: int = 50,
        output_format: str = "json",
    ) -> dict:
        result = self._ask_db_use_case.execute(
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
        write_event(
            {
                "event": "ask_db",
                "nl_query": nl_query,
                "db_url": db_url,
                "policy": result.get("policy", {}),
                "metrics": result.get("metrics", {}),
            }
        )
        return result

    def set_db_url(self, db_url: str) -> dict:
        return self._adapter_provider.set_db_url(db_url)

    def db_debug(self) -> dict:
        return self._adapter_provider.db_debug()
