import json
import posixpath
import re
import shlex
import subprocess
from pathlib import Path
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


def read_remote_config_file(config_path: str) -> dict[str, Any]:
    """Read a config file from the configured remote repo for reproducibility snapshots.

    This is intentionally best-effort. Callers should store the returned error
    rather than fail run creation when the config cannot be read.
    """
    normalized_path = config_path.strip()

    if not normalized_path:
        return {
            "path": config_path,
            "source": "remote_ssh",
            "content": None,
            "error": "No config path provided",
        }

    if normalized_path.startswith("/") or ".." in normalized_path.split("/"):
        return {
            "path": config_path,
            "source": "remote_ssh",
            "content": None,
            "error": "Config path must be relative to the remote repo",
        }

    script = f"""
set -e
cd {shlex.quote(M3_REPO_PATH)}
CONFIG_PATH={shlex.quote(normalized_path)}
if [ ! -f "$CONFIG_PATH" ]; then
  echo "Config file not found: $CONFIG_PATH" >&2
  exit 44
fi
cat "$CONFIG_PATH"
""".strip()

    code, stdout, stderr = run_ssh_command(f"bash -lc {shlex.quote(script)}")

    if code != 0:
        return {
            "path": config_path,
            "source": "remote_ssh",
            "content": None,
            "error": stderr or f"Failed to read remote config file {config_path}",
        }

    return {
        "path": config_path,
        "source": "remote_ssh",
        "content": stdout,
        "error": None,
    }

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

def ensure_config_on_cluster(config_path: str) -> None:
    """If config_path matches a locally saved generated config, SCP it to the cluster.

    config_path is relative to the repo root (e.g. configs/generated/foo.yaml).
    Only acts when a matching local file exists — pre-existing cluster configs are left alone.
    """
    from app.services.config_gen import copy_config_to_cluster

    local_dir = Path(settings.TAP_LOCAL_CONFIG_DIR).resolve()
    local_file = local_dir / Path(config_path).name

    if not local_file.exists():
        return

    copy_config_to_cluster(
        str(local_file),
        cluster_host=settings.TAP_M3_HOST,
        remote_repo_path=M3_REPO_PATH,
        relative_config_path=config_path,
    )


def build_remote_launch_command(
    *,
    run_name: str,
    run_id: str,
    git_commit: str,
    config_path: str,
    config_overrides: dict[str, Any] | None = None,
    submit_script: str | None = None,
) -> str:
    submit_script = submit_script or settings.TAP_M3_SUBMIT_SCRIPT
    overrides_json = json.dumps(config_overrides or {}, ensure_ascii=False)
    tap_api_url = settings.TAP_API_URL

    script = f"""
        set -e
        cd {shlex.quote(M3_REPO_PATH)}
        export TAP_GIT_COMMIT={shlex.quote(git_commit)}
        export CONFIG_PATH={shlex.quote(config_path)}
        export CONFIG_OVERRIDES_JSON={shlex.quote(overrides_json)}
        export TAP_RUN_NAME={shlex.quote(run_name)}
        export TAP_RUN_ID={shlex.quote(run_id)}
        export TAP_API_URL={shlex.quote(tap_api_url)}
        sbatch --job-name={shlex.quote(run_name)} --export=ALL {shlex.quote(submit_script)}
    """.strip()

    return f"bash -lc {shlex.quote(script)}"


def resolve_remote_training_git_commit() -> tuple[str | None, str | None]:
    from app.config import settings
    remote_repo_path = settings.TAP_M3_REPO_PATH

    if not remote_repo_path:
        return None, "settings.TAP_M3_REPO_PATH is empty"

    command = f"cd {shlex.quote(remote_repo_path)} && git rev-parse HEAD"
    code, stdout, stderr = run_ssh_command(command)

    if code != 0:
        return None, stderr or f"Remote git command failed with exit code {code}"

    commit = stdout.strip()
    if not commit:
        return None, "Remote git command succeeded but returned empty stdout"

    return commit, None


def build_remote_log_path(run_name: str, slurm_job_id: str) -> str:
    filename = f"{run_name}-{slurm_job_id}.out"
    return posixpath.join(M3_REPO_PATH, "logs/slurm", filename)

def build_remote_error_log_path(run_name: str, slurm_job_id: str) -> str:
    filename = f"{run_name}-{slurm_job_id}.err"
    return posixpath.join(M3_REPO_PATH, "logs/slurm", filename)

def launch_training_run(
    *,
    run_name: str,
    run_id: str,
    git_commit: str,
    config_path: str,
    config_overrides: dict[str, Any] | None = None,
    submit_script: str | None = None,
) -> tuple[int, str, str, str | None, str]:
    ensure_config_on_cluster(config_path)
    remote_command = build_remote_launch_command(
        run_name=run_name,
        run_id=run_id,
        git_commit=git_commit,
        config_path=config_path,
        config_overrides=config_overrides,
        submit_script=submit_script,
    )

    code, stdout, stderr = run_ssh_command(remote_command)
    combined_output = "\n".join(part for part in [stdout, stderr] if part)
    job_id = parse_slurm_job_id(combined_output)

    return code, stdout, stderr, job_id, remote_command



def launch_direct_run(
    *,
    run_name: str,
    run_id: str,
    git_commit: str,
    config_path: str,
    config_overrides: dict[str, Any] | None = None,
    max_steps: int = 50,
) -> tuple[int, str, str, int | None, str | None, str]:
    """
    Launch a training script directly on M3 via SSH without SLURM.
    Uses nohup so the process survives if the SSH connection drops.
    Returns (exit_code, stdout, stderr, pid, log_path).
    """
    ensure_config_on_cluster(config_path)
    import json as _json
    overrides_json = _json.dumps(config_overrides or {}, ensure_ascii=False)
    log_path = posixpath.join(
        M3_REPO_PATH, "logs/direct", f"{run_name}.out"
    )

    conda_env = settings.TAP_M3_CONDA_ENV
    script = f"""
set -e
cd {shlex.quote(M3_REPO_PATH)}
mkdir -p logs/direct
export TAP_GIT_COMMIT={shlex.quote(git_commit)}
export CONFIG_PATH={shlex.quote(config_path)}
export CONFIG_OVERRIDES_JSON={shlex.quote(overrides_json)}
export TAP_RUN_NAME={shlex.quote(run_name)}
export TAP_RUN_ID={shlex.quote(run_id)}
export TAP_API_URL={shlex.quote(settings.TAP_API_URL)}
module load miniforge3
conda activate {shlex.quote(conda_env)}
nohup torchrun --nproc_per_node=1 -m src.slm.main \\
    --config {shlex.quote(config_path)} \\
    > {shlex.quote(log_path)} 2>&1 &
echo $!
""".strip()

    full_command = f"bash -lc {shlex.quote(script)}"
    code, stdout, stderr = run_ssh_command(full_command)

    pid: int | None = None
    if code == 0 and stdout.strip().isdigit():
        pid = int(stdout.strip())

    return code, stdout, stderr, pid, log_path, full_command


def poll_direct_process(pid: int) -> str:
    """
    Check if a direct (non-SLURM) process is still running on M3.
    Returns TAP status: 'running', 'completed', or 'failed'.
    """
    code, stdout, _ = run_ssh_command(f"ps -p {pid} -o pid= 2>/dev/null")
    if code == 0 and stdout.strip():
        return "running"

    # Process is gone — check exit code via wait (won't work for nohup)
    # Fall back to: check if log has error markers
    log_code, log_out, _ = run_ssh_command(
        f"tail -5 $(ls {shlex.quote(posixpath.join(M3_REPO_PATH, 'logs/direct'))}/*.out 2>/dev/null | tail -1) 2>/dev/null || true"
    )
    if "Error" in log_out or "Traceback" in log_out:
        return "failed"
    return "completed"
