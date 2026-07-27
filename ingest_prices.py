import os
from datetime import datetime, timedelta, timezone

import requests

from lib.supabase_client import supabase
from lib.embeddings import generate_embedding

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"

ARTICLES_PER_SYMBOL_CAP = 5  # cap per symbol to control cost/volume


def _fetch_news_for_symbol(symbol: str) -> list[dict]:
    """Fetches recent headlines for a single symbol, last 24h, English only."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    params = {
        "q": symbol,
        "language": "en",
        "sortBy": "publishedAt",
        "from": since,
        "apiKey": NEWS_API_KEY,
    }
    response = requests.get(NEWS_API_BASE_URL, params=params, timeout=15)

    if not response.ok:
        print(f"[ingest_news] HTTP {response.status_code} fetching news for {symbol}")
        return []

    data = response.json()

    if data.get("status") != "ok":
        print(f"[ingest_news] NewsAPI error for {symbol}: {data.get('message')}")
        return []

    articles = (data.get("articles") or [])[:ARTICLES_PER_SYMBOL_CAP]
    items: list[dict] = []

    for article in articles:
        title = article.get("title")
        if not title:
            continue

        source_name = article.get("source", {}).get("name", "Unknown source")
        description = article.get("description")

        # Factual, source-attributed content string — headline + description
        # only, no added commentary, so the draft node has clean grounding material.
        if description:
            content = f'{source_name} reported: "{title}" — {description}'
        else:
            content = f'{source_name} reported: "{title}"'

        embedding = generate_embedding(content)

        items.append(
            {
                "symbol": symbol,
                "source": "news",
                "content": content,
                "url": article.get("url"),
                "published_at": article.get("publishedAt"),
                "embedding": embedding,
            }
        )

    return items


def ingest_news() -> dict:
    """
    Ingests news headlines for every active watchlist symbol and writes
    the results to raw_items. Returns a summary for dag_steps output.
    """
    if not NEWS_API_KEY:
        raise RuntimeError("Missing NEWS_API_KEY. Check your .env file.")

    watchlist_response = supabase.table("watchlist").select("symbol").eq("active", True).execute()
    symbols = [row["symbol"] for row in watchlist_response.data]

    errors: list[str] = []
    items_to_insert: list[dict] = []

    for symbol in symbols:
        try:
            items = _fetch_news_for_symbol(symbol)
            items_to_insert.extend(items)
        except Exception as err:
            errors.append(f"{symbol}: {err}")

    if items_to_insert:
        supabase.table("raw_items").insert(items_to_insert).execute()

    return {
        "symbolsProcessed": len(symbols),
        "itemsInserted": len(items_to_insert),
        "errors": errors,
    }
