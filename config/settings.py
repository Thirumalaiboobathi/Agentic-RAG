"""
config/settings.py
------------------
Loads agents.yaml and resolves ${ENV_VAR} placeholders from the environment.

This is the single source of truth for all configuration. Every other module
imports `settings` from here — nothing reads os.environ or the YAML directly.

Usage:
    from config.settings import settings
    model_id = settings.llm["model_id"]
    orgs = settings.organizations
"""

import os
import re
import logging
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Path to agents.yaml (same directory as this file)
_CONFIG_PATH = Path(__file__).parent / "agents.yaml"

# Matches ${VAR_NAME} placeholders in the YAML
_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _resolve_env_vars(value):
    """Recursively replace ${ENV_VAR} placeholders with actual env values."""
    if isinstance(value, str):
        def replace(match):
            env_name = match.group(1)
            env_value = os.getenv(env_name)
            if env_value is None:
                logger.warning(f"Environment variable {env_name} is not set")
                return ""
            return env_value
        return _ENV_PATTERN.sub(replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


class Settings:
    """
    Parsed configuration object. Loads once, caches in memory.
    """

    def __init__(self, config_path: Path = _CONFIG_PATH):
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self._config = _resolve_env_vars(raw)
        logger.info(f"Settings loaded from {config_path}")

    # ── Top-level sections as properties ──────────────────────────────────────
    @property
    def llm(self) -> dict:
        return self._config["llm"]

    @property
    def organizations(self) -> list:
        return self._config["organizations"]

    @property
    def opensearch(self) -> dict:
        return self._config["opensearch"]

    @property
    def postgres(self) -> dict:
        return self._config["postgres"]

    @property
    def research(self) -> dict:
        return self._config["research"]

    @property
    def routing(self) -> dict:
        return self._config["routing"]

    @property
    def guardrails(self) -> dict:
        return self._config["guardrails"]

    @property
    def evaluation(self) -> dict:
        return self._config["evaluation"]

    # ── Convenience helpers ───────────────────────────────────────────────────
    def all_org_aliases(self) -> dict:
        """
        Returns a flat map of {alias_lowercase: canonical_org_name}.
        Used by the orchestrator to detect org mentions in a query.
        """
        alias_map = {}
        for org in self.organizations:
            canonical = org["name"]
            alias_map[canonical.lower()] = canonical
            for alias in org.get("aliases", []):
                alias_map[alias.lower()] = canonical
        return alias_map

    def postgres_dsn(self) -> str:
        """Build a psycopg3 connection string from postgres config."""
        pg = self.postgres
        return (
            f"host={pg['host']} port={pg['port']} dbname={pg['database']} "
            f"user={pg['user']} password={pg['password']}"
        )

    def postgres_sqlalchemy_url(self) -> str:
        """Build a SQLAlchemy URL (psycopg3 driver)."""
        pg = self.postgres
        return (
            f"postgresql+psycopg://{pg['user']}:{pg['password']}"
            f"@{pg['host']}:{pg['port']}/{pg['database']}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — loads config only once per process."""
    return Settings()


# Module-level singleton for convenient imports
settings = get_settings()
