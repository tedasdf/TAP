import asyncio
import os
from datetime import datetime, timezone
from typing import Any
from app.db import get_db
from app.services.run_refresh import (
    create_notification_row,
    create_run_event,
    list_active_run_ids,
    refresh_run_by_id,
)

_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None

_worker_state: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "interval_seconds": 60,
    "last_cycle_started_at": None,
    "last_cycle_finished_at": None,
    "last_cycle_run_count": 0,
    "last_cycle_error_count": 0,
    "last_error": None,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def get_refresh_interval_seconds() -> int:
    value = os.environ.get("TAP_BACKGROUND_REFRESH_INTERVAL_SECONDS", "60")

    try:
        return max(10, int(value))
    except ValueError:
        return 60


def is_background_refresh_enabled() -> bool:
    return env_bool("TAP_BACKGROUND_REFRESH_ENABLED", default=False)


def get_background_worker_status() -> dict[str, Any]:
    return dict(_worker_state)


async def run_background_refresh_cycle() -> None:
    _worker_state["last_cycle_started_at"] = utc_now_iso()
    _worker_state["last_cycle_run_count"] = 0
    _worker_state["last_cycle_error_count"] = 0
    _worker_state["last_error"] = None

    run_ids = list_active_run_ids()
    _worker_state["last_cycle_run_count"] = len(run_ids)

    for run_id in run_ids:
        try:
            refresh_run_by_id(run_id)
        except Exception as exc:
            _worker_state["last_cycle_error_count"] += 1
            _worker_state["last_error"] = f"{run_id}: {exc}"

            try:
                record_background_refresh_failure(
                    run_id=run_id,
                    error=exc,
                )
            except Exception as record_exc:
                _worker_state["last_error"] = (
                    f"{run_id}: {exc}; failed to record worker error: {record_exc}"
                )

    _worker_state["last_cycle_finished_at"] = utc_now_iso()


async def background_refresh_loop(stop_event: asyncio.Event) -> None:
    interval_seconds = get_refresh_interval_seconds()

    _worker_state["enabled"] = True
    _worker_state["running"] = True
    _worker_state["interval_seconds"] = interval_seconds

    try:
        while not stop_event.is_set():
            await run_background_refresh_cycle()

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    finally:
        _worker_state["running"] = False


def start_background_worker() -> None:
    global _worker_task, _stop_event

    if not is_background_refresh_enabled():
        _worker_state["enabled"] = False
        _worker_state["running"] = False
        _worker_state["interval_seconds"] = get_refresh_interval_seconds()
        return

    if _worker_task is not None and not _worker_task.done():
        return

    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(background_refresh_loop(_stop_event))


async def stop_background_worker() -> None:
    global _worker_task, _stop_event

    if _stop_event is not None:
        _stop_event.set()

    if _worker_task is not None:
        try:
            await asyncio.wait_for(_worker_task, timeout=5)
        except asyncio.TimeoutError:
            _worker_task.cancel()

    _worker_task = None
    _stop_event = None


def background_failure_notification_exists(
    conn,
    *,
    run_id: str,
    message: str,
) -> bool:
    row = conn.execute(
        """
        SELECT notification_id
        FROM notifications
        WHERE run_id = ?
          AND event_type = ?
          AND message = ?
        LIMIT 1
        """,
        (run_id, "background_refresh_failed", message),
    ).fetchone()

    return row is not None


def record_background_refresh_failure(
    *,
    run_id: str,
    error: Exception,
) -> None:
    error_message = str(error)
    message = f"Background refresh failed for run {run_id}: {error_message}"

    with get_db() as conn:
        create_run_event(
            conn,
            run_id=run_id,
            event_type="BACKGROUND_REFRESH_FAILED",
            message=message,
            payload={
                "error": error_message,
                "source": "background_worker",
            },
        )

        if background_failure_notification_exists(
            conn,
            run_id=run_id,
            message=message,
        ):
            return

        create_notification_row(
            conn,
            event_type="background_refresh_failed",
            severity="warning",
            title="Background refresh failed",
            message=message,
            run_id=run_id,
        )