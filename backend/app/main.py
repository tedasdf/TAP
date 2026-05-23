from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.api.runs import router as runs_router
from app.api.jobs import router as jobs_router
from app.api.metrics import router as metrics_router
from app.api.notifications import router as notifications_router
from app.api.system import router as system_router
from app.api.configs import router as config_router
from app.api.templates import router as templates_router
from app.api import registry
from app.services.orchestrator import orchestrator


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    orchestrator.start()


@app.on_event("shutdown")
async def shutdown():
    await orchestrator.stop()


app.include_router(system_router)
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(notifications_router)
app.include_router(config_router)
app.include_router(templates_router)
app.include_router(registry.router)
