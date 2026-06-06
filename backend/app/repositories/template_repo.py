from __future__ import annotations

import json

from app.models.template import Template, TemplateRun
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository):

    def find(self, template_id: str) -> Template | None:
        row = self._conn.execute(
            """
            SELECT t.*,
                   (SELECT COUNT(*) FROM template_runs tr WHERE tr.template_id = t.template_id) AS run_count
            FROM templates t
            WHERE t.template_id = ?
            """,
            (template_id,),
        ).fetchone()
        return Template.from_row(row) if row else None

    def list_all(self) -> list[Template]:
        rows = self._conn.execute(
            """
            SELECT t.*,
                   (SELECT COUNT(*) FROM template_runs tr WHERE tr.template_id = t.template_id) AS run_count
            FROM templates t
            ORDER BY datetime(t.created_at) DESC
            """
        ).fetchall()
        return [Template.from_row(r) for r in rows]

    def create(self, template: Template) -> Template:
        self._conn.execute(
            """
            INSERT INTO templates (template_id, name, description, params_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                template.template_id,
                template.name,
                template.description,
                json.dumps(template.params, ensure_ascii=False),
                template.created_at,
            ),
        )
        return self.find(template.template_id)  # type: ignore[return-value]

    def list_runs(self, template_id: str) -> list[TemplateRun]:
        rows = self._conn.execute(
            "SELECT * FROM template_runs WHERE template_id = ? ORDER BY combo_index ASC",
            (template_id,),
        ).fetchall()
        return [TemplateRun.from_row(r) for r in rows]

    def add_run(self, template_run: TemplateRun) -> None:
        self._conn.execute(
            "INSERT INTO template_runs (id, template_id, run_id, combo_index) VALUES (?, ?, ?, ?)",
            (template_run.id, template_run.template_id, template_run.run_id, template_run.combo_index),
        )

    def find_pending_runs(self, cap: int) -> list[dict]:
        """Return created template runs that are under the per-template concurrency cap."""
        rows = self._conn.execute(
            """
            SELECT
                r.run_id, r.name, r.git_commit, r.config_path, r.template_id,
                r.wandb_run_id,
                (
                    SELECT COUNT(*) FROM runs r2
                    WHERE r2.template_id = r.template_id
                      AND r2.status IN ('queued', 'running')
                ) AS active_count
            FROM runs r
            WHERE r.status = 'created' AND r.template_id IS NOT NULL
            ORDER BY r.template_id, r.created_at ASC
            """
        ).fetchall()

        slots_used: dict[str, int] = {}
        to_promote: list[dict] = []
        for row in rows:
            tid: str = row["template_id"]
            if tid not in slots_used:
                slots_used[tid] = row["active_count"]
            if slots_used[tid] >= cap:
                continue
            to_promote.append(dict(row))
            slots_used[tid] += 1
        return to_promote
