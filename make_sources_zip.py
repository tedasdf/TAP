from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

include_paths = [
    "backend",
    "frontend",
    "configs",
    "scripts",
    "docker-compose.yml",
    "Dockerfile",
    "package.json",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "README.md",
    ".env.example",
]

exclude_parts = {
    "node_modules",
    "venv",
    ".venv",
    ".tap_venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".git",
    "dist",
    "build",
    ".next",
    "logs",
    "wandb",
    "checkpoints",
    "artifacts",
    "data",
    "generated_configs",
}

exclude_suffixes = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".key",
    ".pem",
    ".zip",
}

exclude_names = {
    ".env",
}

zip_name = f"tap_sources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
zip_path = ROOT / zip_name


def should_exclude(path: Path) -> bool:
    rel_parts = set(path.relative_to(ROOT).parts)

    if rel_parts & exclude_parts:
        return True

    if path.name in exclude_names:
        return True

    if path.suffix in exclude_suffixes:
        return True

    return False


with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for item in include_paths:
        path = ROOT / item

        if not path.exists():
            continue

        if path.is_file():
            if not should_exclude(path):
                zf.write(path, path.relative_to(ROOT))
            continue

        for file_path in path.rglob("*"):
            if file_path.is_file() and not should_exclude(file_path):
                zf.write(file_path, file_path.relative_to(ROOT))

print(f"Done: {zip_path}")