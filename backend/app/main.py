import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.services.template_queue import start_template_queue_worker
from app.api.runs import router as runs_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.api.notifications import router as notifications_router
from app.api.system import router as system_router
from app.api.configs import router as configs_router
from app.api.templates import router as templates_router


DB_PATH = Path(os.environ.get("TAP_DB_PATH", "tap.db"))

app = FastAPI()

_TAILSCALE_IP = os.environ.get("TAP_TAILSCALE_IP", "100.65.199.35")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        f"http://{_TAILSCALE_IP}:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_template_queue_worker()


app.include_router(system_router)
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(notifications_router)
app.include_router(configs_router)
app.include_router(templates_router)