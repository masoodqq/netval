"""End-to-end API test using the mock driver (no hardware needed)."""
import os
import time

os.environ["NETVAL_DB"] = "test_netval.db"

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_module():
    if os.path.exists("test_netval.db"):
        os.remove("test_netval.db")
    db.init_db()


def wait_for(run_id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        run = client.get(f"/runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.1)
    raise TimeoutError


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_plan_404():
    assert client.post("/runs", json={"plan": "nope", "hosts": ["leaf1"]}).status_code == 404


def test_run_with_faults():
    hosts = ["leaf1", "leaf2", "leaf3-linkdown", "leaf4-badfw", "leaf5-unreachable"]
    r = client.post("/runs", json={"plan": "leaf_switch", "hosts": hosts})
    assert r.status_code == 202
    run = wait_for(r.json()["run_id"])

    assert run["status"] == "failed"
    assert run["summary"] == {"total": 5, "passed": 2, "failed": 3}
    results = {d["host"]: d for d in run["devices"]}
    assert results["leaf1"]["passed"]
    assert "timed out" in results["leaf5-unreachable"]["error"]
    failed = {c["check"] for c in results["leaf3-linkdown"]["checks"] if not c["passed"]}
    assert failed == {"interfaces_up"}
