from lib.supabase_client import supabase


def _average_embeddings(vectors: list[list[float]]) -> list[float]:
    """Averages a set of embedding vectors into a single centroid vector."""
    length = len(vectors[0])
    sums = [0.0] * length
    for vec in vectors:
        for i in range(length):
            sums[i] += vec[i]
    return [s / len(vectors) for s in sums]


def cluster_raw_items(run_id: str, run_started_at: str) -> tuple[list[str], dict]:
    """
    Groups this run's ingested raw_items by symbol into one cluster per
    symbol (v1 keeps clustering simple — one "daily_recap" theme per
    symbol rather than sub-clustering by topic within a symbol, since
    watchlist size is small and volume per symbol per day is low).

    Returns the created cluster IDs so the enrich/draft steps that follow
    in the same run know what to work on.
    """
    watchlist_response = supabase.table("watchlist").select("symbol").eq("active", True).execute()

    cluster_ids: list[str] = []
    skipped_symbols: list[str] = []

    for row in watchlist_response.data:
        symbol = row["symbol"]

        items_response = supabase.rpc(
            "raw_items_since", {"match_symbol": symbol, "since_timestamp": run_started_at}
        ).execute()
        items = items_response.data or []

        if not items:
            skipped_symbols.append(symbol)
            continue

        centroid = _average_embeddings([item["embedding"] for item in items])

        cluster_response = (
            supabase.table("clusters")
            .insert(
                {
                    "run_id": run_id,
                    "symbol": symbol,
                    "theme": "daily_recap",
                    "item_ids": [item["id"] for item in items],
                    "embedding": centroid,
                }
            )
            .execute()
        )
        cluster_ids.append(cluster_response.data[0]["id"])

    summary = {
        "clustersCreated": len(cluster_ids),
        "skippedSymbols": skipped_symbols,  # symbols with no new items this run
    }
    return cluster_ids, summary
