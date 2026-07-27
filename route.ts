from typing import Literal

DagRunStatus = Literal["pending", "running", "success", "failed"]
DagStepName = Literal["ingest", "cluster", "enrich", "draft", "assemble"]
DagStepStatus = Literal["pending", "running", "success", "failed", "skipped"]

# Ordered list of steps in the pipeline — used to know what "next" means
DAG_STEP_ORDER: list[DagStepName] = ["ingest", "cluster", "enrich", "draft", "assemble"]
