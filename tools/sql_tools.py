"""
tools/sql_tools.py
------------------
Three tools for the SQL Agent, matching the required 3-step flow:

  1. frame_query(question)    — ONE LLM call to write SQL from natural language
  2. verify_query(sql)        — a tool call to validate the SQL is safe + allowed
  3. execute_query(sql)       — a tool call to run it against RDS PostgreSQL

The verify step is the security gate: it checks the SQL only touches
allowed tables (from agents.yaml) and is read-only (SELECT). This is
separate from the input guardrail — defense in depth.
"""

import re
import logging

import psycopg
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from config.settings import settings
from tools.llm import get_llm

logger = logging.getLogger(__name__)

_ALLOWED_TABLES = set(t.lower() for t in settings.postgres["allowed_tables"])


# ─── Tool 1: Frame the SQL query (one LLM call) ────────────────────────────────

_SQL_SYSTEM_PROMPT = """You are a PostgreSQL expert. Convert the user's question into a single SQL query.

Rules:
- Generate ONLY a SELECT query. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
- Only use these tables: {allowed_tables}
- Use standard PostgreSQL syntax.
- For date math like "yesterday", cast the column to date first: `column::date = CURRENT_DATE - 1`.
  This correctly handles both DATE and TIMESTAMP columns (a bare `= CURRENT_DATE - INTERVAL '1 day'`
  only matches the exact midnight moment on TIMESTAMP columns, missing all other orders).
- Return ONLY the SQL query, no explanation, no markdown fences, no semicolon at the end.

Table schemas:
  orders(id, customer_id, order_date, total_amount, status)
  products(id, name, category, price, stock)
  customers(id, name, email, created_at)
  order_items(id, order_id, product_id, quantity, unit_price)
"""


def frame_query(question: str) -> str:
    """
    Step 1 — One LLM call to translate natural language → SQL.
    The LLM is given verify_query as a bound tool so it can signal
    validation failures directly instead of returning bad SQL.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SQL_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    chain = prompt | get_llm().bind_tools([verify_query_tool])
    response = chain.invoke({
        "question": question,
        "allowed_tables": ", ".join(sorted(_ALLOWED_TABLES)),
    })

    # When the model uses bind_tools, it may call verify_query directly with
    # the generated SQL as an argument — extract it from tool_calls in that case.
    if response.tool_calls:
        sql = response.tool_calls[0]["args"].get("sql", "")
    else:
        content = response.content
        if isinstance(content, list):
            content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        sql = content.strip()

    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
    sql = sql.rstrip(";").strip()

    logger.info(f"Framed SQL: {sql}")
    return sql


# ─── Tool 2: Verify the SQL query (tool call) ──────────────────────────────────

def verify_query(sql: str) -> dict:
    """
    Step 2 — Validate the SQL before execution.

    Checks:
      - Must be a single statement (no stacked queries via ;)
      - Must start with SELECT (read-only)
      - Must not contain dangerous keywords
      - Must only reference allowed tables

    Returns:
        {"valid": bool, "reason": str}
    """
    if not sql:
        return {"valid": False, "reason": "Empty query"}

    sql_lower = sql.lower()

    # No stacked statements
    if ";" in sql.strip().rstrip(";"):
        return {"valid": False, "reason": "Multiple statements not allowed"}

    # Must be SELECT only
    if not sql_lower.strip().startswith("select"):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}

    # Block dangerous keywords
    dangerous = ["insert", "update", "delete", "drop", "alter", "truncate",
                 "create", "grant", "revoke", "exec", "--"]
    for kw in dangerous:
        if re.search(rf"\b{kw}\b" if kw.isalpha() else re.escape(kw), sql_lower):
            return {"valid": False, "reason": f"Forbidden keyword: {kw}"}

    # Table allowlist — extract identifiers after FROM and JOIN
    referenced = set(re.findall(r"(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql_lower))
    disallowed = referenced - _ALLOWED_TABLES
    if disallowed:
        return {
            "valid": False,
            "reason": f"Query references disallowed tables: {disallowed}",
        }

    logger.info(f"SQL verified OK — tables={referenced}")
    return {"valid": True, "reason": "Query is safe and references only allowed tables"}


# LangChain tool wrapper — used only for bind_tools in frame_query.
# verify_query itself stays a plain function so sql_agent.py can call it directly.
verify_query_tool = tool(verify_query)


# ─── Tool 3: Execute the SQL query (tool call) ─────────────────────────────────

def execute_query(sql: str) -> dict:
    """
    Step 3 — Execute the verified SQL against RDS PostgreSQL.

    Uses a read-only transaction as an extra safety layer.

    Returns:
        {"success": bool, "rows": list[dict], "row_count": int, "error": str|None}
    """
    dsn = settings.postgres_dsn()
    try:
        with psycopg.connect(dsn, connect_timeout=10) as conn:
            # Force read-only at the transaction level — belt and suspenders
            conn.read_only = True
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                result_rows = [dict(zip(columns, row)) for row in rows]

        logger.info(f"SQL executed — {len(result_rows)} rows returned")
        return {
            "success": True,
            "rows": result_rows,
            "row_count": len(result_rows),
            "error": None,
        }

    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return {
            "success": False,
            "rows": [],
            "row_count": 0,
            "error": str(e),
        }
