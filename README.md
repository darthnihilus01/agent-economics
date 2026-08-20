# Agent Economics — Financial Control Plane for Autonomous AI

> **Product Loop:** Measure → Attribute → Diagnose → Optimize → Verify.

Agent Economics answers: **What does every agent actually cost, what business value does it produce, and how can we automatically improve economics without reducing quality?**

---

## 🚀 Quickstart

### 1. Activate Environment & Run Server
```bash
cd /home/tinchu/agent-economics
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at `http://localhost:8000/docs`.

### 2. Seed Realistic Enterprise Traces
```bash
python app/scripts/seed_data.py
```

### 3. Generate Executive PMF Savings Report (PRD §23)
```bash
python app/scripts/generate_report.py
```

### 4. Run Test Suite
```bash
pytest tests/
```

---

## 📡 API Endpoints Overview

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/traces/ingest` | Batch ingest agent execution traces |
| `GET` | `/api/v1/traces/{id}` | Detailed trace with span waterfall and cost breakdown |
| `GET` | `/api/v1/analytics/executive` | Executive financial summary (AI spend, net benefit, ROI) |
| `GET` | `/api/v1/analytics/unit-economics` | True Cost per Successful Outcome across workflows |
| `GET` | `/api/v1/analytics/breakdowns` | Cost breakdowns by model, agent, workflow, tool, customer |
| `GET` | `/api/v1/analytics/failure-economics` | Failure waste, retry costs, top failing workflows |
| `GET` | `/api/v1/anomalies` | Active cost anomalies (runaway loops, context bloat) |
| `GET` | `/api/v1/optimizations` | Autopilot savings opportunities with quality confidence |
| `POST` | `/api/v1/optimizations/backtest` | Shadow backtest optimizations against historical traces |
| `POST` | `/api/v1/optimizations/{id}/deploy` | Deploy approved optimizations to production |
| `GET` | `/api/v1/reports/pmf-savings-report` | PRD §23 Verified Savings Report |
