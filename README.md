# Q-Forge  
### AI Query Planning, Safety & Performance Control Plane

---

## 🚀 Overview

**Q-Forge** is an AI-powered query planning and execution control engine that safely transforms natural-language requests into **optimized, explainable, and performance-aware SQL queries**.

Unlike basic NL→SQL generators, Q-Forge is designed as a **database control plane** — enforcing safety policies, measuring performance, and providing full explainability before any query is executed.

The project reflects a strong **AI infrastructure mindset**, focusing on:
- performance analysis
- execution safety
- system boundaries
- clean, extensible architecture

---

## 🎯 Problem Statement

LLMs can generate SQL quickly — but in real systems this introduces serious risks:

- Unsafe write operations  
- Unbounded queries  
- Performance regressions  
- Lack of visibility into query cost  
- No explainability or auditability  

Most existing solutions optimize for **generation**, not for **production usage**.

---

## 💡 Solution

Q-Forge treats every query as a **controlled system operation**, not just text generation.

Each request goes through a structured pipeline:

1. Query planning (structured, deterministic)  
2. Safety & policy validation  
3. Performance estimation & instrumentation  
4. Explain / preview / export modes  
5. Audited execution (optional)  

This makes Q-Forge suitable for **real systems**, not demos.

---

## 🧠 Architectural Philosophy

### Clean Architecture by Design

Q-Forge is built using **Clean Architecture principles**, with strict separation of concerns:

```
Interfaces / MCP Layer
│
├── Application / Orchestration
│   - Query lifecycle
│   - Policy enforcement
│   - Mode handling
│
├── Core Engine
│   - Query planning
│   - Safety rules
│   - Performance heuristics
│   - Explainability
│
└── Infrastructure
    - SQLAlchemy adapters
    - Caching
    - Audit logging
```

The **core engine is LLM-agnostic, DB-agnostic, and interface-agnostic**.

---

## ⚙️ Database Independence

Q-Forge supports **any SQL database supported by SQLAlchemy**, including:

- PostgreSQL  
- MySQL  
- SQLite  
- SQL Server  

This is achieved through:
- a unified `DbContext`
- adapter-based execution
- schema introspection abstraction

No database-specific logic exists in the core engine.

---

## 🛡️ Safety as a First-Class Concern

Before execution, every query is validated by a **Policy Engine**:

- Read-only by default  
- Write operations blocked unless explicitly approved  
- Automatic LIMIT enforcement  
- Join count and complexity thresholds  
- High-risk query detection  

Unsafe queries are **blocked with a clear explanation**, not silently modified.

---

## ⚡ Performance Awareness

Q-Forge was designed with a strong **AI infrastructure & performance mindset**.

Each request includes detailed metrics:
- schema introspection time  
- LLM planning time  
- SQL compilation time  
- execution time  
- rows returned  
- cache hits  

The system also provides:
- heuristic cost estimation  
- EXPLAIN-only mode  
- bounded preview execution  

---

## 🧩 Query Planning (Not Just SQL Generation)

Every request produces a **Query Plan JSON** before SQL is executed.

The plan includes:
- intent  
- tables  
- joins  
- join paths (via foreign-key graph)  
- filters  
- aggregations  
- group_by / order_by  
- limit  
- confidence score  

This makes every decision **inspectable, debuggable, and auditable**.

---

## 🔍 Explain / Preview / Export Modes

- `mode="explain"` – return plan only, no execution  
- `mode="preview"` – bounded execution with LIMIT  
- `output_format="csv"` – safe data export  

Execution is always explicit and controlled.

---

## 🧾 Audit & Observability

Every request is written to an **audit log**:
- natural language query  
- generated SQL  
- policy decision  
- execution metrics  
- lifecycle state  

---

## 🧱 Design Patterns Used

- Clean Architecture  
- Adapter pattern (DB abstraction)  
- Singleton-style DbContext lifecycle  
- Policy engine pattern  
- Explicit lifecycle states  

---

## 🛠️ Technology Stack

- Python  
- SQLAlchemy  
- MCP (Model Context Protocol)  
- LLM-based reasoning (pluggable)  

---

## ▶️ Running the Project

### 1. Clone
```bash
git clone https://github.com/your-org/q-forge
cd q-forge
```

### 2. Setup environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure database
Edit the connection string in:
```
config/database.py
```

### 4. Run MCP server
```bash
python main.py
```

---

## 🚫 Non-Goals

- Not a BI or visualization tool  
- Not a chat interface  
- Not an autonomous agent executing without approval  

---

## 🏁 Summary

Q-Forge demonstrates how AI can be integrated into database systems **responsibly** — with safety, performance, and explainability as core principles.

It is not a demo.  
It is a **foundation for production-grade AI-assisted data access**.
