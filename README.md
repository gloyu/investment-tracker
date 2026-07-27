import os
from openai import OpenAI

_client: OpenAI | None = None

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions — matches schema


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY. Check your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client


def generate_embedding(text: str) -> list[float]:
    """
    Generates a single embedding vector for a piece of text.
    Used at ingestion time so raw_items are embedded as soon as they're
    written, keeping the clustering/enrichment steps simple (no separate
    backfill pass needed).
    """
    response = _get_client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Batch version — OpenAI's embeddings endpoint accepts an array of
    strings in one request, which is cheaper and faster than looping
    generate_embedding() for multiple texts.
    """
    if not texts:
        return []
    response = _get_client().embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
