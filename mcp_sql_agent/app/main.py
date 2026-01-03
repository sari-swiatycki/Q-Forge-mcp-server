from mcp_sql_agent.app.infrastructure.config import get_settings
from mcp_sql_agent.app.infrastructure.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

from mcp_sql_agent.app.interfaces.mcp.mcp_server import mcp  # noqa: E402


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
