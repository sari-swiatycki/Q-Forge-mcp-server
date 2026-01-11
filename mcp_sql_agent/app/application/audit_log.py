import json
import os
from datetime import datetime, timezone
from pathlib import Path

import aiofiles


def _default_log_path() -> Path:
    """Return the default audit log location within the application root."""
    root = Path(__file__).resolve().parents[1]
    return root / "audit.log.jsonl"


async def write_event(event: dict) -> None:
    """Append a JSONL audit event to disk.

    Args:
        event: Event payload to write. Timestamp is injected automatically.
    Side Effects:
        Creates parent directories when missing and writes to the audit log.
    """
    path = Path(os.getenv("AUDIT_LOG_PATH", str(_default_log_path())))
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "a", encoding="utf-8") as handle:
        await handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
