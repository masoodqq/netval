"""Validation checks. Each takes (facts, plan) and returns (passed, detail).

Add a new check by writing a function and registering it in CHECKS.
"""
from typing import Callable

Result = tuple[bool, str]


def check_firmware(facts: dict, plan: dict) -> Result:
    want = plan["expected_version"]
    got = facts["version"]
    return got == want, f"expected {want}, found {got}"


def check_interfaces_up(facts: dict, plan: dict) -> Result:
    down = [
        name for name in plan.get("required_interfaces", [])
        if facts["interfaces"].get(name, {}).get("status") != "up"
    ]
    return not down, f"down/missing: {down}" if down else "all required interfaces up"


def check_interface_speed(facts: dict, plan: dict) -> Result:
    want = plan.get("min_speed_gbps", 0)
    slow = [
        f"{n}={facts['interfaces'][n]['speed_gbps']}G"
        for n in plan.get("required_interfaces", [])
        if n in facts["interfaces"] and facts["interfaces"][n]["speed_gbps"] < want
    ]
    return not slow, f"below {want}G: {slow}" if slow else f"all >= {want}G"


def check_vlans(facts: dict, plan: dict) -> Result:
    missing = sorted(set(plan.get("required_vlans", [])) - set(facts["vlans"]))
    return not missing, f"missing VLANs: {missing}" if missing else "all VLANs present"


def check_lldp(facts: dict, plan: dict) -> Result:
    want = plan.get("min_lldp_neighbors", 0)
    got = len(facts["lldp_neighbors"])
    return got >= want, f"{got} neighbors (need >= {want})"


CHECKS: dict[str, Callable[[dict, dict], Result]] = {
    "firmware_version": check_firmware,
    "interfaces_up": check_interfaces_up,
    "interface_speed": check_interface_speed,
    "vlans_present": check_vlans,
    "lldp_neighbors": check_lldp,
}


def run_checks(facts: dict, plan: dict) -> list[dict]:
    results = []
    for name, fn in CHECKS.items():
        try:
            passed, detail = fn(facts, plan)
        except Exception as e:  # a broken check must never crash the run
            passed, detail = False, f"check error: {e}"
        results.append({"check": name, "passed": passed, "detail": detail})
    return results
