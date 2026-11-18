from app.checks import run_checks

PLAN = {
    "expected_version": "4.32.0F",
    "required_interfaces": ["Ethernet1", "Ethernet2"],
    "min_speed_gbps": 100,
    "required_vlans": [10, 20],
    "min_lldp_neighbors": 1,
}


def good_facts():
    return {
        "version": "4.32.0F",
        "interfaces": {
            "Ethernet1": {"status": "up", "speed_gbps": 100},
            "Ethernet2": {"status": "up", "speed_gbps": 100},
        },
        "vlans": [1, 10, 20],
        "lldp_neighbors": [{"local": "Ethernet1", "neighbor": "spine1", "port": "Ethernet1"}],
    }


def by_name(results):
    return {r["check"]: r["passed"] for r in results}


def test_healthy_switch_passes_everything():
    assert all(by_name(run_checks(good_facts(), PLAN)).values())


def test_wrong_firmware_fails():
    f = good_facts()
    f["version"] = "4.30.1F"
    assert by_name(run_checks(f, PLAN))["firmware_version"] is False


def test_link_down_fails():
    f = good_facts()
    f["interfaces"]["Ethernet2"]["status"] = "down"
    assert by_name(run_checks(f, PLAN))["interfaces_up"] is False


def test_missing_interface_fails():
    f = good_facts()
    del f["interfaces"]["Ethernet2"]
    assert by_name(run_checks(f, PLAN))["interfaces_up"] is False


def test_missing_vlan_fails():
    f = good_facts()
    f["vlans"] = [1, 10]
    assert by_name(run_checks(f, PLAN))["vlans_present"] is False


def test_broken_facts_do_not_crash():
    results = run_checks({}, PLAN)
    assert not any(r["passed"] for r in results)
