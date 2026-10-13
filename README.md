# Opentrons Liquid Handler Agent

Rule-based demonstration of liquid-handling task flags, with separate Python utilities for experimental dilution calculations, well geometry estimates, and in-memory audit records.

**Scope:** This repository does **not** connect to or command an Opentrons robot, generate validated Opentrons Protocol API programs, demonstrate calibrated pipetting accuracy, or establish regulatory compliance. The generic warning thresholds are examples, not manufacturer or laboratory acceptance limits.

## Browser demonstration

The `web/` directory contains a static, server-independent interface suitable for GitHub Pages. It evaluates the same **demonstration rules** as `agents/workers.py`:

- Primary metric above **25** → elevated warning.
- Secondary metric above **12** → elevated warning.
- Explicit critical flag → critical classification.
- Status descriptor containing DISCORDANT, ANOMALY, MUTANT, VIOLATION, FAIL, or REJECT → elevated warning.

The interface supports JSON output and downloading the most recent result. It creates **no HMAC signatures** or real hardware audit records. It does not use a backend, remote API, tracking library, browser storage, or cookies; inputs remain in page memory until reset/reload. Do not enter patient identifiers or sensitive laboratory information.

To preview locally, open `web/index.html` in a modern browser, or serve the directory using `python -m http.server` and navigate to `/web/`. The GitHub Pages deployment workflow publishes the contents of `web/` on changes to `master`.

## Python setup

Python 3.9 or newer is required.

```bash
git clone https://github.com/abusuraihsakhri/opentrons-liquid-handler-agent.git
cd opentrons-liquid-handler-agent
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

The installed `opentrons-liquid-handler-agent` command uses the root `cli.py` implementation. For backward compatibility, `opentrons-liquid-handler-engine` uses the independent `opentrons_agent/cli.py` implementation.

### CLI examples

```bash
python cli.py audit --task-id DEMO-001 --target SAMPLE-A01 --primary 28.5 --secondary 14.2
python cli.py chat "What are the demonstration rules?"
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
```

The CSV input accepts `task_id`, `target_identifier`, `primary_metric`, `secondary_metric`, `status_descriptor`, and `is_critical_flag` (`true`, `1`, or `yes` for true). Invalid rows are skipped with a warning. Output is a threshold-classification dossier, **not a validated protocol**.

### Calculation modules

- `opentrons_agent.normalization_engine`: mass-balance dilution calculations and serial well mapping, with finite-input and feasibility checks.
- `opentrons_agent.protocol_optimizer`: heuristic liquid-class and dead-volume estimates; these are not empirically calibrated or guaranteed hardware settings.
- `opentrons_agent.audit_trail`: in-memory hash-linked action records; these are not immutable storage or 21 CFR Part 11 records.
- `enrichment.py`: generic threshold evaluations named for possible enhancement areas, **not** complete implementations of LIMS integration, QC charts, error recovery, or labware generation.

## Optional local API

```bash
python -m pip install -e ".[server]"
python cli.py serve --host 127.0.0.1 --port 8000
```

Endpoints are `/health`, `/metrics` (JSON), `POST /api/audit`, and `POST /api/chat`. The mock chat provider does not invoke an external language model. The in-memory `/api/audit/logs` endpoint is disabled unless `AUDIT_LOG_ACCESS_KEY` is set; when enabled it requires the `X-Audit-Log-Key` header. Set `AUDIT_SECRET_KEY` to a secure, randomly generated value for consistent HMAC signing across restarts. Neither the log records nor the signing state are persisted to a database or disk.

The development API does not provide user authentication for task submission. **Do not expose the service directly to an untrusted network**; run it locally or behind an authenticated gateway, and do not send PHI. Pattern-based identifier screening does not guarantee de-identification.

## Docker

Copy `.env.example` to `.env` and set a random `AUDIT_SECRET_KEY` value. Then run:

```bash
docker compose up --build
```

The compose file publishes port 8000 to **localhost only**. `.dockerignore` keeps local `.env` files and development artifacts out of the image build context.

## Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
node --check web/app.js
node --test tests/test_web_rules.cjs
```

GitHub Actions executes Python tests on 3.10–3.13 and browser-rule tests using Node.js 22. There is no physical-robot integration or wet-lab verification in this test suite.

## Technology, privacy, and license

Python, Pydantic v2, optional FastAPI/Uvicorn, pytest, and dependency-free browser JavaScript. The browser demo is intended for contemporary desktop and mobile browsers. CLI and API task data are held in process memory and should not be treated as secure persistent records.

Licensed under the [MIT License](LICENSE).
