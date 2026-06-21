"""
graph/state.py
--------------
The shared state object that flows through every node in the LangGraph.

In LangGraph 1.x, state is a TypedDict. Each node receives the current state
and returns a partial dict of fields to update. LangGraph merges the updates.

This single state object carries everything: the user query, the routing
decision, each agent's output, guardrail flags, and the progress callback
used to stream updates to the WebSocket client.
"""

from typing import TypedDict, Optional, Any, Callable, Awaitable
from typing_extensions import NotRequired


class AgentState(TypedDict):
    """
    State shared across all nodes in the multi-agent graph.

    Fields are grouped by lifecycle stage. NotRequired fields are populated
    as the graph progresses — they won't all be present at the start.
    """

    # ── Input (set at graph entry) ────────────────────────────────────────────
    session_id: str
    user_query: str

    # ── Progress streaming ────────────────────────────────────────────────────
    # An async callback the nodes call to push progress to the WebSocket.
    # Signature: await emit(event_type: str, agent: str, message: str, data: dict)
    # Stored in state so every node can reach it without globals.
    emit: NotRequired[Callable[..., Awaitable[None]]]

    # ── Guardrail results ─────────────────────────────────────────────────────
    guardrail_blocked: NotRequired[bool]
    guardrail_flags: NotRequired[list[str]]   # e.g. ["sql_injection"]

    # ── Routing decision (set by orchestrator) ────────────────────────────────
    selected_agent: NotRequired[str]          # "knowledge" | "sql" | "research"
    routing_reason: NotRequired[str]
    detected_org: NotRequired[Optional[str]]  # canonical org name if matched

    # ── Agent outputs (only one is populated, based on routing) ───────────────
    knowledge_output: NotRequired[dict]
    sql_output: NotRequired[dict]
    research_output: NotRequired[dict]

    # ── Raw agent result (normalized — what Author Agent consumes) ─────────────
    # { "agent": str, "content": str, "sources": list, "raw": Any }
    agent_result: NotRequired[dict]

    # ── Final output (set by Author Agent, after PII masking) ─────────────────
    final_response: NotRequired[str]

    # ── Evaluation / tracing ──────────────────────────────────────────────────
    trace_id: NotRequired[str]
    latency_ms: NotRequired[dict]             # {"sql": 1234, "author": 88}
    error: NotRequired[Optional[str]]


def new_state(session_id: str, user_query: str, emit=None) -> AgentState:
    """
    Helper to create a fresh state at graph entry.
    """
    return AgentState(
        session_id=session_id,
        user_query=user_query,
        emit=emit,
        guardrail_blocked=False,
        guardrail_flags=[],
        detected_org=None,
        latency_ms={},
        error=None,
    )
