"""
agents/author_agent.py
----------------------
Author Agent — the single output agent. ALL responses flow through here
before reaching the client, regardless of which agent produced the content.

Responsibilities:
  1. Take the upstream agent_result and polish it into a final answer.
  2. Apply the PII-masking output guardrail (emails, phones → redacted).
  3. Emit the final agent_complete event with the masked response + sources.

Keeping output centralised here means PII masking and formatting happen in
exactly one place — no agent can bypass it.
"""

import asyncio
import time
import logging

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.llm import get_llm
from guardrails.guardrail import mask_pii

logger = logging.getLogger(__name__)


_AUTHOR_PROMPT = """You are the final response author. You receive a draft answer from an
upstream agent. Rewrite it to be clear, well-structured, and directly addressing the
user's question. Keep all factual content and citations intact. Do not add information
that isn't in the draft.

User's original question: {question}

Draft answer from {agent} agent:
{draft}

Polished final answer:"""


async def author_agent_node(state: AgentState) -> dict:
    """
    LangGraph node for the Author agent — final formatting + PII guard.
    """
    start = time.time()
    emit = state.get("emit")
    question = state["user_query"]
    agent_result = state.get("agent_result", {})

    draft = agent_result.get("content", "")
    source_agent = agent_result.get("agent", "unknown")
    sources = agent_result.get("sources", [])

    if emit:
        await emit("agent_progress", "author", "Composing final response...")

    # ── Polish the draft (LLM) ────────────────────────────────────────────────
    # Skip polishing for error messages — pass them through directly.
    if draft and not draft.lower().startswith(("i couldn't", "the query failed", "i don't have")):
        prompt = ChatPromptTemplate.from_template(_AUTHOR_PROMPT)
        chain = prompt | get_llm()
        polished = (await asyncio.to_thread(chain.invoke, {
            "question": question,
            "agent": source_agent,
            "draft": draft,
        })).content
    else:
        polished = draft

    # ── Apply PII-masking output guardrail ────────────────────────────────────
    masked_response, pii_found = mask_pii(polished)

    # Append sources if present
    if sources:
        source_lines = "\n".join(f"  - {s}" for s in sources)
        masked_response = f"{masked_response}\n\nSources:\n{source_lines}"

    latency = int((time.time() - start) * 1000)

    # Track PII flags for evaluation
    existing_flags = state.get("guardrail_flags", [])
    if pii_found:
        existing_flags = existing_flags + [f"pii_masked:{t}" for t in pii_found]

    if emit:
        await emit("agent_complete", "author", "Response ready", data={
            "response": masked_response,
            "source_agent": source_agent,
            "sources": sources,
        })

    return {
        "final_response": masked_response,
        "guardrail_flags": existing_flags,
        "latency_ms": {**state.get("latency_ms", {}), "author": latency},
    }
