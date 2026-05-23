from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Template:
    template_id: str
    name: str
    description: str
    created_at: str
    params: dict[str, Any] = field(default_factory=dict)
    run_count: int = 0

    @classmethod
    def from_row(cls, row: Any) -> Template:
        d = dict(row)
        raw = d.get("params_json")
        params: dict[str, Any] = {}
        if raw:
            try:
                params = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                params = {}
        return cls(
            template_id=d["template_id"],
            name=d["name"],
            description=d.get("description", ""),
            created_at=d["created_at"],
            params=params,
            run_count=d.get("run_count", 0),
        )


@dataclass
class TemplateRun:
    id: str
    template_id: str
    run_id: str
    combo_index: int

    @classmethod
    def from_row(cls, row: Any) -> TemplateRun:
        d = dict(row)
        return cls(
            id=d["id"],
            template_id=d["template_id"],
            run_id=d["run_id"],
            combo_index=d.get("combo_index", 0),
        )
