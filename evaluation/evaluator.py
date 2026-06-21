"""
evaluation/evaluator.py
-----------------------
Captures every agent run for offline evaluation.

Two sinks (both configured in agents.yaml):
  1. PostgreSQL  — structured rows in the agent_traces table (RDS)
  2. CloudWatch  — one JSON log line per trace (picked up by the awslogs driver)

The CloudWatch path needs no extra setup: anything printed to stdout in ECS
is captured by the log group. We emit a single-line JSON object tagged with
"EVAL_TRACE" so it's easy to filter in CloudWatch Logs Insights.

Schema (agent_traces):
    trace_id        UUID PRIMARY KEY
    session_id      TEXT
    user_query      TEXT
    selected_agent  TEXT
    routing_reason  TEXT
    agent_content   TEXT
    final_response  TEXT
    guardrail_flags TEXT[]
    latency_ms      JSONB
    error           TEXT
    created_at      TIMESTAMPTZ DEFAULT now()
"""

import json
import uuid
import logging
from datetime import datetime, timezone

import psycopg

from config.settings import settings

logger = logging.getLogger(__name__)

_eval_cfg = settings.evaluation
_TABLE = _eval_cfg["table_name"]


# ─── DDL — create the table if it doesn't exist ────────────────────────────────

_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    trace_id        UUID PRIMARY KEY,
    session_id      TEXT,
    user_query      TEXT,
    selected_agent  TEXT,
    routing_reason  TEXT,
    agent_content   TEXT,
    final_response  TEXT,
    guardrail_flags TEXT[],
    latency_ms      JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
"""


def ensure_table_exists():
    """Create the agent_traces table if needed. Call once at startup."""
    if _eval_cfg["store"] != "postgres":
        return
    try:
        with psycopg.connect(settings.postgres_dsn(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_TABLE_SQL)
            conn.commit()
        logger.info(f"Evaluation table '{_TABLE}' ready")
    except Exception as e:
        logger.error(f"Could not ensure eval table: {e}")


# ─── Capture one trace ─────────────────────────────────────────────────────────

def capture_trace(state: dict) -> str:
    """
    Persist one agent run. Called after the Author Agent finishes.

    Returns the trace_id (also logged to CloudWatch).
    Never raises — evaluation capture must not break the user request.
    """
    if not _eval_cfg.get("enabled", False):
        return ""

    trace_id = str(uuid.uuid4())
    agent_result = state.get("agent_result", {})

    trace = {
        "trace_id": trace_id,
        "session_id": state.get("session_id", ""),
        "user_query": state.get("user_query", ""),
        "selected_agent": state.get("selected_agent", ""),
        "routing_reason": state.get("routing_reason", ""),
        "agent_content": agent_result.get("content", ""),
        "final_response": state.get("final_response", ""),
        "guardrail_flags": state.get("guardrail_flags", []),
        "latency_ms": state.get("latency_ms", {}),
        "error": state.get("error"),
    }

    # ── Sink 1: CloudWatch (structured stdout line) ───────────────────────────
    if _eval_cfg.get("cloudwatch_log", True):
        # Single-line JSON, prefixed for easy filtering in Logs Insights
        cw_line = {"EVAL_TRACE": trace, "ts": datetime.now(timezone.utc).isoformat()}
        print(json.dumps(cw_line, default=str), flush=True)

    # ── Sink 2: PostgreSQL ────────────────────────────────────────────────────
    if _eval_cfg["store"] == "postgres":
        try:
            with psycopg.connect(settings.postgres_dsn(), connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {_TABLE}
                          (trace_id, session_id, user_query, selected_agent,
                           routing_reason, agent_content, final_response,
                           guardrail_flags, latency_ms, error)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            trace["trace_id"],
                            trace["session_id"],
                            trace["user_query"],
                            trace["selected_agent"],
                            trace["routing_reason"],
                            trace["agent_content"],
                            trace["final_response"],
                            trace["guardrail_flags"],
                            json.dumps(trace["latency_ms"]),
                            trace["error"],
                        ),
                    )
                conn.commit()
            logger.info(f"Trace {trace_id[:8]} persisted to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to persist trace to PostgreSQL: {e}")

    return trace_id


async def evaluator_node(state: dict) -> dict:
    """
    LangGraph node — final node in the graph. Captures the trace.
    """
    emit = state.get("emit")
    trace_id = capture_trace(state)

    if emit and trace_id:
        await emit("eval_captured", "evaluator",
                   "Response logged for evaluation", data={"trace_id": trace_id})

    return {"trace_id": trace_id}
