"""
agents/knowledge_agent.py
-------------------------
Knowledge Brain Agent — answers questions about internal organization data
by retrieving from OpenSearch (the shared RAG pipeline index).

This is a LangGraph node: async function (state) -> partial state update.

It emits progress events so the Angular client sees:
  "Searching knowledge base..." → "Found N relevant documents..."
"""

import asyncio
import time
import logging

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.opensearch_tool import get_retriever
from tools.llm import get_llm

logger = logging.getLogger(__name__)


_KNOWLEDGE_PROMPT = """You are the Knowledge Brain for internal organization data.
Answer the user's question using ONLY the retrieved context below.
If the context does not contain the answer, say you don't have that information
in the internal knowledge base. Cite the source file names you used.

Retrieved context:
{context}

Question: {question}

Answer:"""


async def knowledge_agent_node(state: AgentState) -> dict:
    """
    LangGraph node for the Knowledge Brain agent.
    """
    start = time.time()
    emit = state.get("emit")
    query = state["user_query"]
    org = state.get("detected_org")

    if emit:
        await emit("agent_progress", "knowledge",
                   f"Searching {org or 'internal'} knowledge base...")

    # ── Retrieve from OpenSearch ──────────────────────────────────────────────
    try:
        retriever = await asyncio.to_thread(get_retriever)
        chunks = await asyncio.to_thread(retriever.search, query)
    except Exception as e:
        logger.error(f"Knowledge retrieval failed: {e}")
        return {
            "knowledge_output": {"error": str(e), "chunks": []},
            "agent_result": {
                "agent": "knowledge",
                "content": "I couldn't reach the knowledge base right now.",
                "sources": [],
                "raw": {"error": str(e)},
            },
            "error": str(e),
        }

    if emit:
        await emit("agent_progress", "knowledge",
                   f"Found {len(chunks)} relevant documents, composing answer...")

    if not chunks:
        result_content = "I don't have any internal documents matching that question."
        return {
            "knowledge_output": {"chunks": []},
            "agent_result": {
                "agent": "knowledge",
                "content": result_content,
                "sources": [],
                "raw": {"chunks": []},
            },
            "latency_ms": {**state.get("latency_ms", {}),
                           "knowledge": int((time.time() - start) * 1000)},
        }

    # ── Compose answer with the LLM ───────────────────────────────────────────
    context_block = "\n\n---\n\n".join(
        f"[Source: {c['file_name']}]\n{c['content']}" for c in chunks
    )
    prompt = ChatPromptTemplate.from_template(_KNOWLEDGE_PROMPT)
    chain = prompt | get_llm()
    response = await asyncio.to_thread(chain.invoke, {"context": context_block, "question": query})

    sources = list({c["file_name"] for c in chunks if c["file_name"]})
    latency = int((time.time() - start) * 1000)

    return {
        "knowledge_output": {"chunks": chunks, "answer": response.content},
        "agent_result": {
            "agent": "knowledge",
            "content": response.content,
            "sources": sources,
            "raw": {"chunk_count": len(chunks)},
        },
        "latency_ms": {**state.get("latency_ms", {}), "knowledge": latency},
    }
