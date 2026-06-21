# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run locally (recommended — spins up local Postgres + API):**
```bash
docker-compose up --build
```

**Run without Docker (point `POSTGRES_HOST` at a real RDS in `.env` first):**
```bash
uvicorn api.websocket_server:app --host 0.0.0.0 --port 8000 --reload
```

**Test with the WebSocket client:**
```bash
python tests/test_client.py "How many orders were placed yesterday?"
python tests/test_client.py "What does OTB's runbook say about incident response?"
python tests/test_client.py "What are the latest AI agent frameworks in 2026?"
python tests/test_client.py "DROP TABLE orders;"   # should be blocked by guardrail
```

**Seed / inspect local Postgres:**
```bash
python sql/seed_db.py
python sql/show_seed_data.py
```

**Verify dependency compatibility:**
```bash
pip check    # must show zero conflicts
```

## Architecture

### Request flow

An Angular client connects over WebSocket to `ws://.../ws/agent`. The server (`api/websocket_server.py`) builds an `AgentState`, calls `graph.ainvoke(state)`, and streams progress events back over the same connection while the graph executes.

### LangGraph state machine (`graph/`)

`graph/state.py` defines `AgentState` (a `TypedDict`) — the single object that flows through every node. Each node receives the full state and returns a partial dict to merge back.

`graph/workflow.py` wires all nodes into a `StateGraph`:

```
START → guardrail_input → orchestrator ──┬─→ knowledge ─┐
                       ↘ (blocked)        ├─→ sql ────────┤→ author → evaluator → END
                        └─→ blocked ──┐  └─→ research ───┘
                                      └─────────────────────────────↗
```

The compiled graph is built once at startup (`get_graph()`) and reused for every request.

### Orchestrator routing (`agents/orchestrator.py`)

Three-tier decision, in order:
1. **Org alias match** — if query mentions a name from `config/agents.yaml → organizations`, route to `knowledge`
2. **SQL keyword match** — if query contains keywords from `routing.sql_keywords`, route to `sql`
3. **LLM classify** — call Bedrock to classify as `knowledge | sql | research` (fallback: `research`)

### The three specialist agents

- **knowledge** (`agents/knowledge_agent.py`) — OpenSearch vector retrieval → LLM synthesis. Uses `tools/opensearch_tool.py`.
- **sql** (`agents/sql_agent.py`) — Three fixed steps: `frame_query` (LLM → SQL) → `verify_query` (allowlist + SELECT-only check) → `execute_query` (psycopg3, read-only transaction). Implemented in `tools/sql_tools.py`.
- **research** (`agents/research_agent.py`) — Google Custom Search → read top URLs → LLM synthesis. Uses `tools/search_tools.py`.

All three write their result to `state["agent_result"]` in the same normalized shape (`{agent, content, sources, raw}`).

### Author agent (`agents/author_agent.py`)

Every response — regardless of which specialist ran — flows through here. It polishes the draft with an LLM call and runs `mask_pii()` from `guardrails/guardrail.py` before the response reaches the client. This is the single output choke point.

### Configuration (`config/`)

All tuneable values live in `config/agents.yaml`. `config/settings.py` loads it once (cached via `lru_cache`) and resolves `${ENV_VAR}` placeholders from the environment. Every module imports `from config.settings import settings` — nothing reads `os.environ` or YAML directly.

Things commonly changed in `agents.yaml`:
- `organizations` — add org names / aliases the Knowledge Brain should recognise
- `routing.sql_keywords` — extend keyword list for SQL routing
- `guardrails.sql_injection.patterns` — input block patterns (regex)
- `guardrails.pii_masking.rules` — output redaction patterns
- `postgres.allowed_tables` — SQL agent table allowlist (security gate)
- `llm.model_id` — set via `BEDROCK_MODEL_ID` env var

### Guardrails (`guardrails/guardrail.py`)

Two pure functions, both pattern-driven from `agents.yaml`:
- **Input**: `run_input_guardrails(query)` — SQL injection patterns; blocks before any agent runs
- **Output**: `mask_pii(text)` — email/phone redaction; runs inside the Author agent

### Evaluator (`evaluation/evaluator.py`)

Final graph node. `capture_trace()` writes every run to:
1. **CloudWatch** — single-line JSON tagged `EVAL_TRACE` to stdout (ECS log driver picks it up)
2. **PostgreSQL** — `agent_traces` table (created automatically at startup via `ensure_table_exists()`)

### LLM factory (`tools/llm.py`)

`get_llm()` returns a cached `ChatBedrock` instance. Credential priority: explicit `BEDROCK_AWS_ACCESS_KEY_ID`/`BEDROCK_AWS_SECRET_ACCESS_KEY` → `BEDROCK_AWS_PROFILE` → default AWS chain.

### WebSocket protocol

Client sends: `{"session_id": "...", "query": "..."}`

Server streams: `agent_selected` → `agent_progress` (multiple) → `agent_complete` → `eval_captured` → `turn_complete`

## Dependency version safety

`langgraph`, `langchain-core`, and `langchain-aws` **must be upgraded together, never in isolation**. The pinned, verified-compatible set is in `requirements.txt`. Do not manually pin `langgraph-checkpoint`, `langgraph-prebuilt`, or `langgraph-sdk` — let `langgraph` resolve its own sub-dependencies.

## Required environment variables

```
BEDROCK_MODEL_ID          # e.g. anthropic.claude-3-5-sonnet-20241022-v2:0
OPENSEARCH_HOST           # OpenSearch domain endpoint
OPENSEARCH_INDEX_NAME     # RAG index name
POSTGRES_HOST / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD
GOOGLE_API_KEY            # Google Custom Search API key
GOOGLE_CSE_ID             # Programmable Search Engine ID
```

`docker-compose.yml` overrides the `POSTGRES_*` vars automatically for local runs.
