# A/B Platform

> Interpretable, reproducible, robustness-aware experimentation — built from scratch.

---

## What this is

A lightweight end-to-end A/B testing platform with three core layers:

| Layer | What it does |
|---|---|
| **Assignment service** | Deterministically assigns users to variants via SHA-256 hash — same user always gets same variant, no sessions needed |
| **Inference engine** | Welch t-test (continuous) and two-proportion z-test (binary), with CIs, lift, SRM detection, and fragility warnings |
| **Dashboard** | React UI with experiment registry, result cards, CI visualization, and day-by-day trend plots |

---

## Architecture

```
ab_platform/
├── app/
│   ├── main.py                  # FastAPI entry point + CORS
│   ├── api/
│   │   ├── experiments.py       # CRUD for experiments
│   │   ├── assignment.py        # GET /assign · POST /events
│   │   └── results.py           # GET /results/{id}
│   ├── core/
│   │   ├── hashing.py           # Deterministic SHA-256 bucketing
│   │   ├── inference.py         # binary_test · continuous_test · SRM · fragility
│   │   ├── metrics.py           # (extensible metric definitions)
│   │   └── diagnostics.py      # Balance checks · dropout flags
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM (Experiment, Variant, Assignment, Event)
│   │   ├── schemas.py           # Pydantic v2 request/response models
│   │   └── session.py           # DB engine + get_db dependency
│   └── services/
│       ├── assignment_service.py
│       ├── event_service.py
│       └── result_service.py    # Orchestrates inference + diagnostics + trends
├── frontend/                    # React dashboard (see below)
├── demo_data/
│   └── seed.py                  # Seeds 800 users, 3 event types, realistic CVR split
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Quick start

### Local (Python)

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Start API
uvicorn app.main:app --reload --port 8000

# 3. Seed demo data (in a second terminal)
python demo_data/seed.py

# 4. View results
curl http://localhost:8000/results/exp_demo_001
```

### Docker

```bash
docker-compose up --build
```

API → http://localhost:8000  
Frontend → http://localhost:3000  
Docs → http://localhost:8000/docs

---

## API reference

### Experiments

| Method | Path | Description |
|---|---|---|
| `POST` | `/experiments` | Create experiment + variants |
| `GET` | `/experiments` | List all experiments |
| `GET` | `/experiments/{id}` | Get single experiment |
| `PATCH` | `/experiments/{id}/status?status=running` | Start / pause / complete |
| `DELETE` | `/experiments/{id}` | Delete experiment |

### Assignment & Events

| Method | Path | Description |
|---|---|---|
| `GET` | `/assign?experiment_id=X&user_id=Y` | Deterministic variant assignment |
| `POST` | `/events` | Log outcome event |

### Results

| Method | Path | Description |
|---|---|---|
| `GET` | `/results/{experiment_id}` | Full inference output |

---

## Create an experiment

```bash
curl -X POST http://localhost:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Homepage hero test",
    "description": "New hero image vs. current",
    "metric_name": "conversion",
    "metric_type": "binary",
    "allocation": 1.0,
    "variants": [
      {"name": "control",   "allocation_weight": 0.5},
      {"name": "treatment", "allocation_weight": 0.5}
    ]
  }'
```

## Assign a user

```bash
curl "http://localhost:8000/assign?experiment_id=exp_XXXX&user_id=user_12345"
# → {"user_id":"user_12345","experiment_id":"exp_XXXX","variant_id":"...","variant_name":"control","assigned_at":"..."}
```

Same call repeated = same variant. Always.

## Log an outcome

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_12345","experiment_id":"exp_XXXX","event_name":"conversion","event_value":1}'
```

## Get results

```bash
curl http://localhost:8000/results/exp_XXXX
```

Returns:

```json
{
  "experiment_name": "...",
  "metric_name": "conversion",
  "metric_type": "binary",
  "control":   { "n": 395, "mean": 0.0835, "std": 0.277 },
  "treatment": { "n": 405, "mean": 0.1111, "std": 0.315 },
  "lift_absolute":  0.0276,
  "lift_relative":  0.33,
  "p_value":        0.189,
  "ci_lower":      -0.0134,
  "ci_upper":       0.0686,
  "statistically_significant": false,
  "practically_significant":   true,
  "interpretation": "Treatment increased conversion by 33.0% (not significant at α=0.05).",
  "sample_ratio_mismatch": false,
  "srm_p_value": 0.724,
  "fragility_warning": "CI crosses zero — result is borderline.",
  "dropout_info": { "flag": false, "control_dropout_rate": 0, "treatment_dropout_rate": 0 },
  "daily_trends": [...]
}
```

---

## Inference methods

### Binary metric (conversion rate)
- Two-proportion z-test (pooled SE for p-value, unpooled SE for CI)
- Absolute lift in percentage points
- Relative lift as percentage

### Continuous metric (revenue, time on page)
- Welch's t-test (unequal variances)
- Welch–Satterthwaite degrees of freedom
- 95% confidence interval on difference in means

### Robustness layer
- **SRM check** — chi-square test on observed vs. expected arm sizes (α=0.01)
- **Fragility warning** — flags borderline p-values, tiny effect sizes, CIs crossing zero
- **Practical significance** — separates statistical from business significance (threshold: 1% relative lift)
- **Day-by-day trends** — detects estimate drift or peeking effects

---

## Assignment determinism

```python
# core/hashing.py
raw    = f"{user_id}::{experiment_id}"
digest = hashlib.sha256(raw.encode()).hexdigest()
bucket = int(digest[:8], 16) / 0xFFFFFFFF   # float in [0, 1)
```

- Pure function — no database read needed to check consistency
- Salted per-experiment — same user gets independent assignments across experiments
- No reassignment — first assignment is persisted and always returned

---

## Demo scenario

**"Email Campaign Landing Page Test"**

| | Control | Treatment |
|---|---|---|
| Page | Old landing page | Redesigned page |
| CVR (true) | 8% | 11.3% |
| CVR (observed) | 8.35% | 11.11% |
| n | 395 | 405 |
| Lift | +33% | |
| p-value | 0.189 (n.s.) | |
| Interpretation | Promising lift but underpowered — need more data | |

---

## Roadmap (v0.2)

- [ ] Covariate adjustment (CUPED) to reduce variance
- [ ] Multi-armed bandit assignment option
- [ ] Power analysis + sample size calculator
- [ ] Subgroup breakdown (segment-level lift)
- [ ] Sequential testing with alpha spending
- [ ] PostgreSQL support for production
- [ ] Authentication + multi-tenant experiments
