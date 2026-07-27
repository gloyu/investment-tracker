from lib.supabase_client import supabase


def assemble_report(run_id: str, sections: list[dict]) -> tuple[str, dict]:
    """
    Writes the final assembled report for this run. Sections are ordered
    alphabetically by symbol for now — a more meaningful ordering (e.g.
    biggest movers first) can be added later without touching the schema.
    """
    ordered_sections = sorted(sections, key=lambda s: s["symbol"])

    response = (
        supabase.table("reports")
        .insert({"run_id": run_id, "sections": ordered_sections})
        .execute()
    )
    report = response.data[0]

    return report["id"], {"sectionCount": len(ordered_sections)}
