import os
import time
from datetime import datetime, timezone

import requests

from lib.supabase_client import supabase
from lib.embeddings import generate_embedding

ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


def _fetch_quote_for_symbol(symbol: str) -> dict | None:
    """
    Fetches the latest quote for a single symbol from Alpha Vantage's
    GLOBAL_QUOTE endpoint and formats it into a raw_items-shaped record.
    Returns None if the symbol had no usable data (rate limited, bad symbol, etc).
    """
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)

    if not response.ok:
        print(f"[ingest_prices] HTTP {response.status_code} fetching {symbol}")
        return None

    data = response.json()

    if data.get("Note") or data.get("Information"):
        print(
            f"[ingest_prices] Alpha Vantage returned an error for {symbol}: "
            f"{data.get('Note') or data.get('Information')}"
        )
        return None

    quote = data.get("Global Quote")
    if not quote or not quote.get("05. price"):
        print(f"[ingest_prices] No quote data returned for {symbol}")
        return None

    price = quote["05. price"]
    volume = quote["06. volume"]
    change = quote["09. change"]
    change_percent = quote["10. change percent"]
    trading_day = quote["07. latest trading day"]

    # Plain-language content string — this is what gets embedded and what
    # the draft node will summarize from, so keep it factual and specific.
    content = (
        f"{symbol} closed at ${price} on {trading_day}, a change of {change} "
        f"({change_percent}) from the previous close. Volume: {volume} shares."
    )

    embedding = generate_embedding(content)
    published_at = datetime.strptime(trading_day, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()

    return {
        "symbol": symbol,
        "source": "price",
        "content": content,
        "url": None,
        "published_at": published_at,
        "embedding": embedding,
    }


def ingest_prices() -> dict:
    """
    Ingests price/volume data for every active watchlist symbol and
    writes the results to raw_items. Returns a summary for the dag_steps
    output column.
    """
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("Missing ALPHA_VANTAGE_API_KEY. Check your .env file.")

    watchlist_response = supabase.table("watchlist").select("symbol").eq("active", True).execute()
    symbols = [row["symbol"] for row in watchlist_response.data]

    errors: list[str] = []
    items_to_insert: list[dict] = []

    # Alpha Vantage free tier is rate-limited (typically 5 req/min), so
    # fetch sequentially with a small delay rather than in parallel.
    for symbol in symbols:
        try:
            item = _fetch_quote_for_symbol(symbol)
            if item:
                items_to_insert.append(item)
            else:
                errors.append(f"No data for {symbol}")
        except Exception as err:
            errors.append(f"{symbol}: {err}")

        # ~13s between calls keeps us under a 5 req/min limit with margin
        time.sleep(13)

    if items_to_insert:
        supabase.table("raw_items").insert(items_to_insert).execute()

    return {
        "symbolsProcessed": len(symbols),
        "itemsInserted": len(items_to_insert),
        "errors": errors,
    }
