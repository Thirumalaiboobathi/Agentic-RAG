"""
tools/llm.py
------------
Single factory for the Bedrock LLM. Every agent imports get_llm() from here
so the model config lives in exactly one place (driven by agents.yaml / .env).

Credential priority (mirrors RAG_AWS/test_bedrock_llm.py):
  1. Explicit BEDROCK_AWS_ACCESS_KEY_ID + BEDROCK_AWS_SECRET_ACCESS_KEY
  2. BEDROCK_AWS_PROFILE (named AWS profile)
  3. Default credential chain (env AWS_*, ~/.aws/credentials, ECS task role)

Model is set via BEDROCK_MODEL_ID in .env (resolved into agents.yaml).
"""

import os
import logging
from functools import lru_cache

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock

from config.settings import settings

logger = logging.getLogger(__name__)

BEDROCK_PROFILE    = os.getenv("BEDROCK_AWS_PROFILE", "")
BEDROCK_ACCESS_KEY = os.getenv("BEDROCK_AWS_ACCESS_KEY_ID", "")
BEDROCK_SECRET_KEY = os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY", "")


@lru_cache(maxsize=1)
def get_llm() -> ChatBedrock:
    """
    Returns a cached ChatBedrock instance configured from agents.yaml / .env.

    Builds a boto3 session using the same credential-priority logic as
    RAG_AWS/test_bedrock_llm.py, then passes the resulting bedrock-runtime
    client directly into ChatBedrock so credential handling is explicit.
    """
    cfg = settings.llm

    boto_config = Config(retries={"max_attempts": 3, "mode": "standard"})

    if BEDROCK_ACCESS_KEY and BEDROCK_SECRET_KEY:
        session = boto3.Session(
            aws_access_key_id=BEDROCK_ACCESS_KEY,
            aws_secret_access_key=BEDROCK_SECRET_KEY,
        )
        logger.info("Bedrock: using explicit access-key credentials")
    elif BEDROCK_PROFILE:
        session = boto3.Session(profile_name=BEDROCK_PROFILE)
        logger.info(f"Bedrock: using AWS profile '{BEDROCK_PROFILE}'")
    else:
        session = boto3.Session()
        logger.info("Bedrock: using default credential chain")

    client = session.client(
        "bedrock-runtime",
        region_name=cfg["region"],
        config=boto_config,
    )

    llm = ChatBedrock(
        model=cfg["model_id"],
        client=client,
        model_kwargs={
            "temperature": cfg["temperature"],
            "max_tokens": cfg["max_tokens"],
        },
        beta_use_converse_api=True,
    )
    logger.info(f"ChatBedrock initialised — model={cfg['model_id']}")
    return llm
