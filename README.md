# Q-Forge
### AI Query Planning, Safety & Performance Control Plane

Q-Forge is an MCP-ready control plane that turns natural-language questions into **optimized SQL**, validates them for **safety**, and executes them with **performance guardrails**. This is less about hype and more about accuracy and speed: the system prioritizes the most correct and fastest queries.

This is not just "NL-to-SQL". It is a **full query lifecycle system**: plan, validate, explain, measure, and control.

---

## What Makes It Different

- **Speed-first design**: built to produce the fastest, most efficient queries possible.
- **Production-grade reliability**: audit logs and metrics for every request.
- **Tests for everything that matters**: policy, planning, caching, audit, MCP tools.
- **Clean Architecture**: strict separation of layers and easy extensibility.
- **Built for any DB**: consistent access via DbContext, DI, DTOs, and adapters.

---

## The Story Behind It

In a previous project I worked on AI infrastructure with a strong focus on performance. There it was GPU and inference. That experience made it clear this project will not be complete without serious performance focus. I spoke with several companies, including a bank, and the need was clear: the intelligence must know the VDB, know how to assemble SQL scripts for heavy tables on busy, bank-grade servers, and understand context and schema through diagrams. So I built a system that is pleasant and efficient, not only for SQL developers, but also for people who want to manage employee payroll in a simple way.

---

## Core Pipeline

1. **Plan**: build a structured Query Plan (JSON).
2. **Validate**: safety and policy checks.
3. **Estimate**: performance heuristics + optional EXPLAIN.
4. **Execute**: explicit, bounded execution.
5. **Audit**: log every decision and metric.

---

## Architecture

![Q-Forge Architecture](docs/architecture.svg)

Q-Forge follows **Clean Architecture**:

- **Interfaces (MCP tools)**: transport and tool definitions.
- **Application layer**: orchestration, modes, and safety gates.
- **Core engine**: planning, validation, explainability.
- **Infrastructure**: SQLAlchemy, LLM providers, audit logging.

It uses a **DbContext (VDBContext-style lifecycle)** for consistent access, cache awareness, and testability.

---

## Safety & Performance

Safety is first-class:
- Read-only by default.
- Writes require explicit approval.
- Automatic LIMIT enforcement.
- Join and risk thresholds with clear explanations.

Performance is built in:
- Planning, compile, and execution timing metrics.
- EXPLAIN-only mode.
- Bounded preview execution.

---

## Query Planning (Not Just SQL Generation)

Every request produces a **Query Plan JSON** before execution, including:
- intent
- tables + join paths
- filters + aggregations
- group_by / order_by / limit
- confidence score

This makes decisions **inspectable, debuggable, and auditable**.

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
- `mode="execute"`: full execution (still policy-bounded).

---

## Tech & Build Principles

- **SQLAlchemy** as the primary DB adapter.
- **DbContext Singleton** for consistent access and lifecycle control.
- **Dependency Injection** across layers.
- **DTOs** for clean, safe data transfer.

---

## Local Run

Clone first:
```bash
git clone <REPO_URL>
```

```bash
python -m venv venv
```
Activate:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

Install:
```bash
pip install -e .
```

Create `.env` and activate the virtual environment. Add a `CONNECTION_STRING` only if you need a DB connection.

For MCP integration, add this to your `.toml`:
```toml
model = "gpt-5.2-codex"
model_reasoning_effort = "medium"

[mcp_servers.mcp_sql_agent]
command = "C:\\Users\\user1\\Desktop\\mcp_sql_agent\\venv\\Scripts\\python.exe"
args = ["C:\\Users\\user1\\Desktop\\mcp_sql_agent\\mcp_sql_agent\\app\\main.py"]
cwd = "C:\\Users\\user1\\Desktop\\mcp_sql_agent\\mcp_sql_agent\\app"
[mcp_servers.github_mcp_server]
```

---

## Tests

```bash
pytest
```

Includes tests for policy enforcement, caching, audit logging, planning, and tool behavior.

There are tests in the project, and the system is far from perfect. The plan is to harden security, especially the painful prompt-security gap and the broader security surface of MCP servers.

---

## Non-Goals

- Not a BI or visualization tool.
- Not a chat UI.
- Not an autonomous agent executing without approval.

---

## Summary

Q-Forge is a **production-minded query control plane** built to deliver the **fastest, safest, and most efficient** database requests. It is engineered with Clean Architecture, full test coverage, and strict policy control for real-world use.