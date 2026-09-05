# Opentrons Liquid Handler Agent

> **Domain:** Computational Biology & AI Drug Discovery  
> **Reference Guidelines & Standards:** `wwPDB, IUPAC & CLSI Computational Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Opentrons Liquid Handler Agent is an enterprise-grade distributed component platform for computational biology and AI drug discovery. It provides deterministic calculation engines, multi-tier risk classification, and cryptographic audit trails for liquid handling robotics workflows.

---

## ⚙️ Key Capabilities & Algorithmic Modules

- **Deterministic Calculation Engine**: Strict compliance with standard reference formulations and thresholds.
- **Risk & Urgency Classification**: Multi-tier categorization with automated clinical/operational action recommendations.
- **Validation & Guardrails**: Rigorous input bounds checking and anomaly detection.
- **Multi-Worker Evaluation**: InvariantQC, Safety Escalation, and Protocol Conformance workers.
- **Enrichment Suite**: Protocol optimization, labware definition, traceability, parallelization, error recovery, LIMS integration, normalization, and QC monitoring.

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/opentrons-liquid-handler-agent.git
cd opentrons-liquid-handler-agent

# Install dependencies
pip install fastapi uvicorn pydantic pytest

# Optional: Set audit secret key for persistent audit integrity
export AUDIT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

---

## 💻 CLI Quickstart & Usage

### 1. Run Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Interactive Chat Query
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch Process CSV Records
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Launch FastAPI REST Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--task-id`: Unique task identifier (default: TASK-2026-001)
- `--target`: Target identifier (default: KEY-TARGET-01)
- `--primary`: Primary metric value (float, default: 28.5)
- `--secondary`: Secondary metric value (float, default: 14.2)
- `--critical`: Flag for critical status (store_true)
- `--status`: Status descriptor (default: DISCORDANT)

### Input Data Schema (CSV Batch)

| Field | Description | Requirement |
|:------|:------------|:------------|
| `task_id` | Unique task identifier | Required |
| `target_identifier` | Target entity identifier | Required |
| `primary_metric` | Primary measurement value | Required |
| `secondary_metric` | Secondary measurement value | Optional |
| `is_critical_flag` | Critical escalation flag | Optional |
| `status_descriptor` | Status code descriptor | Optional |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Security Configuration

Set the `AUDIT_SECRET_KEY` environment variable for persistent audit trail integrity:

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in environment
export AUDIT_SECRET_KEY="your-generated-key"
```

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

### Docker
```bash
# Copy environment template
cp .env.example .env
# Edit .env and set AUDIT_SECRET_KEY

# Build and run
docker build -t opentrons-liquid-handler-agent .
docker run -p 8000:8000 --env-file .env opentrons-liquid-handler-agent
```

### Docker Compose
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env and set AUDIT_SECRET_KEY

# Launch
docker-compose up -d
```

---

## 📁 Project Structure

```
opentrons-liquid-handler-agent/
├── agents/                  # Core agent modules
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── models.py           # Pydantic data models
│   ├── supervisor.py       # Supervisor orchestrator
│   ├── workers.py          # Specialized worker agents
│   ├── llm_factory.py      # LLM provider factory
│   ├── learning.py         # Bayesian calibration engine
│   ├── metrics.py          # Prometheus metrics collector
│   └── streamer.py         # WebSocket telemetry broadcaster
├── opentrons_agent/        # Frontier agent modules
│   ├── agents.py           # Sub-agent implementations
│   ├── engine.py           # Core algorithmic engine
│   ├── models.py           # Data models
│   ├── cli.py              # Frontier CLI
│   ├── server.py           # Frontier FastAPI server
│   ├── audit_trail.py      # 21 CFR Part 11 audit trail
│   ├── normalization_engine.py  # Dilution calculator
│   └── protocol_optimizer.py    # Protocol optimization
├── tests/                  # Test suite
├── web/                    # Web operations console
├── cli.py                  # Main CLI entry point
├── simulator.py            # High-throughput simulator
├── enrichment.py           # Enrichment feature suite
├── pyproject.toml          # Project configuration
├── Dockerfile              # Docker build config
├── docker-compose.yml      # Docker Compose config
└── .env.example            # Environment template
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
