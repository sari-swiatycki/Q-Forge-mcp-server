from mcp_sql_agent.app.application.sql_agent_service import SqlAgentService
from mcp_sql_agent.app.infrastructure.config import get_settings
from mcp_sql_agent.app.infrastructure.db_context import DbContext
from mcp_sql_agent.app.infrastructure.llm.translator import OpenAiTranslator


def build_sql_agent_service() -> SqlAgentService:
    # Composition root: wire infrastructure to application once.
    settings = get_settings()
    context = DbContext(settings.db_url)
    return SqlAgentService(
        context,
        lambda: OpenAiTranslator(settings.openai_api_key, settings.openai_model),
    )
