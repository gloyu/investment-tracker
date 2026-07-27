from lib.supabase_client import supabase

MATCH_COUNT_PER_CLUSTER = 5
MIN_SIMILARITY = 0.7  # discard weak matches rather than force-feeding irrelevant context


def enrich_clusters(
    run_id: str, cluster_ids: list[str], run_started_at: str
) -> tuple[dict[str, list[dict]], dict]:
    """
    For each cluster from this run, finds historically similar raw_items
    for the same symbol (fetched before this run started) via pgvector
    cosine similarity. This is the RAG grounding step — it gives the
    draft node context like "this is the third consecutive earnings beat"
    instead of drafting each recap in isolation.

    Returns a dict mapping cluster_id -> list of historical match dicts.
    """
    if not cluster_ids:
        return {}, {"clustersEnriched": 0}

    clusters_response = (
        supabase.table("clusters").select("id, symbol, embedding").in_("id", cluster_ids).execute()
    )

    enrichment_map: dict[str, list[dict]] = {}
    total_matches = 0

    for cluster in clusters_response.data:
        try:
            matches_response = supabase.rpc(
                "match_raw_items",
                {
                    "query_embedding": cluster["embedding"],
                    "match_symbol": cluster["symbol"],
                    "before_timestamp": run_started_at,
                    "match_count": MATCH_COUNT_PER_CLUSTER,
                },
            ).execute()
            matches = matches_response.data or []
        except Exception as err:
            # Non-fatal — a symbol with no history yet (e.g. first-ever run)
            # just gets an empty context list, draft node handles that fine.
            print(f"[enrich] similarity search failed for {cluster['symbol']}: {err}")
            enrichment_map[cluster["id"]] = []
            continue

        relevant = [m for m in matches if m.get("similarity", 0) >= MIN_SIMILARITY]
        enrichment_map[cluster["id"]] = relevant
        total_matches += len(relevant)

    summary = {
        "clustersEnriched": len(enrichment_map),
        "totalHistoricalMatches": total_matches,
    }
    return enrichment_map, summary
