import hashlib
import json
import time


class QueryCache:
    """TTL-based in-memory cache for NL->SQL translations."""
    def __init__(self, ttl_seconds: int = 300) -> None:
        """Create a cache with a time-to-live in seconds."""
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        """Return cached value when fresh, otherwise None."""
        cached = self._store.get(key)
        if cached is None:
            return None
        value, ts = cached
        if time.time() - ts > self._ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str) -> None:
        """Store a value in the cache with the current timestamp."""
        self._store[key] = (value, time.time())


def build_cache_key(nl_query: str, schema: dict) -> str:
    """Build a deterministic cache key from the request and schema."""
    payload = {"nl_query": nl_query, "schema": schema}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
