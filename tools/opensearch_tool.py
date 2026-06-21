"""
tools/opensearch_tool.py
------------------------
Retrieves relevant chunks from the shared OpenSearch vector index using the
same client setup as RAG_AWS/opensearch_client.py and the same credential
logic as RAG_AWS/embeddings.py.

Auth modes (controlled by USE_AWS_OPENSEARCH env var):
  - false (default/local) → basic auth (OPENSEARCH_USERNAME / OPENSEARCH_PASSWORD)
  - true  (production)    → AWS SigV4 via BEDROCK_AWS_* credentials

Embedding:
  - Amazon Titan Embed Text V2  (1024 dims, normalize=True)
  - Credentials resolved: BEDROCK_AWS_ACCESS_KEY_ID → BEDROCK_AWS_PROFILE → default chain

Flow:
    query text → Bedrock Titan embed (1024-dim) → OpenSearch kNN search → top-k chunks
"""

import json
import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

load_dotenv()

from config.settings import settings

logger = logging.getLogger(__name__)

# ── Credential env vars (same names as RAG_AWS) ──────────────────────────────
_BEDROCK_ACCESS_KEY = os.getenv("BEDROCK_AWS_ACCESS_KEY_ID", "")
_BEDROCK_SECRET_KEY = os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY", "")
_BEDROCK_PROFILE    = os.getenv("BEDROCK_AWS_PROFILE", "")

# ── OpenSearch auth env vars (same names as RAG_AWS) ─────────────────────────
_OS_USERNAME       = os.getenv("OPENSEARCH_USERNAME", "admin")
_OS_PASSWORD       = os.getenv("OPENSEARCH_PASSWORD", "")
_USE_AWS_OPENSEARCH = os.getenv("USE_AWS_OPENSEARCH", "false").lower() == "true"

# Titan V2 safe character limit (~8192 tokens)
_MAX_CHARS = 30_000


def _make_bedrock_session() -> boto3.Session:
    """Same 3-priority credential logic as RAG_AWS/embeddings.py."""
    if _BEDROCK_ACCESS_KEY and _BEDROCK_SECRET_KEY:
        logger.info("OpenSearch/Bedrock: using explicit BEDROCK_AWS_ACCESS_KEY_ID")
        return boto3.Session(
            aws_access_key_id=_BEDROCK_ACCESS_KEY,
            aws_secret_access_key=_BEDROCK_SECRET_KEY,
        )
    if _BEDROCK_PROFILE:
        logger.info(f"OpenSearch/Bedrock: using AWS profile '{_BEDROCK_PROFILE}'")
        return boto3.Session(profile_name=_BEDROCK_PROFILE)
    logger.info("OpenSearch/Bedrock: using default credential chain")
    return boto3.Session()


class OpenSearchRetriever:
    """
    Semantic retrieval against the shared OpenSearch vector index.

    Mirrors RAG_AWS/opensearch_client.py (auth) + RAG_AWS/embeddings.py (embed).

    Usage:
        retriever = OpenSearchRetriever()
        chunks = retriever.search("What is OTB's SLA policy?", top_k=5)
    """

    def __init__(self):
        cfg = settings.opensearch
        self.index_name        = cfg["index_name"]
        self.embedding_model_id = cfg["embedding_model_id"]
        self.embedding_dims    = cfg["embedding_dimensions"]
        self.default_top_k     = cfg["top_k"]
        self.region            = settings.llm["region"]

        self._session  = _make_bedrock_session()
        self._bedrock  = self._session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(retries={"max_attempts": 1, "mode": "standard"}),
        )
        self._os_client = self._build_os_client(cfg)
        logger.info(
            f"OpenSearchRetriever ready — index={self.index_name}, "
            f"aws_auth={_USE_AWS_OPENSEARCH}, dims={self.embedding_dims}"
        )

    # ── OpenSearch client ─────────────────────────────────────────────────────

    def _build_os_client(self, cfg: dict) -> OpenSearch:
        host = cfg["host"].replace("https://", "").replace("http://", "")

        if _USE_AWS_OPENSEARCH:
            # Production: SigV4 (same session as Bedrock)
            credentials = self._session.get_credentials()
            auth = AWSV4SignerAuth(credentials, self.region, "es")
            logger.info("OpenSearch: using SigV4 auth")
        else:
            # Local/dev: basic auth (same as RAG_AWS with USE_AWS_OPENSEARCH=false)
            auth = (_OS_USERNAME, _OS_PASSWORD)
            logger.info(f"OpenSearch: using basic auth (user={_OS_USERNAME})")

        return OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

    # ── Embedding (mirrors RAG_AWS/embeddings.py) ─────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Embed query text with Bedrock Titan V2 (1024-dim, normalized)."""
        if not text or not text.strip():
            return [0.0] * self.embedding_dims

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS]

        payload = {
            "inputText": text,
            "dimensions": self.embedding_dims,  # Titan V2: 256 | 512 | 1024
            "normalize": True,                  # unit vectors → cosine similarity
        }

        try:
            response = self._bedrock.invoke_model(
                modelId=self.embedding_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )
            return json.loads(response["body"].read())["embedding"]

        except ClientError as e:
            logger.error(f"Bedrock embedding failed: {e}")
            raise

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Embed the query then run kNN search — mirrors RAG_AWS/opensearch_client.py.

        Returns list of dicts: {content, score, file_name, source_key,
                                 file_type, chunk_index, total_chunks}
        """
        k = top_k or self.default_top_k
        query_vector = self._embed(query)

        body = {
            "size": k,
            "query": {"knn": {"embedding": {"vector": query_vector, "k": k}}},
            "_source": {"excludes": ["embedding"]},
        }

        response = self._os_client.search(index=self.index_name, body=body)
        hits = response["hits"]["hits"]

        results = []
        for hit in hits:
            src = hit["_source"]
            results.append({
                "content":      src.get("content", ""),
                "score":        hit["_score"],
                "file_name":    src.get("file_name", ""),
                "source_key":   src.get("source_key", ""),
                "file_type":    src.get("file_type", ""),
                "chunk_index":  src.get("chunk_index", 0),
                "total_chunks": src.get("total_chunks", 0),
            })

        logger.info(f"OpenSearch returned {len(results)} chunks for query")
        return results


# Module-level singleton (lazy — created on first use)
_retriever = None


def get_retriever() -> OpenSearchRetriever:
    global _retriever
    if _retriever is None:
        _retriever = OpenSearchRetriever()
    return _retriever
