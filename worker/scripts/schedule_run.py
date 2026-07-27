"""
Meant to run as a one-off script, NOT as part of the long-running poll
loop in main.py. Deploy it as a separate Render Cron Job service (see
render.yaml) pointed at:
    python scripts/schedule_run.py
scheduled for e.g. "0 21 * * 1-5" (weekdays, after US market close).

It just creates a pending dag_runs row (+ its dag_steps) — the existing
worker's poll loop picks it up on its next tick, so there's no
duplication of pipeline logic here.
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from lib.dag_tracker import create_run


def main() -> None:
    run = create_run()
    print(f"Scheduled run created: {run['id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"Failed to schedule run: {err}")
        sys.exit(1)
