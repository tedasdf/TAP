import os
from pathlib import Path

from fastapi import FastAPI

from app.db import init_db
from app.api.runs import router as runs_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.api.notifications import router as notifications_router
from app.api.system import router as system_router


DB_PATH = Path(os.environ.get("TAP_DB_PATH", "tap.db"))

app = FastAPI(title="TAP API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(system_router)
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(notifications_router)