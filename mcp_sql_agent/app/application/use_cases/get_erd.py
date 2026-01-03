from mcp_sql_agent.app.application.erd_rendering import build_erd_mermaid
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class GetErdUseCase:
    def __init__(self, adapter_provider: SqlAdapterProvider) -> None:
        self._adapter_provider = adapter_provider

    def execute(self, db_url: str | None = None) -> dict:
        schema = self._adapter_provider.get_schema(db_url)
        return {"erd": build_erd_mermaid(schema)}
