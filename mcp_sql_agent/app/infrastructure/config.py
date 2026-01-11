from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """Immutable configuration loaded from env vars and .env overrides."""
    db_url: str
    openai_api_key: str
    openai_model: str
    log_level: str


_SETTINGS: Settings | None = None


def load_env(env_path: Path) -> None:
    """Load environment variables from a .env file without overriding existing ones.

    Args:
        env_path: Path to the .env file to read.
    Side Effects:
        Populates os.environ for keys not already set in the process.
    """
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Do not override process env vars to keep runtime config explicit.
        if key and key not in os.environ:
            os.environ[key] = value


def get_settings() -> Settings:
    """Return cached settings, loading from .env and env vars on first call.

    Returns:
        Settings object with DB/LLM configuration and log level.
    Side Effects:
        Reads .env and environment variables on first call.
    """
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_env(env_path)

    db_path = Path(__file__).resolve().parents[1] / "demo.db"
    db_url = os.getenv("DB_URL", f"sqlite:///{db_path}")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    _SETTINGS = Settings(
        db_url=db_url,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        log_level=log_level,
    )
    return _SETTINGS
