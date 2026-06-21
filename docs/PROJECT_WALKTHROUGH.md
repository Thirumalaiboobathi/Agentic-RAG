# Multi-Agent System — Project Walkthrough

A plain-English guide to how this project works, where execution begins, how to run it, and how to consume it from a client like Angular.

---

## 1. What this project does

A user sends a question over a WebSocket. An orchestrator decides which of four specialist agents should answer it, that agent does the work, and a final author agent polishes and returns the answer. Every step streams progress back to the client in real time, and every run is logged for evaluation.

The four agents:

- **Knowledge Brain** — answers questions about internal organization data by searching OpenSearch (the same vector index the RAG pipeline fills).
- **SQL Agent** — answers data questions (orders, products, counts) by writing SQL, verifying it is safe, then running it against PostgreSQL.
- **Research Agent** — answers anything else by searching Google and reading the resulting web pages.
- **Author Agent** — the single exit point. Every answer passes through here for final formatting and PII masking.

---

## 2. Where the flow starts

The entry point is `api/websocket_server.py`. This is the file you run. Everything else is imported by it.

When the server starts, it does two things once: it compiles the LangGraph (wiring all the agents together) and it makes sure the evaluation table exists in PostgreSQL. After that it waits for WebSocket connections on `/ws/agent`.

```
api/websocket_server.py          ← you run THIS
        │ on startup: compile graph + ensure eval table
        │ on each client message:
        ▼
graph/workflow.py  (the compiled graph)
        │ runs node by node:
        ▼
  guardrail_input → orchestrator → [one agent] → author → evaluator
```

The graph itself is defined in `graph/workflow.py`. That file is the map: it says "start at the guardrail, then go to the orchestrator, then branch to whichever agent the orchestrator picked, then always finish through the author and the evaluator."

---

## 3. The journey of one question

Here is what happens, in order, when a user asks "How many orders were placed yesterday?"

1. **Client sends the question** over the WebSocket as JSON: `{"session_id": "...", "query": "How many orders yesterday?"}`. This arrives in `websocket_server.py`.

2. **Guardrail check** (`guardrails/guardrail.py`). The raw question is scanned for SQL-injection patterns. If it looks like an attack, the request is blocked here and never reaches an agent. A normal question passes straight through.

3. **Orchestrator decides the route** (`agents/orchestrator.py`). It checks: does the question mention a known organization? Does it contain data-question keywords like "how many" or "orders"? If the simple rules do not give a clear answer, it asks the LLM to classify. For our example, "how many orders" matches the SQL keywords, so it routes to the SQL Agent. The client receives an `agent_selected` event here.

4. **The chosen agent does the work** (`agents/sql_agent.py` in this case). The SQL Agent runs its three steps, emitting a progress event before each one: it frames the SQL with one LLM call, verifies the SQL is safe with a tool call, then executes it against PostgreSQL with another tool call. Finally it turns the rows into a sentence.

5. **Author Agent finalizes** (`agents/author_agent.py`). It polishes the wording, masks any emails or phone numbers, attaches sources, and emits the `agent_complete` event containing the final response.

6. **Evaluator logs the run** (`evaluation/evaluator.py`). The whole trace — the question, which agent ran, the response, timing, any guardrail flags — is written to PostgreSQL and printed as a JSON line to CloudWatch. The client receives an `eval_captured` event.

7. **Server sends `turn_complete`** so the client knows the turn is finished and it can re-enable the input box.

---

## 4. How to run it locally

The fastest path uses Docker Compose, which starts a local PostgreSQL (pre-loaded with sample orders and products) alongside the API. Note that OpenSearch, Bedrock, and Google Search always talk to the real services, so you need valid AWS credentials and a Google API key even for local runs.

### Step 1 — Install and configure

```
cd multi_agent
cp .env.example .env
```

Edit `.env` and fill in `OPENSEARCH_HOST`, `GOOGLE_API_KEY`, and `GOOGLE_CSE_ID`. The PostgreSQL values are handled automatically by Docker Compose for local runs.

### Step 2 — Add your organizations

Open `config/agents.yaml` and list the org names the Knowledge Brain should recognize. This is the only file you edit to change business behavior.

```yaml
organizations:
  - name: "OTB"
    aliases: ["otb", "on the beach"]
```

### Step 3 — Start everything

```
docker-compose up --build
```

When you see the API report that the graph is compiled and the eval table is ready, it is listening on port 8000.

### Step 4 — Ask it questions

In a second terminal, use the included test client. It connects to the WebSocket, sends your question, and prints every progress event as it arrives.

```
python tests/test_client.py "How many orders were placed yesterday?"
python tests/test_client.py "What does OTB's runbook say about incidents?"
python tests/test_client.py "What are the newest AI agent frameworks in 2026?"
python tests/test_client.py "DROP TABLE orders;"
```

The first routes to SQL, the second to Knowledge Brain, the third to Research, and the last is blocked by the guardrail. Watching all four is the quickest way to confirm the whole system works.

### Running without Docker

If you would rather run the Python directly and point at your real RDS, set `POSTGRES_HOST` in `.env` to your RDS endpoint and run:

```
uvicorn api.websocket_server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. How to consume it from a client

The contract is a WebSocket at `/ws/agent`. A client opens the connection, sends one JSON message per question, and reads a stream of JSON events back.

### What the client sends

```json
{ "session_id": "user-123", "query": "How many orders yesterday?" }
```

### What the client receives (in order)

```json
{ "event": "agent_selected", "agent": "sql",    "message": "Routing to SQL Agent" }
{ "event": "agent_progress", "agent": "sql",    "message": "Framing SQL query..." }
{ "event": "agent_progress", "agent": "sql",    "message": "Verifying query safety..." }
{ "event": "agent_progress", "agent": "sql",    "message": "Executing query..." }
{ "event": "agent_complete", "agent": "author", "data": { "response": "..." } }
{ "event": "eval_captured",  "message": "...", "data": { "trace_id": "..." } }
{ "event": "turn_complete",  "trace_id": "..." }
```

### Angular example

```typescript
const ws = new WebSocket('wss://your-alb-dns/ws/agent');

ws.onopen = () => {
  ws.send(JSON.stringify({ session_id: 'user-123', query: userText }));
};

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  switch (msg.event) {
    case 'agent_selected':
      // show which agent picked up the question
      break;
    case 'agent_progress':
      // update a status line / spinner with msg.message
      break;
    case 'agent_complete':
      // render the final answer: msg.data.response
      break;
    case 'turn_complete':
      // re-enable the input box for the next question
      break;
    case 'guardrail_blocked':
    case 'error':
      // show the message to the user
      break;
  }
};
```

The progress events are what make the UI feel live — the user sees "Framing SQL query... Verifying... Executing..." instead of staring at a blank spinner.

---

## 6. How the pieces map to files

| Concern | File | Role |
|---------|------|------|
| Entry point | `api/websocket_server.py` | Run this; handles WebSocket, runs the graph |
| Graph wiring | `graph/workflow.py` | Defines node order and branching |
| Shared state | `graph/state.py` | The data object passed between nodes |
| Routing | `agents/orchestrator.py` | Picks the agent |
| Internal data | `agents/knowledge_agent.py` | OpenSearch retrieval |
| Data questions | `agents/sql_agent.py` | Frame → verify → execute |
| Web questions | `agents/research_agent.py` | Search → read URLs → synthesize |
| Output | `agents/author_agent.py` | Format + PII mask, single exit |
| Safety | `guardrails/guardrail.py` | SQL-injection block + PII mask |
| Logging | `evaluation/evaluator.py` | Trace to PostgreSQL + CloudWatch |
| Config | `config/agents.yaml` | Orgs, model, guardrails, routing — edit this |
| Settings loader | `config/settings.py` | Reads YAML + environment variables |
| Shared LLM | `tools/llm.py` | One Bedrock client for all agents |
| Tools | `tools/sql_tools.py`, `tools/search_tools.py`, `tools/opensearch_tool.py` | The work each agent delegates to |

The mental model: `agents.yaml` holds everything that changes between businesses, `websocket_server.py` is the front door, `workflow.py` is the routing map, the `agents/` folder holds the workers, and the `tools/` folder holds what those workers use.

---

## 7. Where to look when something goes wrong

- **A question routes to the wrong agent** — check the routing keywords and organization aliases in `config/agents.yaml`, then the logic in `agents/orchestrator.py`.
- **SQL Agent returns an error** — the verify step may be rejecting the query. Check the allowed tables list in `agents.yaml` and the verification rules in `tools/sql_tools.py`.
- **No progress events reach the client** — confirm the WebSocket stayed open. On ECS this usually means the ALB idle timeout is too low; raise it well above 60 seconds.
- **Nothing logged for evaluation** — confirm PostgreSQL is reachable and look for the `EVAL_TRACE` JSON lines in CloudWatch, which work even if the database write fails.

---

## 8. Quick start summary

```
cp .env.example .env          # fill in OpenSearch + Google keys
# edit config/agents.yaml      # add your organizations
docker-compose up --build      # starts local Postgres + API
python tests/test_client.py "How many orders yesterday?"   # try it
```

Then point your Angular app at `ws://localhost:8000/ws/agent` locally, or `wss://your-alb-dns/ws/agent` once deployed to ECS.
