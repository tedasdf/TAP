import json
import posixpath
import re
import shlex
import subprocess
from typing import Any

from app.config import settings


# Temporary hardcoded values for MVP.
# Later, move these fully back into config/.env if you want.
M3_REPO_PATH = settings.TAP_M3_REPO_PATH
M3_GIT_REMOTE = settings.TAP_GIT_REMOTE



def get_remote_git_state() -> dict[str, Any]:
    script = f"""
set -e
cd {shlex.quote(M3_REPO_PATH)}
COMMIT=$(git rev-parse HEAD)
BRANCH=$(git branch --show-current || true)
DIRTY=$(test -n "$(git status --porcelain)" && echo true || echo false)

printf '{{"commit":"%s","branch":"%s","dirty":%s}}' "$COMMIT" "$BRANCH" "$DIRTY"
""".strip()

    code, stdout, stderr = run_ssh_command(f"bash -lc {shlex.quote(script)}")

    if code != 0:
        raise RuntimeError(stderr or "Failed to read remote git state")

    return json.loads(stdout)

def parse_slurm_job_id(output: str) -> str | None:
    match = re.search(r"Submitted batch job\s+(\d+)", output)
    if match:
        return match.group(1)
    return None


def run_ssh_command(remote_command: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["ssh", settings.TAP_M3_HOST, remote_command],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()

def build_remote_launch_command(
    *,
    run_name: str,
    git_commit: str,
    config_path: str,
    config_overrides: dict[str, Any] | None = None,
    submit_script: str | None = None,
) -> str:
    submit_script = submit_script or settings.TAP_M3_SUBMIT_SCRIPT
    overrides_json = json.dumps(config_overrides or {}, ensure_ascii=False)

    script = f"""
        set -e
        cd {shlex.quote(M3_REPO_PATH)}
        export TAP_GIT_COMMIT={shlex.quote(git_commit)}
        export CONFIG_PATH={shlex.quote(config_path)}
        export CONFIG_OVERRIDES_JSON={shlex.quote(overrides_json)}
        export TAP_RUN_NAME={shlex.quote(run_name)}
        sbatch --job-name={shlex.quote(run_name)} {shlex.quote(submit_script)}
    """.strip()

    return f"bash -lc {shlex.quote(script)}"


def build_remote_log_path(run_name: str, slurm_job_id: str) -> str:
    filename = f"{run_name}-{slurm_job_id}.out"
    return posixpath.join(M3_REPO_PATH, "logs/slurm", filename)

def build_remote_error_log_path(run_name: str, slurm_job_id: str) -> str:
    filename = f"{run_name}-{slurm_job_id}.err"
    return posixpath.join(M3_REPO_PATH, "logs/slurm", filename)

def launch_training_run(
    *,
    run_name: str,
    git_commit: str,
    config_path: str,
    config_overrides: dict[str, Any] | None = None,
    submit_script: str | None = None,
) -> tuple[int, str, str, str | None]:
    remote_command = build_remote_launch_command(
        run_name=run_name,
        git_commit=git_commit,
        config_path=config_path,
        config_overrides=config_overrides,
        submit_script=submit_script,
    )

    code, stdout, stderr = run_ssh_command(remote_command)
    combined_output = "\n".join(part for part in [stdout, stderr] if part)
    job_id = parse_slurm_job_id(combined_output)

    return code, stdout, stderr, job_id