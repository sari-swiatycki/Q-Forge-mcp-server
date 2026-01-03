import time

from mcp_sql_agent.app.application.dto import SqlResultDto
from mcp_sql_agent.app.application.sql_formatting import format_csv, format_table
from mcp_sql_agent.app.application.sql_planning import build_query_plan
from mcp_sql_agent.app.application.sql_validation import apply_limit, validate_sql_select
from mcp_sql_agent.app.application.safety_policy import evaluate_policy
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class RunSqlUseCase:
    def __init__(self, adapter_provider: SqlAdapterProvider) -> None:
        self._adapter_provider = adapter_provider

    def execute(
        self,
        sql: str,
        format_table_result: bool = False,
        table_style: str = "simple",
        db_url: str | None = None,
        safe: bool = True,
        safe_limit: int = 1000,
        plan: dict | None = None,
        mode: str = "execute",
        preview_limit: int = 50,
        output_format: str = "json",
        metrics: dict | None = None,
    ) -> dict:
        ok, err = validate_sql_select(sql)
        if not ok:
            return {"error": err}

        adapter = self._adapter_provider.get_adapter(db_url)
        if plan is None:
            plan_start = time.perf_counter()
            active_plan = build_query_plan(sql, adapter, safe_limit=safe_limit)
            if metrics is not None:
                metrics["compile_sql_ms"] = round(
                    (time.perf_counter() - plan_start) * 1000, 2
                )
        else:
            active_plan = plan
        policy = evaluate_policy(sql, active_plan, read_only=True)
        if safe and not policy["allowed"]:
            return {
                "error": "Query blocked by safety policy.",
                "plan": active_plan,
                "policy": policy,
            }

        exec_sql = active_plan["safe_sql"] if safe else sql
        if mode == "preview":
            exec_sql, _ = apply_limit(exec_sql, preview_limit)
        if mode == "explain":
            return {"plan": active_plan, "policy": policy, "metrics": metrics or {}}

        exec_start = time.perf_counter()
        rows = adapter.query(exec_sql)
        db_exec_ms = round((time.perf_counter() - exec_start) * 1000, 2)
        if metrics is not None:
            metrics["db_exec_ms"] = db_exec_ms
            metrics["rows_returned"] = len(rows)
        table = format_table(rows, style=table_style) if format_table_result else None
        csv_data = format_csv(rows) if output_format == "csv" else None
        dto = SqlResultDto.from_parts(
            row_count=len(rows),
            rows=rows,
            executed_sql=exec_sql,
            plan=active_plan,
            table=table,
        )
        payload = dto.to_dict()
        if csv_data is not None:
            payload["csv"] = csv_data
        if metrics is not None:
            payload["metrics"] = metrics
        payload["policy"] = policy
        return payload
