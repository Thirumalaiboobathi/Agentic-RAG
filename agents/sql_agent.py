"""
agents/sql_agent.py
-------------------
SQL Agent — answers data questions (orders, products, counts, revenue).

Implements the required 3-step flow:
  1. frame_query   — one LLM call to write the SQL
  2. verify_query  — a tool call to validate safety + allowed tables
  3. execute_query — a tool call to run it against RDS PostgreSQL

Each step emits a progress event to the WebSocket client.
After execution, one more LLM call turns the raw rows into a natural-language
answer (so the Author Agent receives readable content, not raw tuples).
"""

import asyncio
import json
import time
import logging

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.sql_tools import frame_query, verify_query, execute_query
from tools.llm import get_llm

logger = logging.getLogger(__name__)


_ANSWER_PROMPT = """The user asked: {question}

The SQL query returned these rows (JSON):
{rows}

Write a concise, natural-language answer to the user's question based on these results.
If there are no rows, say no matching data was found. Do not mention SQL or tables."""


async def sql_agent_node(state: AgentState) -> dict:
    """
    LangGraph node for the SQL agent — 3-step flow with progress events.
    """
    start = time.time()
    emit = state.get("emit")
    question = state["user_query"]

    # ── Step 1: Frame the query (LLM) ─────────────────────────────────────────
    # Wrapped in asyncio.to_thread so the synchronous LLM/DB calls don't block
    # the event loop while other WebSocket clients are being served.
    if emit:
        await emit("agent_progress", "sql", "Framing SQL query from your question...")
    sql = await asyncio.to_thread(frame_query, question)

    # ── Step 2: Verify the query (tool) ───────────────────────────────────────
    if emit:
        await emit("agent_progress", "sql", "Verifying query safety...")
    verification = await asyncio.to_thread(verify_query, sql)

    if not verification["valid"]:
        logger.warning(f"SQL verification failed: {verification['reason']}")
        content = (
            "I couldn't run that data request safely. "
            f"Reason: {verification['reason']}"
        )
        return {
            "sql_output": {"sql": sql, "verified": False, "reason": verification["reason"]},
            "agent_result": {
                "agent": "sql",
                "content": content,
                "sources": [],
                "raw": {"sql": sql, "verification": verification},
            },
            "latency_ms": {**state.get("latency_ms", {}),
                           "sql": int((time.time() - start) * 1000)},
        }

    # ── Step 3: Execute the query (tool) ──────────────────────────────────────
    if emit:
        await emit("agent_progress", "sql", "Executing query against database...")
    execution = await asyncio.to_thread(execute_query, sql)

    if not execution["success"]:
        content = f"The query failed to execute: {execution['error']}"
        return {
            "sql_output": {"sql": sql, "verified": True, "execution": execution},
            "agent_result": {
                "agent": "sql",
                "content": content,
                "sources": [],
                "raw": {"sql": sql, "error": execution["error"]},
            },
            "latency_ms": {**state.get("latency_ms", {}),
                           "sql": int((time.time() - start) * 1000)},
        }

    # ── Turn rows into a natural-language answer (LLM) ────────────────────────
    if emit:
        await emit("agent_progress", "sql",
                   f"Got {execution['row_count']} rows, composing answer...")

    rows_json = json.dumps(execution["rows"][:50], default=str)  # cap at 50 rows for the prompt
    prompt = ChatPromptTemplate.from_template(_ANSWER_PROMPT)
    chain = prompt | get_llm()
    answer = await asyncio.to_thread(chain.invoke, {"question": question, "rows": rows_json})

    latency = int((time.time() - start) * 1000)

    return {
        "sql_output": {
            "sql": sql,
            "verified": True,
            "row_count": execution["row_count"],
            "rows": execution["rows"][:50],
        },
        "agent_result": {
            "agent": "sql",
            "content": answer.content,
            "sources": [f"SQL: {sql}"],
            "raw": {"sql": sql, "row_count": execution["row_count"]},
        },
        "latency_ms": {**state.get("latency_ms", {}), "sql": latency},
    }
