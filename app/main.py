"""REST API for the network validation service.

  GET  /health            liveness probe
  GET  /plans             list available test plans
  POST /runs              start a run: {"plan": "leaf_switch", "hosts": [...]}
  GET  /runs              recent runs
  GET  /runs/{id}         run detail with per-device, per-check results
"""
import logging
from pathlib import Path

import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import db
from .runner import execute_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
PLAN_DIR = Path(__file__).resolve().parent.parent / "test_plans"

app = FastAPI(title="NetVal: Network Provisioning & Validation Service")
db.init_db()


class RunRequest(BaseModel):
    plan: str = Field(examples=["leaf_switch"])
    hosts: list[str] = Field(min_length=1, examples=[["leaf1", "leaf2", "leaf3-linkdown"]])


def load_plan(name: str) -> dict:
    path = PLAN_DIR / f"{name}.yaml"
    if not path.is_file() or path.parent != PLAN_DIR:
        raise HTTPException(404, f"plan '{name}' not found")
    return yaml.safe_load(path.read_text())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/plans")
def plans():
    return sorted(p.stem for p in PLAN_DIR.glob("*.yaml"))


@app.post("/runs", status_code=202)
def start_run(req: RunRequest, bg: BackgroundTasks):
    plan = load_plan(req.plan)
    run_id = db.create_run(req.plan)
    bg.add_task(execute_run, run_id, req.hosts, plan)
    return {"run_id": run_id, "status": "running", "devices": len(req.hosts)}


@app.get("/runs")
def runs():
    return db.list_runs()


@app.get("/runs/{run_id}")
def run_detail(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run
