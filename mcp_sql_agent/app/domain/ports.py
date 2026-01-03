from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SqlAdapter(Protocol):
    def query(self, sql: str) -> list[dict]:
        ...

    def execute_write(self, sql: str) -> int:
        ...

    def get_schema(self) -> dict:
        ...

    def get_dialect(self) -> str:
        ...


@runtime_checkable
class LlmTranslator(Protocol):
    def translate(self, nl_query: str, schema: dict, dialect: str) -> str:
        ...


@runtime_checkable
class SqlAdapterProvider(Protocol):
    def get_adapter(self, db_url: str | None = None) -> SqlAdapter:
        ...

    def get_schema(self, db_url: str | None = None) -> dict:
        ...

    def list_tables(self, db_url: str | None = None) -> dict:
        ...

    def set_db_url(self, db_url: str) -> dict:
        ...

    def db_debug(self) -> dict:
        ...
