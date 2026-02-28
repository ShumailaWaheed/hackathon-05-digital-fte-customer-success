"""Shared LLM client — uses Groq (free) for chat, sentence-transformers for embeddings.

Groq is OpenAI-compatible, so we use the openai SDK with a different base_url.
Embeddings are generated locally using sentence-transformers (all-MiniLM-L6-v2, 384 dims).
"""

from __future__ import annotations

import os
import logging
from functools import lru_cache

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# --- Chat client (Groq - free, OpenAI-compatible) ---

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("GROQ_API_KEY", ""))
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")

_chat_client: AsyncOpenAI | None = None


def get_chat_client() -> AsyncOpenAI:
    """Get the shared async chat client (Groq)."""
    global _chat_client
    if _chat_client is None:
        _chat_client = AsyncOpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )
    return _chat_client


# --- Embedding model (local, free, no API key needed) ---

_embedding_model = None
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load local sentence-transformers model (downloaded once, cached)."""
    from sentence_transformers import SentenceTransformer
    logger.info("Loading local embedding model: all-MiniLM-L6-v2")
    return SentenceTransformer("all-MiniLM-L6-v2")


def generate_embedding(text: str) -> list[float]:
    """Generate embedding locally using sentence-transformers.

    Returns a 384-dimensional vector.
    """
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


async def generate_embedding_async(text: str) -> list[float]:
    """Async wrapper for embedding generation.

    sentence-transformers is sync, so we run it in the default executor.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_embedding, text)
