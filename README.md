# Q-Forge
### AI Query Planning, Safety & Performance Control Plane

Q-Forge is an MCP-ready control plane that turns natural-language requests into SQL through a structured query lifecycle: plan, validate, explain, execute (optional), and measure. It emphasizes safety gates, policy reasoning, and measurable performance metrics rather than opaque SQL generation.

---

## Background / Motivation

This project is a continuation of my work on AI infrastructure, where performance measurement, bottleneck analysis, and efficiency were core requirements. The same mindset applies to databases: queries are potentially expensive and risky operations, so they must be planned, validated, measured, and governed.

In production environments such as banks or enterprise data platforms, there is no room for unnecessary latency, and scripts must never block or degrade the system. Q-Forge exists to make NL-to-SQL safe, auditable, and performance-aware by default.

---

## What Makes It Different

- **Database-aware NL-to-SQL**: translation is guided by live schema introspection.
- **Explicit schema understanding**: tables, columns, foreign keys, and join paths are modeled and exposed as plans or diagrams.
- **Plan-first lifecycle**: every request produces a Query Plan JSON before any execution.
- **Policy-driven safety**: writes are blocked by default; rule checks decide what can execute.
- **Stage-level metrics**: schema fetch, LLM translation, planning/EXPLAIN, and execution timings are recorded.
- **Explain/preview modes**: safe modes return EXPLAIN output or bounded results before full execution.
- **Deterministic caching**: NL-to-SQL results are cached with a schema+query fingerprint.

---

## Core Query Lifecycle

1. **Plan**: build a structured Query Plan (JSON).
2. **Validate**: policy engine checks for safety and allowed operations.
3. **Explain**: produce EXPLAIN output and heuristic estimates by default.
4. **Execute (optional)**: only when explicitly requested by the client.
5. **Audit**: write decisions, metrics, and outcomes to the audit log.

---

## Architecture

```mermaid
flowchart TD
  A[Natural language request] --> B[Schema Introspection]
  B --> C[Query Plan JSON]
  C --> D[Safety/Policy Gate]
  D --> F[Explain Output + Estimates]
  F --> J{Client requests execution?}
  J -->|no| I[Metrics + Audit Log]
  J -->|yes| G[Execute (preview or full)]
  G --> I
```

Q-Forge follows Clean Architecture:
- **Interfaces (MCP tools)**: transport and tool definitions.
- **Application layer**: query lifecycle orchestration and modes.
- **Domain (ports)**: stable interfaces for adapters.
- **Infrastructure**: SQLAlchemy adapter, DB context, LLM provider, config, and logging.

---

## Safety Guarantees

- Read-only by default; writes require explicit approval.
- Bounded preview execution enforces LIMIT.
- Audit log records decisions, metrics, and outcomes.
- Policy engine returns reasons when a request is blocked.

---

## Non-Goals

- Not a BI or visualization tool.
- Not a chat UI.
- Not an autonomous system that performs writes without approval.

---

## Who It's For

Q-Forge is useful for teams that need controlled NL-to-SQL:
- **Banking/finance analytics** teams who need safe, audited query execution.
- **Operations/HR** teams who ask for employee and staffing reports in SQL.
- **Data/BI** users who want fast, safe exploration without direct DB access.

---

## MCP Tools

Core tools:
- `nl_to_sql`: translate NL to SQL (optionally include plan).
- `plan_query`: plan only, no execution (returns recommended SQL and estimates).
- `run_sql`: execute SQL with safety + modes.
- `ask_db`: NL -> SQL -> plan by default; executes only when requested.
- `run_sql_write` / `run_sql_write_approved`: write operations with explicit approval.
- `get_schema` / `get_erd` / `list_tables`: schema utilities.

Execution modes:
- `mode="explain"`: return plan and EXPLAIN only.
- `mode="preview"`: safe limited execution.
- `mode="execute"`: full execution (still policy-bounded).

---

## Tech & Build Principles

- **SQLAlchemy** as the primary DB adapter.
- **DbContext** for consistent access and lifecycle control.
- **Dependency Injection** across layers.
- **DTOs** for clean, safe data transfer.

---

## Quickstart

Create and activate a venv:
```bash
python -m venv venv
```
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

Install:
```bash
pip install -e .
```

Configure environment in `mcp_sql_agent/app/.env`:
```bash
DB_URL=sqlite:///mcp_sql_agent/app/demo.db
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

Run the MCP server (stdio transport):
```bash
python -m mcp_sql_agent.app.main
```

Example MCP client config (`mcp.toml`):
```toml
[mcp_servers.q_forge]
command = "C:\\path\\to\\Q-Forge\\venv\\Scripts\\python.exe"
args = ["-m", "mcp_sql_agent.app.main"]
cwd = "C:\\path\\to\\Q-Forge"
```

Example tool call (client-side):
```json
{
  "tool": "ask_db",
  "arguments": {
    "nl_query": "Top 5 customers by revenue last quarter"
  }
}
```

---

## Tests

```bash
pytest
```

Includes tests for policy enforcement, caching, audit logging, planning, and tool behavior.

---

## Roadmap (Near-Term)

- Expand safety policy with configurable allowlists and stricter SQL parsing.
- Add true query optimization hints (not just safe LIMIT and heuristics).
- Harden authentication/authorization for multi-tenant deployments.
- Improve observability with structured tracing and richer audit schemas.
