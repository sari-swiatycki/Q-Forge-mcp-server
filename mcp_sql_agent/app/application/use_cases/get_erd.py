from mcp_sql_agent.app.application.erd_rendering import build_erd_mermaid
from mcp_sql_agent.app.domain.ports import SqlAdapterProvider


class GetErdUseCase:
    """Generate an ER diagram from database schema metadata."""
    def __init__(self, adapter_provider: SqlAdapterProvider) -> None:
        """Create the use case with a schema provider."""
        self._adapter_provider = adapter_provider

    async def execute(self, db_url: str | None = None) -> dict:
        """Return a Mermaid ER diagram for the requested database.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict containing Mermaid ER diagram text under "erd".
        """
        schema = await self._adapter_provider.get_schema(db_url)
        return {"erd": build_erd_mermaid(schema)}
