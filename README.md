# Q-Forge
### AI Query Planning, Safety & Performance Control Plane

Q-Forge is an MCP-ready control plane that turns natural-language questions about your database into **optimized SQL**, validates them for **safety**, and (optionally) executes them with **performance guardrails**.

It is not just a "NL-to-SQL" generator. It is a **query lifecycle system** that plans, validates, explains, and measures every request before execution.

---

## What It Does

- Accepts natural-language questions about your DB (or direct SQL).
- Translates to SQL with a deterministic plan step first.
- Enforces safety policies (read-only by default).
- Adds performance safeguards (limits, complexity thresholds, EXPLAIN mode).
- Emits audit logs and execution metrics for every request.

---

## Why It Exists (AI Infrastructure Mindset)

The project was inspired by real AI infrastructure work: deploying models, measuring performance, and hardening systems in production. That experience made one point obvious: **without safety and speed, nothing ships**.

Q-Forge applies that mindset to data access:
- Not about GPU inference, but about **query speed, safety, and visibility**.
- Built to measure, explain, and control queries before they touch production data.
- Focused on reliability and operational clarity, not flashy demos.

---

## Core Pipeline

1. **Plan**: Build a structured query plan (JSON).
2. **Validate**: Safety/policy checks (read-only by default).
3. **Estimate**: Performance heuristics + optional EXPLAIN.
4. **Execute**: Explicit, bounded execution.
5. **Audit**: Log every decision and metric.

---

## Architecture

![Q-Forge Architecture](docs/architecture.svg)

Q-Forge follows **Clean Architecture** with strict separation of concerns:

- **Interfaces (MCP tools)**: transport and tool definitions.
- **Application layer**: orchestration, mode handling, safety gates.
- **Core engine**: planning, validation, explainability.
- **Infrastructure**: adapters for SQLAlchemy, LLM providers, audit logging.

It uses a **DbContext (VDBContext-style lifecycle)** to keep database access consistent, cache-aware, and easy to test.

---

## Safety & Performance

Safety is a first-class feature:
- Read-only by default.
- Write queries require explicit approval.
- Automatic LIMIT enforcement.
- Join complexity thresholds.
- High-risk query detection with clear explanations.

Performance awareness is baked in:
- Planning time, compile time, and execution time metrics.
- Optional EXPLAIN-only mode.
- Bounded preview execution.

---

## Query Planning (Not Just SQL Generation)

Every request produces a **Query Plan JSON** before execution, including:
- intent
- tables + join paths
- filters + aggregations
- group_by / order_by / limit
- confidence score

This makes query decisions **inspectable, debuggable, and auditable**.

---

## MCP Tools (What You Can Call)

Core tools:
- `nl_to_sql`: translate NL to SQL (optionally include plan).
- `plan_query`: plan only, no execution.
- `run_sql`: execute SQL with safety + modes.
- `ask_db`: NL -> SQL -> (optional) execute in one call.
- `run_sql_write` / `run_sql_write_approved`: write operations with explicit approval.
- `get_schema` / `get_erd` / `list_tables`: schema utilities.

Execution modes:
- `mode="explain"`: return plan and EXPLAIN only.
- `mode="preview"`: safe limited execution.
- `mode="execute"`: full execution (still bounded by policy).

---

## Setup

### 1) Environment
```bash
python -m venv venv
```
Activate:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

Install dependencies:
```bash
pip install -e .
```

### 2) Configure `.env`
Create `mcp_sql_agent/app/.env`:
```bash
DB_URL=sqlite:///path/to/your.db
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

### 3) Run MCP Server
```bash
python -m mcp_sql_agent.app.main
```

---

## Tests

```bash
pytest
```

Includes tests for policy enforcement, caching, audit logging, planning, and tool behavior.

---

## Non-Goals

- Not a BI or visualization tool.
- Not a chat UI.
- Not an autonomous agent executing without approval.

---

## Summary

Q-Forge is a **production-minded query control plane**. It emphasizes **performance, safety, and explainability** across the entire query lifecycle, with Clean Architecture and test coverage to keep the system reliable as it grows.
