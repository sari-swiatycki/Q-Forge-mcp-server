from mcp_sql_agent.app.application.dto import SqlWriteResultDto
from mcp_sql_agent.app.application.safety_policy import evaluate_policy
from mcp_sql_agent.app.application.sql_validation import validate_sql_write
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class RunSqlWriteUseCase:
    """Execute write statements with validation and policy checks."""
    def __init__(self, adapter_provider: SqlAdapterProvider) -> None:
        """Create the use case with a DB adapter provider."""
        self._adapter_provider = adapter_provider

    async def execute(
        self, sql: str, db_url: str | None = None, allow_write: bool = False
    ) -> dict:
        """Validate and execute write SQL if policy allows it.

        Args:
            sql: INSERT/UPDATE/DELETE statement to execute.
            db_url: Optional override for the default DB URL.
            allow_write: When True, allow writes through policy checks.
        Returns:
            Dict containing affected row count and policy metadata.
        """
        ok, err = validate_sql_write(sql)
        if not ok:
            return {"error": err}

        policy = evaluate_policy(sql, {"risk_score": 0.0}, read_only=not allow_write)
        if not policy["allowed"]:
            return {"error": "Write blocked by safety policy.", "policy": policy}

        adapter = self._adapter_provider.get_adapter(db_url)
        row_count = await adapter.execute_write(sql)
        payload = SqlWriteResultDto.from_rowcount(row_count).to_dict()
        payload["policy"] = policy
        return payload
