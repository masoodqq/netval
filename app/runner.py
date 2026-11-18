"""Runs a test plan against many devices in parallel.

Per device: connect -> provision (push config) -> collect facts -> validate.
A failure on one device is recorded and never stops the others, which is
what you want on a production line.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

from . import db
from .checks import run_checks
from .drivers.mock import MockDriver

log = logging.getLogger("netval.runner")
MAX_WORKERS = int(os.getenv("NETVAL_WORKERS", "16"))


def get_driver(kind: str):
    if kind == "mock":
        return MockDriver
    if kind == "eos":
        from .drivers.eos import EOSDriver  # imported lazily so mock mode needs no netmiko
        return EOSDriver
    raise ValueError(f"unknown driver: {kind}")


def validate_device(host: str, plan: dict, driver_cls, retries: int = 2) -> dict:
    start = time.monotonic()
    result = {"host": host, "passed": False, "checks": []}
    for attempt in range(1, retries + 2):
        try:
            with driver_cls(host, plan.get("username", "admin"), plan.get("password", "admin")) as dev:
                if plan.get("config"):
                    dev.push_config(plan["config"])
                facts = dev.get_facts()
                result["serial"] = facts.get("serial")
                result["checks"] = run_checks(facts, plan)
                result["passed"] = all(c["passed"] for c in result["checks"])
                result.pop("error", None)
                break
        except Exception as e:
            log.warning("%s attempt %d failed: %s", host, attempt, e)
            result["error"] = str(e)
            time.sleep(0.2 * attempt)
    result["duration_s"] = round(time.monotonic() - start, 2)
    return result


def execute_run(run_id: int, hosts: list[str], plan: dict) -> None:
    driver_cls = get_driver(plan.get("driver", "mock"))
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for r in pool.map(lambda h: validate_device(h, plan, driver_cls), hosts):
            db.add_result(run_id, r)
            log.info("%s %s", r["host"], "PASS" if r["passed"] else "FAIL")
    run = db.get_run(run_id)
    db.finish_run(run_id, "passed" if run["summary"]["failed"] == 0 else "failed")
