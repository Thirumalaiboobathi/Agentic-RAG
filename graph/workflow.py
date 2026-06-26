"""
graph/workflow.py
-----------------
Wires all nodes into a LangGraph StateGraph (LangGraph 1.x API).

Graph topology:

    START
      ↓
    [guardrail_input]  ── blocked? ──→ [blocked_response] ─→ [evaluator] → END
      ↓ (clean)
    [orchestrator]
      ↓ (conditional edge on selected_agent)
      ├──→ [knowledge] ─┐
      ├──→ [sql] ───────┤
      └──→ [research] ──┤
                        ↓
                    [author]
                        ↓
                   [evaluator]
                        ↓
                       END

The compiled graph is created once and reused for every request.
"""

import logging

from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from guardrails.guardrail import run_input_guardrails
from agents.orchestrator import orchestrator_node, route_decision
from agents.knowledge_agent import knowledge_agent_node
from agents.sql_agent import sql_agent_node
from agents.research_agent import research_agent_node
from agents.author_agent import author_agent_node
from evaluation.evaluator import evaluator_node
from agents.bmi_agents import bmi_agent_node
from agents.drug_agent import drug_agent_node



logger = logging.getLogger(__name__)


# ─── Guardrail input node ──────────────────────────────────────────────────────

async def guardrail_input_node(state: AgentState) -> dict:
    """First node — run input guardrails (SQL injection check)."""
    emit = state.get("emit")
    result = run_input_guardrails(state["user_query"])
    if result["guardrail_blocked"] and emit:
        await emit("guardrail_blocked", "guardrail",
                   "Your request was blocked by a security guardrail.")
    return result


# ─── Blocked response node ─────────────────────────────────────────────────────

async def blocked_response_node(state: AgentState) -> dict:
    """Terminal content node for blocked requests."""
    return {
        "agent_result": {
            "agent": "guardrail",
            "content": "This request was blocked because it appeared to contain "
                       "an unsafe database operation.",
            "sources": [],
            "raw": {"flags": state.get("guardrail_flags", [])},
        },
        "final_response": "This request was blocked for security reasons "
                          "(possible SQL injection detected).",
    }


# ─── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    """
    Construct and compile the LangGraph StateGraph.
    Returns a compiled graph ready for .ainvoke().
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("guardrail_input", guardrail_input_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("knowledge", knowledge_agent_node)
    graph.add_node("sql", sql_agent_node)
    graph.add_node("research", research_agent_node)
    graph.add_node("author", author_agent_node)
   
    graph.add_node("bmi",bmi_agent_node)
    graph.add_node("drug",drug_agent_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("blocked", blocked_response_node)

    # Entry: START → guardrail_input
    graph.add_edge(START, "guardrail_input")

    # guardrail_input → orchestrator (or → blocked if guardrail tripped)
    def after_guardrail(state: AgentState) -> str:
        return "blocked" if state.get("guardrail_blocked") else "orchestrator"

    graph.add_conditional_edges(
        "guardrail_input",
        after_guardrail,
        {"blocked": "blocked", "orchestrator": "orchestrator"},
    )

    # orchestrator → one of the three agents (conditional on selected_agent)
    graph.add_conditional_edges(
        "orchestrator",
        route_decision,
        {
            "knowledge": "knowledge",
            "sql": "sql",
            "research": "research",
            "weather": "weather",
            "bmi": "bmi",
            "drug": "drug",
            "blocked": "blocked",
        },
    )

    # All three agents → author
    graph.add_edge("knowledge", "author")
    graph.add_edge("sql", "author")
    graph.add_edge("research", "author")
    graph.add_edge("bmi", "author")
    graph.add_edge("drug", "author")

    graph.add_edge("author", "evaluator")


    # blocked → evaluator (we still log blocked requests for evaluation)
    graph.add_edge("blocked", "evaluator")

    # evaluator → END
    graph.add_edge("evaluator", END)

    compiled = graph.compile()
    logger.info("LangGraph compiled successfully")
    return compiled


# Module-level singleton — compiled once, reused per request
_compiled_graph = None

def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
