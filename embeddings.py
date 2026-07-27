import json
import re

from anthropic import Anthropic

from lib.supabase_client import supabase

anthropic_client = Anthropic()  # reads ANTHROPIC_API_KEY from env automatically

# This is the guardrail: the prompt explicitly forbids opinion/prediction
# content, matching the v1 scope decision (facts only, phase 2 adds
# opinionated analysis behind human review later).
SYSTEM_PROMPT = """You are a financial news summarizer. Your job is to write short, strictly factual recap sections for a stock/index watchlist.

Rules you must follow:
- State only facts that are directly supported by the provided source material (today's data and/or historical context).
- Do NOT make predictions, forecasts, or statements about future performance.
- Do NOT give buy/sell/hold recommendations or any investment advice.
- Do NOT editorialize, speculate on causes not stated in the sources, or use promotional language.
- If historical context is provided, you may note factual patterns (e.g. "this is the third consecutive day of gains") but do not interpret what it means for the future.
- If source material is thin or unclear, keep the section short rather than filling in unsupported claims.

Respond ONLY with a JSON object in this exact shape, no other text:
{
  "headline": "short factual headline, under 12 words",
  "body": "2-3 sentences, strictly factual",
  "metrics": { "key": "value" }
}
The metrics object should pull out 1-4 concrete numbers mentioned in the source material (e.g. price, % change, volume) as simple key-value string pairs."""


def _get_cluster_content(item_ids: list[str]) -> list[dict]:
    """Fetches the raw_items content for a cluster's item_ids."""
    response = supabase.table("raw_items").select("id, content, source").in_("id", item_ids).execute()
    return response.data or []


def _draft_section_for_cluster(cluster: dict, enrichment_map: dict[str, list[dict]]) -> dict | None:
    """Drafts one section for a single cluster via the Anthropic API."""
    items = _get_cluster_content(cluster["item_ids"])
    if not items:
        return None

    todays_facts = "\n".join(f"- [{item['source']}] {item['content']}" for item in items)

    historical_matches = enrichment_map.get(cluster["id"], [])
    historical_context = "\n".join(
        f"- [{m['published_at']}] {m['content']}" for m in historical_matches
    )

    if historical_context:
        history_block = (
            f"Historical context (for pattern reference only, do not predict from this):\n{historical_context}"
        )
    else:
        history_block = "No historical context available yet for this symbol."

    user_prompt = f"""Symbol: {cluster['symbol']}

Today's facts:
{todays_facts}

{history_block}

Write the recap section as instructed."""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text_block = next((b for b in response.content if b.type == "text"), None)
    if not text_block:
        raise RuntimeError(f"No text response from draft call for {cluster['symbol']}")

    # Model is instructed to return raw JSON only, but strip code-fence
    # wrapping defensively in case it adds one anyway.
    cleaned = re.sub(r"```json\n?|```", "", text_block.text).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Failed to parse draft JSON for {cluster['symbol']}: {text_block.text}") from err

    return {
        "symbol": cluster["symbol"],
        "headline": parsed["headline"],
        "body": parsed["body"],
        "metrics": parsed.get("metrics", {}),
        "source_item_ids": cluster["item_ids"],
    }


def draft_sections(cluster_ids: list[str], enrichment_map: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    """
    Drafts a report section for every cluster from this run.
    Runs sequentially to stay within reasonable API rate limits and
    keep error attribution per-symbol clear in logs.
    """
    if not cluster_ids:
        return [], {"sectionsDrafted": 0}

    clusters_response = (
        supabase.table("clusters").select("id, symbol, item_ids").in_("id", cluster_ids).execute()
    )

    sections: list[dict] = []
    errors: list[str] = []

    for cluster in clusters_response.data:
        try:
            section = _draft_section_for_cluster(cluster, enrichment_map)
            if section:
                sections.append(section)
        except Exception as err:
            errors.append(f"{cluster['symbol']}: {err}")

    summary = {"sectionsDrafted": len(sections), "errors": errors}
    return sections, summary
