# 🗺️ deadline-map

> A dependency-aware infrastructure deadline and blast-radius monitor engineered to track expiring certificates, domains, runtimes, tokens, and trials—and map each deadline to the services that break when it lapses.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61DAFB.svg?style=flat-square&logo=react&logoColor=black)
![DuckDB](https://img.shields.io/badge/Database-DuckDB-FFF000.svg?style=flat-square&logo=duckdb&logoColor=black)
![Pytest](https://img.shields.io/badge/Tests-Pytest-0A9EDC.svg?style=flat-square&logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF.svg?style=flat-square&logo=github-actions&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)

---

## 🎯 Overview

**deadline-map** solves a common operational blind spot in small-team and solo infrastructure: tracking expiration dates in isolation without knowing what actually breaks when they pass. Instead of checking scattered dashboards or guessing impact, `deadline-map` models resources (`tls_cert`, `domain`, `runtime`, `token`, `trial`) and the services that depend on them in a single `deadlines.yml` inventory. It validates definitions up front with Pydantic v2, evaluates automated and manual deadlines, computes priority and blast radius within a configurable lookahead window, records snapshots in DuckDB, exports Prometheus gauge metrics, dispatches Telegram/Discord alerts, and serves a dark-mode React dashboard via FastAPI.

---

## 💻 Development Environment

This project was natively engineered and tested in the following environment:

- **Operating System:** Arch Linux (Wayland / Hyprland)
- **Terminal Environment:** `sunraku` (ZSH / Foot)
- **Core Languages:** Python 3.14, Node.js
- **Package Management:** `pip` / `venv` (Backend), `npm` (Frontend)
- **Theme Palette:** Custom Deep Black (`#050505`) with Bright Red Accent (`#B21318`)

---

## 🚀 Installation & Execution

`deadline-map` includes a Python CLI, a FastAPI backend with Prometheus/JSON endpoints, a `systemd` timer for Linux, and a React + Vite web dashboard.

### Backend & CLI Setup

1. **Create and activate a virtual environment, then install in editable mode:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e "backend[dev]"

```

2. **Run the automated test suite (`pytest`):**

```bash
pytest -v

```

3. **Run a CLI status check (with optional DuckDB history and Prometheus metrics output):**

```bash
deadline-map status --file examples/deadlines.yml --offline
deadline-map status --file examples/deadlines.yml --offline --db snapshots.duckdb --metrics-out metrics.prom

```

### FastAPI Server & Web Dashboard Setup

1. **Start the FastAPI backend:**

```bash
deadline-map serve --file examples/deadlines.yml

```

2. **Start the React + Vite frontend in a separate terminal:**

```bash
cd frontend
npm install
npm run dev

```

3. **Access the application:**

* **Frontend Dashboard:** `http://localhost:5173`
* **Backend API & Swagger Docs:** `http://127.0.0.1:8000/docs`
* **Prometheus Metrics Endpoint:** `http://127.0.0.1:8000/metrics`

---

## 🏗️ System Architecture

```text
[ deadlines.yml Inventory ] ───────┐
                                   ▼
                     [ Pydantic v2 Schema Validator ]
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
     [ Automated Probes ]                [ Manual Deadlines ]
  (TLS ssl, RDAP, endoflife.date)        (Tokens, Trials, Rotation)
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
                 [ Blast-Radius & Priority Graph Engine ]
                 /                 │                 \
                ▼                  ▼                  ▼
   [ DuckDB Snapshots ]   [ Telegram/Discord ]  [ FastAPI + React UI ]
   [ Prometheus /metrics ]     [ Alerts ]       [ /api/status & /api/history ]

```

---

## 🛠️ Tech Stack

* **Backend API Framework:** `FastAPI` + `Uvicorn` (`/health`, `/api/status`, `/api/history`, `/metrics`)
* **CLI Framework:** `Typer` (`deadline-map status`, `deadline-map serve`, `deadline-map version`)
* **Schema & Validation:** `Pydantic` v2 + `PyYAML`
* **Probes & HTTP Client:** Python `ssl`/`socket`, `httpx` (`rdap.org` and `endoflife.date`)
* **History & Metrics:** `DuckDB` snapshots + Prometheus textfile/HTTP gauges
* **Testing:** `Pytest` + FastAPI `TestClient` (offline deterministic fixtures)
* **Frontend UI:** `React` + `Vite`
* **Automation & CI/CD:** `systemd` service/timer + `GitHub Actions` (`ubuntu-latest` + `windows-latest` matrix)

---

## 📂 Project Structure

```text
deadline-map/
├── backend/
│   ├── app/
│   │   ├── alerts/
│   │   │   └── notifier.py      # 30/14/7/1d alert rules + Telegram/Discord senders
│   │   ├── graph/
│   │   │   └── blast_radius.py  # Dependency mapping, criticality weights, priority scoring
│   │   ├── history/
│   │   │   └── store.py         # DuckDB snapshot persistence
│   │   ├── inventory/
│   │   │   ├── loader.py        # YAML inventory loader helpers
│   │   │   └── models.py        # Pydantic models & cross-reference validation
│   │   ├── probes/
│   │   │   ├── domain_rdap.py   # RDAP domain expiration probe
│   │   │   ├── models.py        # ProbeResult & threshold classification
│   │   │   ├── runtime_eol.py   # endoflife.date runtime lifecycle probe
│   │   │   └── tls_cert.py      # TLS certificate expiration probe
│   │   ├── cli.py               # Typer CLI entry point
│   │   ├── main.py              # FastAPI application factory & routes
│   │   └── metrics.py           # Prometheus gauge exporter
│   ├── tests/                   # Pytest unit and API test suite
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Blast-radius summary cards & dependency timeline UI
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── examples/
│   └── deadlines.yml            # Sample resource + service dependency inventory
├── systemd/
│   ├── deadline-map.service     # Oneshot systemd unit
│   └── deadline-map.timer       # Daily scheduled timer
├── .github/workflows/ci.yml     # Cross-platform Python (Linux/Windows) + Vite build CI
├── .gitignore
├── LICENSE                      # MIT License
└── README.md

```

---

## 🚀 Key Features

* **Dependency-First Blast Radius:** Connects each expiring resource to specific dependent services, criticality levels (`low`, `medium`, `high`), outage impacts, and renewal hints.
* **Strict Inventory Validation:** Catches duplicate IDs, missing kind-specific fields, invalid threshold ranges, and references to undefined resources before checks run.
* **Offline-Testable Probes & Alerts:** Supports injectable fetchers and senders so unit tests run deterministically offline while live runs query TLS, RDAP, `endoflife.date`, Telegram, and Discord.
* **DuckDB History & Prometheus Metrics:** Stores periodic snapshots in DuckDB and exposes `deadline_map_services_at_risk`, `deadline_map_deadlines_in_window`, `deadline_map_days_remaining`, and `deadline_map_priority_score`.
* **Cross-Platform CI & Zero-Cost Stack:** Tested on both `ubuntu-latest` and `windows-latest` in GitHub Actions with free/open-source tools and zero cloud billing requirements.

---

## ⚙️ Custom Tweaks & Architecture Decisions

* **Single DuckDB Store:** Uses DuckDB directly for snapshot persistence and analytical queries rather than maintaining separate operational and analytics databases.
* **Injectable External Boundaries:** TLS, RDAP, `endoflife.date`, and webhook senders accept callables so tests verify threshold edge cases and alert payloads without network calls.
* **Custom UI Theming:** Styled the React dashboard with a `#050505` dark background and `#B21318` crimson accents to highlight urgent deadlines and affected services at a glance.

---

## 🛠️ System Tweaks & Troubleshooting

* **Editable Install Without Build Isolation:** If running `pip install --no-build-isolation` inside a fresh `.venv` fails on `setuptools`, run `pip install -e "backend[dev]"` with build isolation enabled.
* **Backend Unreachable from Frontend:** Make sure `deadline-map serve` is running on `http://127.0.0.1:8000` and `http://localhost:5173` is allowed in CORS (`backend/app/main.py`).
* **Offline vs. Live Probes:** Pass `--offline` during local/CI runs when skipping live external TLS/RDAP/`endoflife.date` lookups.

---

**Author:** [Braveen R](https://braveenr.linklee.in/)

*Targeting entry-level Cloud Computing, DevOps, and Site Reliability Engineering roles.*

---

## ✌️ Wrapping Up

`deadline-map` focuses on the real cause of many preventable outages: an expiring dependency whose blast radius nobody mapped in advance. Run the checks, watch the risk window, and catch expirations before they hit production! 🚀

See you in the terminal!