import time

from mcp_sql_agent.app.application.sql_planning import build_query_plan
from mcp_sql_agent.app.application.safety_policy import evaluate_policy
from mcp_sql_agent.app.application.use_cases.run_sql import RunSqlUseCase
from mcp_sql_agent.app.application.use_cases.translate import TranslateUseCase
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class AskDbUseCase:
    def __init__(
        self,
        adapter_provider: SqlAdapterProvider,
        translate_use_case: TranslateUseCase,
        run_sql_use_case: RunSqlUseCase,
    ) -> None:
        self._adapter_provider = adapter_provider
        self._translate = translate_use_case
        self._run_sql = run_sql_use_case

    def execute(
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
        meta = self._translate.execute_with_meta(nl_query, db_url=db_url)
        sql = meta["sql"]
        adapter = self._adapter_provider.get_adapter(db_url)
        plan_start = time.perf_counter()
        plan = build_query_plan(sql, adapter, safe_limit=safe_limit, schema=meta["schema"])
        compile_sql_ms = round((time.perf_counter() - plan_start) * 1000, 2)
        metrics = {
            "schema_ms": meta["schema_ms"],
            "llm_ms": meta["llm_ms"],
            "compile_sql_ms": compile_sql_ms,
            "db_exec_ms": None,
            "rows_returned": None,
            "cache_hit": meta["cache_hit"],
        }
        policy = evaluate_policy(sql, plan, read_only=True)
        result = {
            "nl_query": nl_query,
            "sql": sql,
            "executed": False,
            "plan": plan,
            "metrics": metrics,
            "policy": policy,
        }

        if execute:
            # Reuse the computed plan to keep cost and risk signals consistent.
            exec_res = self._run_sql.execute(
                sql,
                format_table_result=format_table_result,
                table_style=table_style,
                db_url=db_url,
                safe=safe,
                safe_limit=safe_limit,
                plan=plan,
                metrics=metrics,
                mode=mode,
                preview_limit=preview_limit,
                output_format=output_format,
            )
            result.update(exec_res)
            result["executed"] = True

        return result
