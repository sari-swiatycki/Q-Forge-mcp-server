from pathlib import Path
import os
import time

from mcp_sql_agent.app.infrastructure.db.sqlalchemy_adapter import SQLAlchemyAdapter
from mcp_sql_agent.app.infrastructure.config import get_settings


class DbContext:
    """Owns DB adapter instances and schema cache for a default DB URL."""
    def __init__(self, db_url: str):
        """Initialize context with a default DB URL and adapter."""
        self._db_url = db_url
        self._adapter = SQLAlchemyAdapter(db_url)
        self._schema_cache: dict[str, tuple[dict, float]] = {}
        self._schema_cache_ttl_seconds = 60

    @property
    def db_url(self) -> str:
        """Return the current default DB URL."""
        return self._db_url

    def get_adapter(self, db_url: str | None = None) -> SQLAlchemyAdapter:
        """Return an adapter for the requested DB URL or the default.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            SQLAlchemyAdapter bound to the requested database.
        """
        if not db_url:
            return self._adapter
        return SQLAlchemyAdapter(db_url)

    async def get_schema(self, db_url: str | None = None) -> dict:
        """Return schema metadata, using cached results when available.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict with tables, columns, and relationship metadata.
        """
        cache_key = self._schema_cache_key(db_url)
        cached = self._get_cached_schema(cache_key)
        if cached is not None:
            return cached
        schema = await self.get_adapter(db_url).get_schema()
        self._set_cached_schema(cache_key, schema)
        return schema

    async def list_tables(self, db_url: str | None = None) -> dict:
        """Return a dict of table names for the requested database.

        Args:
            db_url: Optional override for the default DB URL.
        Returns:
            Dict with a "tables" list.
        """
        schema = await self.get_schema(db_url)
        return {"tables": list(schema.get("tables", {}).keys())}

    async def set_db_url(self, db_url: str) -> dict:
        """Update the default DB URL and reset cached schema.

        Args:
            db_url: New default DB URL for subsequent calls.
        Returns:
            Dict containing updated configuration metadata.
        Side Effects:
            Resets schema cache and replaces the default adapter.
        """
        self._db_url = db_url
        self._adapter = SQLAlchemyAdapter(db_url)
        self._schema_cache.clear()
        return {"db_url": self._db_url}

    async def db_debug(self) -> dict:
        """Return basic diagnostic metadata for the DB context."""
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
    """Return the singleton DbContext, creating it on first call.

    Side Effects:
        Initializes the default context using environment configuration.
    """
    global _DEFAULT_CONTEXT
    if _DEFAULT_CONTEXT is None:
        settings = get_settings()
        _DEFAULT_CONTEXT = DbContext(settings.db_url)
    return _DEFAULT_CONTEXT


def set_default_context(context: DbContext) -> None:
    """Set the singleton DbContext (used primarily for testing)."""
    global _DEFAULT_CONTEXT
    _DEFAULT_CONTEXT = context


def get_adapter(db_url: str | None) -> SQLAlchemyAdapter:
    """Return an adapter from the default context.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        SQLAlchemyAdapter bound to the requested database.
    """
    return get_default_context().get_adapter(db_url)


async def get_schema(db_url: str | None = None) -> dict:
    """Return schema metadata from the default context.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with tables, columns, and relationship metadata.
    """
    return await get_default_context().get_schema(db_url)


async def list_tables(db_url: str | None = None) -> dict:
    """Return table names from the default context.

    Args:
        db_url: Optional override for the default DB URL.
    Returns:
        Dict with a "tables" list.
    """
    return await get_default_context().list_tables(db_url)


async def set_db_url(db_url: str) -> dict:
    """Set the default DB URL for the current process.

    Args:
        db_url: New default DB URL for subsequent calls.
    Returns:
        Dict containing updated configuration metadata.
    """
    return await get_default_context().set_db_url(db_url)


async def db_debug() -> dict:
    """Return debug metadata from the default context."""
    return await get_default_context().db_debug()
