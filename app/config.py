import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    TAP_DB_PATH: str = os.environ.get("TAP_DB_PATH", "data/tap.db")
    TAP_M3_HOST: str = os.environ.get("TAP_M3_HOST", "m3")
    TAP_M3_REPO_PATH: str = os.environ.get("TAP_M3_REPO_PATH", "~/slm_repo")
    TAP_GIT_REMOTE: str = os.environ.get("TAP_GIT_REMOTE", "origin")
    TAP_M3_SUBMIT_SCRIPT: str = os.environ.get("TAP_M3_SUBMIT_SCRIPT", "slurm/train.sh")
    TAP_M3_LOG_DIR: str = os.environ.get("TAP_M3_LOG_DIR", "logs/slurm")

    WANDB_ENTITY: str = os.environ.get("WANDB_ENTITY", "")
    WANDB_PROJECT: str = os.environ.get("WANDB_PROJECT", "")
    WANDB_API_KEY: str = os.environ.get("WANDB_API_KEY", "")


settings = Settings()