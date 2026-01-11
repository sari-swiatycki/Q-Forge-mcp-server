from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class SQLAlchemyAdapter:
    """SQLAlchemy-backed implementation of the SqlAdapter protocol.

    Uses an async engine and normalized async driver URLs.
    """
    def __init__(self, connection_string: str):
        """Create an async engine for the given connection string.

        Args:
            connection_string: SQLAlchemy URL, sync or async.
        Side Effects:
            Initializes an async engine and connection pool.
        """
        normalized = _normalize_db_url(connection_string)
        self.engine: AsyncEngine = create_async_engine(normalized, future=True)

    async def query(self, sql: str) -> list[dict]:
        """Execute a read query and return rows as dicts.

        Args:
            sql: SQL to execute (typically SELECT/CTE).
        Returns:
            List of row dicts.
        """
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql))
            rows = result.mappings().all()
            return [dict(r) for r in rows]

    async def execute_write(self, sql: str) -> int:
        """Execute a write query and return affected row count.

        Args:
            sql: INSERT/UPDATE/DELETE statement.
        Returns:
            Number of affected rows.
        """
        async with self.engine.begin() as conn:
            result = await conn.execute(text(sql))
            return int(result.rowcount or 0)

    async def get_schema(self) -> dict:
        """Introspect database schema, including foreign keys.

        Returns:
            Dict with tables, columns, and foreign key metadata.
        """
        def _run(sync_conn) -> dict:
            insp = inspect(sync_conn)
            schema = {}
            foreign_keys = []
            for table in insp.get_table_names():
                cols = insp.get_columns(table)
                schema[table] = [
                    {"name": c["name"], "type": str(c["type"])} for c in cols
                ]
                for fk in insp.get_foreign_keys(table):
                    if not fk.get("referred_table") or not fk.get(
                        "constrained_columns"
                    ):
                        continue
                    foreign_keys.append(
                        {
                            "table": table,
                            "columns": fk.get("constrained_columns", []),
                            "referred_table": fk.get("referred_table"),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                    )
            return {"tables": schema, "foreign_keys": foreign_keys}

        async with self.engine.connect() as conn:
            payload = await conn.run_sync(_run)
        payload["dialect"] = self.engine.dialect.name
        return payload

    async def get_dialect(self) -> str:
        """Return the SQL dialect name used by the engine."""
        return self.engine.dialect.name


def _normalize_db_url(db_url: str) -> str:
    """Map sync SQLAlchemy URLs to async driver URLs when needed.

    Args:
        db_url: SQLAlchemy URL from config.
    Returns:
        Async-driver URL when a known mapping exists.
    """
    url = make_url(db_url)
    driver = url.drivername
    if "+" in driver:
        return db_url
    if driver == "sqlite":
        return str(url.set(drivername="sqlite+aiosqlite"))
    if driver in {"postgresql", "postgres"}:
        return str(url.set(drivername="postgresql+psycopg"))
    return db_url



