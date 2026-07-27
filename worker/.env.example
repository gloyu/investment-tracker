from concurrent.futures import ThreadPoolExecutor

from nodes.ingest_prices import ingest_prices
from nodes.ingest_news import ingest_news


def ingest() -> dict:
    """
    Runs both ingestion sources for the current DAG run and merges their
    summaries into a single dag_steps output payload. Run in parallel
    threads since these are independent, I/O-bound (network) calls.
    """
    errors: list[str] = []
    price_summary = None
    news_summary = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        price_future = executor.submit(ingest_prices)
        news_future = executor.submit(ingest_news)

        try:
            price_summary = price_future.result()
        except Exception as err:
            errors.append(f"price ingestion failed: {err}")

        try:
            news_summary = news_future.result()
        except Exception as err:
            errors.append(f"news ingestion failed: {err}")

    # If BOTH sources failed outright, treat the whole step as failed —
    # a partial result (one source down) is still useful and shouldn't
    # block the rest of the pipeline.
    if price_summary is None and news_summary is None:
        raise RuntimeError(f"Both ingestion sources failed: {'; '.join(errors)}")

    return {"price": price_summary, "news": news_summary, "errors": errors}
