# MCP SQL Agent

Plan-first, risk-aware MCP server that accepts natural language requests,
translates them into SQL, and can safely execute reads or controlled writes
(insert/update/delete). It focuses on performance, speed, and safety so queries
do not stall the database, and it serves both developers and non-technical
users who want convenient access to data.
  
## Why this exists

In my last role, I worked on AI infrastructure performance, measuring and
improving throughput and latency. It is not the same domain as SQL systems, but
it made the importance of performance crystal clear. That mindset shaped this
project: not just a tool that knows a database and writes queries, but a system
that understands performance and protects databases from costly workloads. Every
query is planned, scored, and constrained before it executes.

## What it delivers

- Natural language to SQL translation with schema grounding
- Plan-only mode: get SQL + EXPLAIN without executing
- Structured query plan JSON (intent, tables, joins, filters, confidence)
- Safety gate that blocks risky queries before execution
- Performance metrics on every response
- Safe execution with enforced limits and risk blocking
- Controlled writes (INSERT/UPDATE/DELETE) with strict validation
- ERD generation to understand table relationships quickly
- Fast DB onboarding for teams and SQL developers

## Performance and safety model

- EXPLAIN-first planning with cost and row estimates when supported
- Risk heuristics for full scans, large joins, ORDER BY without LIMIT, SELECT *
- Automatic safe LIMIT (default: 1000) when a query is unbounded
- Query blocking when risk score is high (default threshold: 0.7)
- Index suggestions based on WHERE/JOIN/ORDER BY patterns
- Schema caching (TTL: 60s) to avoid repeated introspection
- Audit log for every query decision (JSONL)

## Architecture

Dependency rule: application logic never depends on infrastructure. Adapters
point inward through ports.

![Architecture](docs/architecture.svg)

Patterns used:
- Clean Architecture (Ports and Adapters)
- Use Case orchestration for workflows
- Singleton-style service wiring with dependency injection
- DbContext as a bounded access layer
- DTOs for validated, explicit responses

## Quick start

1) Create `mcp_sql_agent/app/.env` from the example and set your values.
2) Install Python dependencies (OpenAI SDK, SQLAlchemy, and a DB driver).
3) Run the MCP server:

```bash
cd mcp_sql_agent
python app/main.py
```

## Configuration

`mcp_sql_agent/app/.env`:

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
DB_URL=postgresql+psycopg://user:password@localhost:5432/mcp_db
```

## How to use

Plan-only SQL (no execution):
```json
{"tool":"plan_query","nl_query":"Show active users by signup date","safe_limit":500}
```

Safe read:
```json
{"tool":"run_sql","sql":"SELECT id, name FROM users ORDER BY id","safe":true,"mode":"preview"}
```

Controlled write:
```json
{"tool":"run_sql_write_approved","sql":"UPDATE users SET name='Dana' WHERE id=2"}
```

ERD relationships:
```json
{"tool":"get_erd"}
```

## MCP tools

- `ping()`
- `get_schema(db_url=None)`
- `list_tables(db_url=None)`
- `get_erd(db_url=None)`
- `nl_to_sql(nl_query, db_url=None)`
- `plan_query(nl_query, db_url=None, safe_limit=1000)`
- `run_sql(sql, format_table=False, db_url=None, safe=True, safe_limit=1000, mode="execute", preview_limit=50, output_format="json")`
- `run_sql_write(sql, db_url=None)`
- `run_sql_write_approved(sql, db_url=None)`
- `explain_sql(sql, db_url=None, safe_limit=1000)`
- `ask_db(nl_query, execute=True, format_table=False, db_url=None, safe=True, safe_limit=1000, mode="execute", preview_limit=50, output_format="json")`
- `set_db_url(db_url)`
- `db_debug()`

## Code structure

- `mcp_sql_agent/app/interfaces`: MCP tools and transport boundary
- `mcp_sql_agent/app/application`: use cases and orchestration logic
- `mcp_sql_agent/app/domain`: ports and core policies
- `mcp_sql_agent/app/infrastructure`: DB and LLM adapters

## MCP client example (TOML)

Use any MCP-capable client. Example configuration (adjust to your client):

```toml
[mcp.servers.sql]
command = "python"
args = ["mcp_sql_agent/app/main.py"]
transport = "stdio"
```

## Notes

- Store secrets locally and never commit `.env`.
- `run_sql_write` is intentionally strict; validate inputs before use.
