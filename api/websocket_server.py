"""
api/websocket_server.py
-----------------------
FastAPI app exposing a WebSocket endpoint. The Angular client connects here,
sends a query, and receives a stream of progress events ending in the final
response.

WebSocket protocol:

  Client → Server:
    { "session_id": "abc", "query": "How many orders yesterday?" }

  Server → Client (multiple events):
    { "event": "agent_selected", "agent": "sql", "message": "..." }
    { "event": "agent_progress", "agent": "sql", "message": "Framing SQL query..." }
    ... more progress ...
    { "event": "agent_complete", "agent": "author", "data": { "response": "..." } }
    { "event": "eval_captured",  "trace_id": "...", "message": "..." }

Run locally:
    uvicorn api.websocket_server:app --host 0.0.0.0 --port 8000 --reload

The /health endpoint is for ECS/ALB target group health checks.
"""

import json
import logging
import sys
from pathlib import Path

# Allow running directly: python api/websocket_server.py
# Without this, `from graph.workflow import ...` fails because Python adds
# api/ to sys.path instead of the project root (multi-agent/).
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from graph.workflow import get_graph
from graph.state import new_state
from evaluation.evaluator import ensure_table_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,   # ECS → CloudWatch
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Compile the graph and ensure the eval table exists at startup."""
    get_graph()                  # warm the compiled graph
    ensure_table_exists()        # create agent_traces table if needed
    logger.info("Multi-agent server started — graph compiled, eval table ready")
    yield


app = FastAPI(
    title="Multi-Agent LangGraph API",
    description="Orchestrator + Knowledge/SQL/Research/Author agents over WebSocket",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Health check for ALB / ECS target group."""
    return {"status": "healthy", "service": "multi-agent-api"}


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    Main WebSocket endpoint. One connection handles one or more queries.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            # ── Receive a query from the client ───────────────────────────────
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "event": "error",
                    "message": "Invalid JSON. Send {\"session_id\": \"..\", \"query\": \"..\"}",
                })
                continue

            session_id = payload.get("session_id", "anonymous")
            query = payload.get("query", "").strip()

            if not query:
                await websocket.send_json({
                    "event": "error",
                    "message": "Empty query.",
                })
                continue

            logger.info(f"[{session_id}] Query received: {query[:80]}")

            # ── Progress emitter — pushes events back over this WebSocket ─────
            async def emit(event_type: str, agent: str, message: str, data: dict = None):
                msg = {"event": event_type, "agent": agent, "message": message}
                if data is not None:
                    msg["data"] = data
                await websocket.send_json(msg)

            # ── Run the graph ─────────────────────────────────────────────────
            state = new_state(session_id=session_id, user_query=query, emit=emit)
            graph = get_graph()

            try:
                final_state = await graph.ainvoke(state)
            except Exception as e:
                logger.exception(f"[{session_id}] Graph execution failed: {e}")
                await websocket.send_json({
                    "event": "error",
                    "message": f"Internal error: {e}",
                })
                continue

            # agent_complete + eval_captured are emitted inside the nodes.
            # Send a final close-of-turn marker so the client knows we're done.
            await websocket.send_json({
                "event": "turn_complete",
                "trace_id": final_state.get("trace_id", ""),
            })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
