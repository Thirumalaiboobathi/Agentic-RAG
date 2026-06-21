"""
guardrails/guardrail.py
-----------------------
Two guardrails, both driven by patterns in agents.yaml:

  1. INPUT GUARD  — check_sql_injection(query)
     Runs BEFORE any agent. If the raw user query matches a SQL-injection
     pattern, the request is blocked outright.

  2. OUTPUT GUARD — mask_pii(text)
     Runs on the Author Agent's output BEFORE sending to the client.
     Emails and phone numbers are replaced with redaction tokens.

Both are pure functions (no side effects) so they're trivial to unit test.
"""

import re
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


# ─── Compile patterns once at import time ──────────────────────────────────────
_gr = settings.guardrails

_SQL_INJECTION_ENABLED = _gr["sql_injection"]["enabled"]
_SQL_INJECTION_PATTERNS = [
    re.compile(p) for p in _gr["sql_injection"]["patterns"]
]

_PII_ENABLED = _gr["pii_masking"]["enabled"]
_PII_RULES = [
    {"name": r["name"], "pattern": re.compile(r["pattern"]), "mask": r["mask"]}
    for r in _gr["pii_masking"]["rules"]
]


# ─── Input guard: SQL injection ────────────────────────────────────────────────

def check_sql_injection(query: str) -> tuple[bool, list[str]]:
    """
    Check a user query for SQL-injection patterns.

    Returns:
        (is_blocked, matched_flags)
        is_blocked    — True if any injection pattern matched
        matched_flags — list of human-readable flags for logging/eval
    """
    if not _SQL_INJECTION_ENABLED:
        return False, []

    flags = []
    for pattern in _SQL_INJECTION_PATTERNS:
        if pattern.search(query):
            flags.append(f"sql_injection:{pattern.pattern[:40]}")

    if flags:
        logger.warning(f"SQL injection blocked — query='{query[:80]}', flags={flags}")
        return True, ["sql_injection"]

    return False, []


# ─── Output guard: PII masking ─────────────────────────────────────────────────

def mask_pii(text: str) -> tuple[str, list[str]]:
    """
    Replace PII (emails, phone numbers) in text with redaction tokens.

    Returns:
        (masked_text, pii_types_found)
        masked_text     — text with PII replaced
        pii_types_found — e.g. ["email", "phone_india"] for eval logging
    """
    if not _PII_ENABLED or not text:
        return text, []

    found = []
    masked = text
    for rule in _PII_RULES:
        if rule["pattern"].search(masked):
            found.append(rule["name"])
            masked = rule["pattern"].sub(rule["mask"], masked)

    if found:
        logger.info(f"PII masked — types={found}")

    # De-duplicate while preserving order
    return masked, list(dict.fromkeys(found))


# ─── Combined helper for the graph entry node ──────────────────────────────────

def run_input_guardrails(query: str) -> dict:
    """
    Run all input-side guardrails. Returns a dict to merge into AgentState.
    """
    blocked, flags = check_sql_injection(query)
    return {
        "guardrail_blocked": blocked,
        "guardrail_flags": flags,
    }
