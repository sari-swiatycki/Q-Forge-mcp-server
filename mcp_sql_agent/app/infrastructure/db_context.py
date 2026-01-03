from pathlib import Path
import os
import time

from mcp_sql_agent.app.infrastructure.db.sqlalchemy_adapter import SQLAlchemyAdapter
from mcp_sql_agent.app.infrastructure.config import get_settings


class DbContext:
    def __init__(self, db_url: str):
        self._db_url = db_url
        self._adapter = SQLAlchemyAdapter(db_url)
        self._schema_cache: dict[str, tuple[dict, float]] = {}
        self._schema_cache_ttl_seconds = 60

    @property
    def db_url(self) -> str:
        return self._db_url

    def get_adapter(self, db_url: str | None = None) -> SQLAlchemyAdapter:
        if not db_url:
            return self._adapter
        return SQLAlchemyAdapter(db_url)

    def get_schema(self, db_url: str | None = None) -> dict:
        cache_key = self._schema_cache_key(db_url)
        cached = self._get_cached_schema(cache_key)
        if cached is not None:
            return cached
        schema = self.get_adapter(db_url).get_schema()
        self._set_cached_schema(cache_key, schema)
        return schema

    def list_tables(self, db_url: str | None = None) -> dict:
        schema = self.get_schema(db_url)
        return {"tables": list(schema.get("tables", {}).keys())}

    def set_db_url(self, db_url: str) -> dict:
        self._db_url = db_url
        self._adapter = SQLAlchemyAdapter(db_url)
        self._schema_cache.clear()
        return {"db_url": self._db_url}

    def db_debug(self) -> dict:
        db_path = Path(__file__).resolve().parents[1] / "demo.db"
        return {
            "cwd": os.getcwd(),
            "db_url": self._db_url,
            "db_path": str(db_path),
            "db_exists": db_path.exists(),
        }

    def _schema_cache_key(self, db_url: str | None) -> str:
        """Return the cache key for schema lookups."""
        return db_url or self._db_url

    def _get_cached_schema(self, cache_key: str) -> dict | None:
        """Return cached schema when fresh, otherwise None."""
        cached = self._schema_cache.get(cache_key)
        if cached is None:
            return None
        schema, ts = cached
        if time.time() - ts > self._schema_cache_ttl_seconds:
            self._schema_cache.pop(cache_key, None)
            return None
        return schema

    def _set_cached_schema(self, cache_key: str, schema: dict) -> None:
        """Store schema in cache with a timestamp."""
        self._schema_cache[cache_key] = (schema, time.time())


_DEFAULT_CONTEXT: DbContext | None = None


def get_default_context() -> DbContext:
    global _DEFAULT_CONTEXT
    if _DEFAULT_CONTEXT is None:
        settings = get_settings()
        _DEFAULT_CONTEXT = DbContext(settings.db_url)
    return _DEFAULT_CONTEXT


def set_default_context(context: DbContext) -> None:
    global _DEFAULT_CONTEXT
    _DEFAULT_CONTEXT = context


def get_adapter(db_url: str | None) -> SQLAlchemyAdapter:
    return get_default_context().get_adapter(db_url)


def get_schema(db_url: str | None = None) -> dict:
    return get_default_context().get_schema(db_url)


def list_tables(db_url: str | None = None) -> dict:
    return get_default_context().list_tables(db_url)


def set_db_url(db_url: str) -> dict:
    return get_default_context().set_db_url(db_url)


def db_debug() -> dict:
    return get_default_context().db_debug()
