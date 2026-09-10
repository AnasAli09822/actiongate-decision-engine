from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.audit import get_audit, init_db
from app.engine.service import evaluate
from app.schemas import DecisionRequest, DecisionResponse, Scenario
from app.scenarios import get_scenario, get_scenarios

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ActionGate",
    version="2.0.0",
    description="A context-aware decision layer for consequential AI agent actions.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@app.get("/api/scenarios", response_model=list[Scenario])
def scenarios() -> list[Scenario]:
    return get_scenarios()


@app.get("/api/scenarios/{scenario_id}", response_model=Scenario)
def scenario(scenario_id: str) -> Scenario:
    value = get_scenario(scenario_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return value


@app.post("/api/decisions/evaluate", response_model=DecisionResponse)
def evaluate_decision(request: DecisionRequest) -> DecisionResponse:
    return evaluate(request)


@app.post("/api/scenarios/{scenario_id}/run", response_model=DecisionResponse)
def run_scenario(scenario_id: str) -> DecisionResponse:
    value = get_scenario(scenario_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return evaluate(value.request)


@app.get("/api/decisions/{decision_id}/audit")
def audit(decision_id: str) -> dict:
    trail = get_audit(decision_id)
    if trail is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return trail
