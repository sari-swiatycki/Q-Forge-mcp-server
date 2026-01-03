from typing import Any, Dict

from mcp_sql_agent.app.domain.ports import LlmTranslator


def _build_prompt(nl_query: str, schema: Dict[str, Any], dialect: str) -> str:
    return (
        "You are a SQL generator.\n"
        "Return ONLY the SQL query, no markdown, no explanation.\n"
        f"Dialect: {dialect}\n\n"
        "Schema:\n"
        f"{schema}\n\n"
        "User request:\n"
        f"{nl_query}\n"
    )

class OpenAiTranslator(LlmTranslator):
    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - handled as runtime guidance
            raise RuntimeError(
                "Missing dependency: install openai SDK (pip install openai)."
            ) from exc

        cleaned = api_key.strip()
        if not cleaned:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self._client = OpenAI(api_key=cleaned)
        self._model = model

    def translate(self, nl_query: str, schema: Dict[str, Any], dialect: str) -> str:
        prompt = _build_prompt(nl_query, schema, dialect)
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()
