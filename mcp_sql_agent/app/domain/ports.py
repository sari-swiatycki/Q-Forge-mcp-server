from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SqlAdapter(Protocol):
    """Database adapter abstraction for querying and schema inspection."""
    async def query(self, sql: str) -> list[dict]:
        ...

    async def execute_write(self, sql: str) -> int:
        ...

    async def get_schema(self) -> dict:
        ...

    async def get_dialect(self) -> str:
        ...


@runtime_checkable
class LlmTranslator(Protocol):
    """Translator abstraction for NL -> SQL generation."""
    async def translate(self, nl_query: str, schema: dict, dialect: str) -> str:
        ...


@runtime_checkable
class SqlAdapterProvider(Protocol):
    """Provider abstraction for DB adapters and DB-level metadata."""
    def get_adapter(self, db_url: str | None = None) -> SqlAdapter:
        ...

    async def get_schema(self, db_url: str | None = None) -> dict:
        ...

    async def list_tables(self, db_url: str | None = None) -> dict:
        ...

    async def set_db_url(self, db_url: str) -> dict:
        ...

    async def db_debug(self) -> dict:
        ...
