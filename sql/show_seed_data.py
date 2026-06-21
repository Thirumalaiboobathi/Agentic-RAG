"""
sql/show_seed_data.py
---------------------
Connects to PostgreSQL using credentials from .env and prints all records
from the four tables created by seed.sql.

Usage:
    python sql/show_seed_data.py
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

_HERE = Path(__file__).parent
_ENV_PATH = _HERE.parent / ".env"

if not _ENV_PATH.exists():
    print(f"[ERROR] .env not found at {_ENV_PATH}")
    sys.exit(1)

load_dotenv(_ENV_PATH)


def _get_conn_params() -> dict:
    missing = []
    params = {}
    for key in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        val = os.getenv(key)
        if not val:
            missing.append(key)
        params[key] = val
    if missing:
        print(f"[ERROR] Missing env vars: {', '.join(missing)}")
        sys.exit(1)
    return {
        "host":     params["POSTGRES_HOST"],
        "dbname":   params["POSTGRES_DB"],
        "user":     params["POSTGRES_USER"],
        "password": params["POSTGRES_PASSWORD"],
        "port":     int(os.getenv("POSTGRES_PORT", "5432")),
    }


def _print_table(title: str, columns: list[str], rows: list[tuple]):
    """Pretty-print query results as an ASCII table."""
    print(f"\n{'=' * 60}")
    print(f"  {title}  ({len(rows)} row{'s' if len(rows) != 1 else ''})")
    print(f"{'=' * 60}")

    if not rows:
        print("  (no rows)")
        return

    # Calculate column widths
    col_widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    def fmt_row(values):
        return "  " + "  |  ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(values))

    separator = "  " + "--+--".join("-" * w for w in col_widths)

    print(fmt_row(columns))
    print(separator)
    for row in rows:
        print(fmt_row(row))


def show_all(conn):
    queries = [
        (
            "customers",
            "SELECT id, name, email, created_at FROM customers ORDER BY id",
        ),
        (
            "products",
            "SELECT id, name, category, price, stock FROM products ORDER BY id",
        ),
        (
            "orders",
            "SELECT id, customer_id, order_date, total_amount, status FROM orders ORDER BY id",
        ),
        (
            "order_items",
            "SELECT id, order_id, product_id, quantity, unit_price FROM order_items ORDER BY id",
        ),
    ]

    with conn.cursor() as cur:
        for table, sql in queries:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            _print_table(table.upper(), columns, rows)

    print(f"\n{'=' * 60}\n")


def main():
    params = _get_conn_params()
    print(f"Connecting to {params['host']}:{params['port']} "
          f"(db={params['dbname']}, user={params['user']}) ...")
    try:
        with psycopg.connect(**params, connect_timeout=10) as conn:
            print("Connected.")
            show_all(conn)
    except psycopg.OperationalError as e:
        print(f"[ERROR] Could not connect: {e}")
        sys.exit(1)
    except psycopg.Error as e:
        print(f"[ERROR] Query failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
