# Trend‑aware risk signals engine 

**explainable risk signals engine** + **UK trend alert subsystem** for a reputation & exposure manager.

It includes:
- A small **synthetic Items dataset** (CSV + JSONL) with **edge cases** (sarcasm, quoting, ambiguity, non‑political use of political terms, multi‑meaning trend terms).
- A minimal **FastAPI** service with transparent scoring and reason lists.
- A minimal **UK trends ingestor** (NewsAPI optional, RSS fallback) + trend term extraction.
- A simple **cross‑match job** that creates Alerts when historical items overlap with current trends.
- A tiny demo **single‑page dashboard** (vanilla HTML/JS) that calls the API.
- Starter **SQLite schema** + seed script + unit tests.

> Ethical framing: scores are **risk indicators**, not judgments. Operate only on **user‑provided/consented** data. Explanations are returned for every flag.

---

## 1) Quick start (local)

### Prereqs
- Python 3.10+
- (Optional) Node not required
- (Optional) A NewsAPI key (for /trends/ingest using live headlines)

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Seed the local DB (SQLite)
```bash
python -m scripts.seed_db
```

### Run the API
```bash
uvicorn app.main:app --reload
```

Open:
- API docs: http://127.0.0.1:8000/docs
- Demo UI:   http://127.0.0.1:8000/

---

## 2) Key endpoints

- `POST /risk/score` — score a single item (returns score + reasons + decomposition)
- `GET  /items` — list sample items + latest stored scores
- `GET  /trends/current` — list current trends stored in DB
- `POST /trends/ingest` — ingest headlines and update `TrendTopic`
- `POST /alerts/run` — cross‑match trends to items and create `Alert`
- `GET  /alerts` — list alerts

A static OpenAPI contract is included at `openapi.yaml` (FastAPI also generates one at `/openapi.json`).

---

## 3) Scoring model (transparent, configurable)

Signals (all weights configurable in `config/scoring.yaml`):
- **Sentiment** (VADER, rule‑based) — negative tone nudges risk upward
- **Topic tags** (keyword rules from `config/topics.yaml`)
- **Toxicity** (rule‑based keyword list + simple style cues)
- **Age** (older items get a small exposure bump)
- **Trend overlap delta** (if item overlaps with current trends)

Every signal returns:
- numeric contribution
- structured reasons (matched terms, categories, overlaps)
- optional “edge case” annotations (possible sarcasm, quoting, ambiguity)

---

## 4) Data included

### Items dataset
- `data/items_synthetic.csv`
- `data/items_synthetic.jsonl`

### Trend history (for offline backtesting / rescoring demos)
- `data/trend_history_uk_demo.csv`

---

## 5) Notes on “Twitter/X datasets”
Many Twitter/X research datasets are shared as **Tweet IDs only**, and require “rehydration” via the API to fetch text (to comply with platform redistribution/compliance rules). For this student project (no keys / no OAuth), this sponsor pack ships a synthetic dataset and open‑licensed trend sources instead.

See `data/EXTERNAL_DATASETS.md` for recommended open‑licensed alternatives and caveats.

---

## 6) Tests
```bash
pytest -q
```

---

## 7) Repo structure
```
app/            FastAPI app
config/         YAML configs (topics, scoring weights, ambiguity rules)
data/           sample datasets
scripts/        seed + demo scripts
tests/          unit tests
web/            simple dashboard (served as static)
```
