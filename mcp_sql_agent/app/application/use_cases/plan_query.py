import time

from mcp_sql_agent.app.application.sql_planning import build_query_plan
from mcp_sql_agent.app.application.safety_policy import evaluate_policy
from mcp_sql_agent.app.application.use_cases.translate import TranslateUseCase
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class PlanQueryUseCase:
    """Translate NL to SQL and return a safety/risk-aware plan."""
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translate_use_case: TranslateUseCase,
    ) -> None:
        """Create the use case with translation and adapter dependencies."""
        self._adapter_provider = adapter_provider
        self._translate = translate_use_case

    async def execute(
        self, nl_query: str, db_url: str | None = None, safe_limit: int = 1000
    ) -> dict:
        """Translate the query and build a plan without executing SQL.

        Args:
            nl_query: Natural language request from the caller.
            db_url: Optional override for the default DB URL.
            safe_limit: Max rows used for safety checks and planning.
        Returns:
            Dict containing SQL, recommended SQL, EXPLAIN output, risk signals,
            and metrics.
        """
        meta = await self._translate.execute_with_meta(nl_query, db_url=db_url)
        sql = meta["sql"]
        adapter = self._adapter_provider.get_adapter(db_url)
        plan_start = time.perf_counter()
        plan = await build_query_plan(
            sql, adapter, safe_limit=safe_limit, schema=meta["schema"]
        )
        compile_sql_ms = round((time.perf_counter() - plan_start) * 1000, 2)
        policy = evaluate_policy(sql, plan, read_only=True)
        metrics = {
            "schema_ms": meta["schema_ms"],
            "llm_ms": meta["llm_ms"],
            "compile_sql_ms": compile_sql_ms,
            "db_exec_ms": None,
            "rows_returned": None,
            "cache_hit": meta["cache_hit"],
        }
        return {
            "nl_query": nl_query,
            "sql": sql,
            "recommended_sql": plan.get("safe_sql", sql),
            "plan": plan,
            "metrics": metrics,
            "policy": policy,
        }
