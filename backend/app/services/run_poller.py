import asyncio
import logging
import os
from typing import Any

from app.db import get_db

# M1 shortcut:
# Reuse the existing API refresh function so manual refresh and auto refresh behave the same.
# Later, this can be cleaned up by extracting refresh_run into a pure service function.
from app.api.runs import refresh_run


logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {"created", "queued", "running", "unknown"}


def list_refreshable_run_ids() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT run_id, status, slurm_job_id, wandb_run_id
            FROM runs
            WHERE status IN (?, ?, ?, ?)
            ORDER BY datetime(created_at) ASC
            """,
            tuple(ACTIVE_STATUSES),
        ).fetchall()

    run_ids: list[str] = []

    for row in rows:
        item = dict(row)

        # Skip runs that have nothing external to refresh yet.
        # Example: launch_now=false with no Slurm/W&B ID.
        if not item.get("slurm_job_id") and not item.get("wandb_run_id"):
            continue

        run_ids.append(item["run_id"])

    return run_ids


async def refresh_active_runs_once() -> dict[str, Any]:
    run_ids = list_refreshable_run_ids()

    result: dict[str, Any] = {
        "checked": len(run_ids),
        "succeeded": 0,
        "failed": 0,
        "errors": [],
    }

    for run_id in run_ids:
        try:
            # refresh_run is sync and may call SSH/SQLite,
            # so run it off the event loop.
            await asyncio.to_thread(refresh_run, run_id)
            result["succeeded"] += 1
        except Exception as exc:
            result["failed"] += 1
            result["errors"].append({"run_id": run_id, "error": str(exc)})
            logger.exception("Failed to refresh run %s", run_id)

    return result


async def poll_active_runs() -> None:
    interval_seconds = int(os.getenv("TAP_RUN_REFRESH_INTERVAL_SECONDS", "15"))

    logger.info(
        "Starting TAP run refresh poller with interval=%ss",
        interval_seconds,
    )

    while True:
        try:
            result = await refresh_active_runs_once()
            if result["checked"]:
                logger.info("Run refresh poll result: %s", result)
        except Exception:
            logger.exception("Run refresh poller crashed during refresh cycle")

        await asyncio.sleep(interval_seconds)