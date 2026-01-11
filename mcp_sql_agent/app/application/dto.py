from dataclasses import dataclass
from typing import Any


def _assert(condition: bool, message: str) -> None:
    """Raise ValueError with a message when condition is False."""
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class QueryPlanDto:
    """Typed representation of a query plan with risk and safety metadata."""
    explain: dict
    estimate_ms: float | None
    plan_rows: int | None
    total_cost: float | None
    risk_score: float
    risk_level: str | None
    risky_reasons: list[str]
    improvements: list[str]
    plan_json: dict
    safe_sql: str
    notes: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "QueryPlanDto":
        """Validate and build a QueryPlanDto from a plain dict."""
        _assert(isinstance(data.get("explain"), dict), "plan.explain must be a dict")
        _assert(isinstance(data.get("risk_score"), (int, float)), "plan.risk_score must be numeric")
        _assert(isinstance(data.get("risky_reasons"), list), "plan.risky_reasons must be a list")
        _assert(isinstance(data.get("improvements"), list), "plan.improvements must be a list")
        _assert(isinstance(data.get("plan_json"), dict), "plan.plan_json must be a dict")
        _assert(isinstance(data.get("safe_sql"), str), "plan.safe_sql must be a string")
        _assert(isinstance(data.get("notes"), list), "plan.notes must be a list")
        return cls(
            explain=data["explain"],
            estimate_ms=data.get("estimate_ms"),
            plan_rows=data.get("plan_rows"),
            total_cost=data.get("total_cost"),
            risk_score=float(data["risk_score"]),
            risk_level=data.get("risk_level"),
            risky_reasons=list(data["risky_reasons"]),
            improvements=list(data["improvements"]),
            plan_json=data["plan_json"],
            safe_sql=str(data["safe_sql"]),
            notes=list(data["notes"]),
        )

    def to_dict(self) -> dict:
        """Serialize the query plan to a JSON-friendly dict."""
        return {
            "explain": self.explain,
            "estimate_ms": self.estimate_ms,
            "plan_rows": self.plan_rows,
            "total_cost": self.total_cost,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risky_reasons": self.risky_reasons,
            "improvements": self.improvements,
            "plan_json": self.plan_json,
            "safe_sql": self.safe_sql,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SqlResultDto:
    """Typed representation of a SELECT result with plan metadata."""
    row_count: int
    rows: list[dict]
    executed_sql: str
    plan: QueryPlanDto
    table: str | None = None

    @classmethod
    def from_parts(
        cls, row_count: int, rows: list[dict], executed_sql: str, plan: dict, table: str | None = None
    ) -> "SqlResultDto":
        """Validate and build a SqlResultDto from raw parts."""
        _assert(isinstance(row_count, int), "row_count must be int")
        _assert(isinstance(rows, list), "rows must be list")
        _assert(isinstance(executed_sql, str), "executed_sql must be string")
        plan_dto = QueryPlanDto.from_dict(plan)
        return cls(row_count=row_count, rows=rows, executed_sql=executed_sql, plan=plan_dto, table=table)

    def to_dict(self) -> dict:
        """Serialize the SQL result to a JSON-friendly dict."""
        data: dict[str, Any] = {
            "row_count": self.row_count,
            "rows": self.rows,
            "executed_sql": self.executed_sql,
            "plan": self.plan.to_dict(),
        }
        if self.table is not None:
            data["table"] = self.table
        return data


@dataclass(frozen=True)
class SqlWriteResultDto:
    """Typed representation of a write result with affected row count."""
    row_count: int

    @classmethod
    def from_rowcount(cls, row_count: int) -> "SqlWriteResultDto":
        """Validate and build a SqlWriteResultDto from row count."""
        _assert(isinstance(row_count, int), "row_count must be int")
        return cls(row_count=row_count)

    def to_dict(self) -> dict:
        """Serialize the write result to a JSON-friendly dict."""
        return {"row_count": self.row_count}
