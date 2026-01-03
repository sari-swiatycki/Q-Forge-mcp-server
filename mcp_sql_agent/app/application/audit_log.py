import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _default_log_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "audit.log.jsonl"


def write_event(event: dict) -> None:
    """Append a JSONL audit event to disk."""
    path = Path(os.getenv("AUDIT_LOG_PATH", str(_default_log_path())))
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
