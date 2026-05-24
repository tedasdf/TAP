from __future__ import annotations

import json

from app.models.metric import MetricPoint, MetricSnapshot, MetricSyncStatus
from app.repositories.base import BaseRepository


class MetricRepository(BaseRepository):

    def find_snapshot(self, run_id: str) -> MetricSnapshot | None:
        row = self._conn.execute(
            "SELECT * FROM metrics WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return MetricSnapshot.from_row(row) if row else None

    def upsert_snapshot(self, snapshot: MetricSnapshot) -> MetricSnapshot:
        self._conn.execute(
            """
            INSERT INTO metrics (
                run_id, current_step, current_epoch, training_loss,
                validation_loss, runtime, learning_rate, latest_metric_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            ON CONFLICT(run_id) DO UPDATE SET
                current_step           = excluded.current_step,
                current_epoch          = excluded.current_epoch,
                training_loss          = excluded.training_loss,
                validation_loss        = excluded.validation_loss,
                runtime                = excluded.runtime,
                learning_rate          = excluded.learning_rate,
                latest_metric_timestamp = excluded.latest_metric_timestamp
            """,
            (
                snapshot.run_id,
                snapshot.current_step,
                snapshot.current_epoch,
                snapshot.training_loss,
                snapshot.validation_loss,
                snapshot.runtime,
                snapshot.learning_rate,
                snapshot.latest_metric_timestamp,
            ),
        )
        row = self._conn.execute(
            "SELECT * FROM metrics WHERE run_id = ?",
            (snapshot.run_id,),
        ).fetchone()
        return MetricSnapshot.from_row(row)

    def add_point(self, point: MetricPoint) -> None:
        point_id   = point.point_id or self._new_id()
        created_at = point.created_at or self._utc_now()
        self._conn.execute(
            """
            INSERT INTO metric_points (point_id, run_id, step, epoch, source, metrics_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, step, source) DO UPDATE SET
                epoch        = excluded.epoch,
                metrics_json = excluded.metrics_json,
                created_at   = excluded.created_at
            """,
            (
                point_id,
                point.run_id,
                point.step,
                point.epoch,
                point.source,
                json.dumps(point.metrics, ensure_ascii=False),
                created_at,
            ),
        )

    def list_history(self, run_id: str, limit: int = 500) -> list[MetricPoint]:
        rows = self._conn.execute(
            """
            SELECT * FROM metric_points
            WHERE run_id = ?
            ORDER BY step ASC, created_at ASC
            LIMIT ?
            """,
            (run_id, limit),
        ).fetchall()
        return [MetricPoint.from_row(r) for r in rows]

    def get_best_validation_loss(self, run_id: str) -> float | None:
        row = self._conn.execute(
            """
            SELECT MIN(CAST(json_extract(metrics_json, '$.validation_loss') AS REAL)) AS best
            FROM metric_points
            WHERE run_id = ?
              AND json_extract(metrics_json, '$.validation_loss') IS NOT NULL
            """,
            (run_id,),
        ).fetchone()
        if row is None or row["best"] is None:
            return None
        try:
            return float(row["best"])
        except (TypeError, ValueError):
            return None

    def get_last_step(self, run_id: str, source: str) -> int | None:
        row = self._conn.execute(
            "SELECT MAX(step) AS s FROM metric_points WHERE run_id = ? AND source = ?",
            (run_id, source),
        ).fetchone()
        if row and row["s"] is not None:
            return int(row["s"])
        return None

    def count_points(self, run_id: str, source: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM metric_points WHERE run_id = ? AND source = ?",
            (run_id, source),
        ).fetchone()
        return int(row["c"]) if row else 0

    def find_sync_status(self, run_id: str) -> MetricSyncStatus | None:
        self._ensure_sync_status_table()
        row = self._conn.execute(
            "SELECT * FROM metric_sync_status WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return MetricSyncStatus.from_row(row) if row else None

    def upsert_sync_status(self, status: MetricSyncStatus) -> None:
        self._ensure_sync_status_table()
        self._conn.execute(
            """
            INSERT INTO metric_sync_status (
                run_id, source, status, last_started_at, last_finished_at,
                error_message, points_synced
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                source           = excluded.source,
                status           = excluded.status,
                last_started_at  = CASE
                    WHEN excluded.last_started_at IS NOT NULL
                    THEN excluded.last_started_at
                    ELSE metric_sync_status.last_started_at
                END,
                last_finished_at = CASE
                    WHEN excluded.last_finished_at IS NOT NULL
                    THEN excluded.last_finished_at
                    ELSE metric_sync_status.last_finished_at
                END,
                error_message    = excluded.error_message,
                points_synced    = excluded.points_synced
            """,
            (
                status.run_id,
                status.source,
                status.status,
                status.last_started_at,
                status.last_finished_at,
                status.error_message,
                status.points_synced,
            ),
        )

    def _ensure_sync_status_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_sync_status (
                run_id TEXT PRIMARY KEY,
                source TEXT,
                status TEXT NOT NULL,
                last_started_at TEXT,
                last_finished_at TEXT,
                error_message TEXT,
                points_synced INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
            """
        )
