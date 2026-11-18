# NetVal: Network Provisioning & Validation Service

A Python microservice that provisions network switches, validates them against a
test plan, and records pass/fail results, the way a test station does on a
data center hardware manufacturing line.

```
 POST /runs ──► FastAPI ──► Runner (thread pool, 16 devices in parallel)
                   │              │
                   │              ├─ connect (SSH, with retries)
                   │              ├─ provision (push config from test plan)
                   │              ├─ collect facts (normalized JSON)
                   │              └─ run checks (firmware, links, speed, VLANs, LLDP)
                   ▼
               SQLite  ◄── per-device, per-check results, serial numbers, timing
```

**Stack:** Python, FastAPI, Netmiko, pytest, Docker, GitHub Actions, Containerlab (Arista cEOS)

## Quick start (no hardware needed)

```bash
pip install -r requirements.txt
pytest -v                                   # 9 tests
uvicorn app.main:app --reload               # API docs at http://localhost:8000/docs
```

Start a run against mock switches. Host names containing `linkdown`, `badfw` or
`unreachable` simulate failures:

```bash
curl -X POST localhost:8000/runs -H 'Content-Type: application/json' \
  -d '{"plan":"leaf_switch","hosts":["leaf1","leaf2","leaf3-linkdown","leaf4-badfw","leaf5-unreachable"]}'
curl localhost:8000/runs/1
```

With Docker: `docker compose up --build`

## Against real (virtual) switches

1. Install [Containerlab](https://containerlab.dev) and import the free Arista cEOS-lab image (see `lab/topology.clab.yml`).
2. `sudo containerlab deploy -t lab/topology.clab.yml`
3. Start a run with `"plan":"leaf_switch_ceos","hosts":["172.20.20.21","172.20.20.22"]`

## Project layout

| Path | What it does |
|---|---|
| `app/main.py` | REST API |
| `app/runner.py` | Parallel execution, retries, isolation of per-device failures |
| `app/checks.py` | Validation checks (add new ones to `CHECKS`) |
| `app/drivers/` | `base.py` interface, `mock.py` simulator, `eos.py` Arista driver |
| `app/db.py` | Result storage |
| `test_plans/` | YAML test plans: config to push + pass/fail limits |
| `lab/` | Containerlab topology |

## Roadmap: build these next

**Phase 2: more realistic testing**
- [ ] SONiC driver (SONiC-VS runs in Containerlab), so checks run unchanged on two vendors
- [ ] Traffic test: run `iperf3` between two hosts in the lab and check throughput against a limit
- [ ] Firmware upgrade step: if the version is wrong, upgrade, reboot, wait, re-check
- [ ] Config drift check: compare running config against the plan

**Phase 3: production-line features**
- [ ] Split into microservices: API service + worker service + Redis queue (Celery or RQ)
- [ ] PostgreSQL instead of SQLite; add a `units` table keyed by serial number for traceability
- [ ] Server checks over Redfish (BMC): fan, PSU, temperature, firmware. Use the DMTF Redfish mock server.
- [ ] Prometheus `/metrics` endpoint + Grafana dashboard for yield (pass rate) per plan and per station
- [ ] Export a test report (JSON/CSV) per serial number

**Phase 4: polish**
- [ ] Auth on the API (API key)
- [ ] Structured JSON logging with run ID and serial number on every line
- [ ] Load test: 500 mock devices, measure time per run, tune `NETVAL_WORKERS`
