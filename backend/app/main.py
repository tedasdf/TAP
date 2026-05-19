import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.api.runs import router as runs_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.api.notifications import router as notifications_router
from app.api.system import router as system_router
from app.services.background_worker import start_background_worker, stop_background_worker
from app.api.configs import router as config_router

DB_PATH = Path(os.environ.get("TAP_DB_PATH", "tap.db"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    start_background_worker()

@app.on_event("shutdown")
async def shutdown():
    await stop_background_worker()
    
app.include_router(system_router)
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(notifications_router)
app.include_router(config_router)