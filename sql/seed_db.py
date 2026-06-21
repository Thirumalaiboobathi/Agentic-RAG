"""
sql/seed_db.py
--------------
Connects to PostgreSQL using credentials from the project .env file
and executes seed.sql to create tables and load sample data.

Usage:
    # From the multi-agent/ root directory:
    python sql/seed_db.py

    # Or from inside sql/:
    python seed_db.py
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# ── Locate .env relative to this file (../. env from sql/) ───────────────────
_HERE = Path(__file__).parent
_ENV_PATH = _HERE.parent / ".env"
_SEED_SQL = _HERE / "seed.sql"

if not _ENV_PATH.exists():
    print(f"[ERROR] .env not found at {_ENV_PATH}")
    print("        Copy .env.example to .env and fill in your credentials.")
    sys.exit(1)

load_dotenv(_ENV_PATH)

# ── Build connection params from env ──────────────────────────────────────────
def _get_conn_params() -> dict:
    missing = []
    params = {}
    for key in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        val = os.getenv(key)
        if not val:
            missing.append(key)
        params[key] = val

    if missing:
        print(f"[ERROR] Missing required env vars: {', '.join(missing)}")
        print(f"        Check your .env file at {_ENV_PATH}")
        sys.exit(1)

    return {
        "host":     params["POSTGRES_HOST"],
        "dbname":   params["POSTGRES_DB"],
        "user":     params["POSTGRES_USER"],
        "password": params["POSTGRES_PASSWORD"],
        "port":     int(os.getenv("POSTGRES_PORT", "5432")),
    }


def _ensure_database(params: dict):
    """
    Connect to the default 'postgres' maintenance database and create
    the target database if it doesn't already exist.
    CREATE DATABASE cannot run inside a transaction, so autocommit is required.
    """
    target_db = params["dbname"]
    maintenance_params = {**params, "dbname": "postgres", "autocommit": True}

    try:
        with psycopg.connect(**{k: v for k, v in maintenance_params.items()
                                if k != "autocommit"},
                             connect_timeout=10,
                             autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                if cur.fetchone():
                    print(f"Database '{target_db}' already exists.")
                else:
                    cur.execute(f'CREATE DATABASE "{target_db}"')
                    print(f"Database '{target_db}' created.")
    except psycopg.OperationalError as e:
        print(f"[ERROR] Could not connect to maintenance database: {e}")
        sys.exit(1)


def run_seed():
    params = _get_conn_params()

    print(f"Connecting to PostgreSQL at {params['host']}:{params['port']} "
          f"(db={params['dbname']}, user={params['user']}) ...")

    # Create the target database if it doesn't exist yet
    _ensure_database(params)

    try:
        with psycopg.connect(**params, connect_timeout=10) as conn:
            print(f"Connected. Executing {_SEED_SQL.name} ...")
            sql = _SEED_SQL.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("Done. Tables created and seed data loaded.")
    except psycopg.OperationalError as e:
        print(f"[ERROR] Could not connect to PostgreSQL: {e}")
        sys.exit(1)
    except psycopg.Error as e:
        print(f"[ERROR] SQL execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_seed()
