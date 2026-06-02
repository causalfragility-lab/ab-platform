# A/B Platform

> Interpretable, reproducible, robustness-aware experimentation — built from scratch.

---

## 🚀 Live Demo

| | URL |
|---|---|
| **API docs** | https://ab-platform-p56v.onrender.com/docs |
| **Live results** | https://ab-platform-p56v.onrender.com/results/exp_eaf81ae8 |
| **Health check** | https://ab-platform-p56v.onrender.com/health |

> Note: hosted on Render free tier — first request may take ~30 seconds to wake up.

---

## What this is

A lightweight end-to-end A/B testing platform with three core layers:

| Layer | What it does |
|---|---|
| **Assignment service** | Deterministically assigns users to variants via SHA-256 hash — same user always gets same variant, no sessions needed |
| **Inference engine** | Welch t-test (continuous) and two-proportion z-test (binary), with CIs, lift, SRM detection, and fragility warnings |
| **Methods notebook** | Power analysis, CUPED variance reduction, sequential testing (O'Brien-Fleming), and causal forest HTE |

---

## Architecture

```
ab-platform/
├── app/
│   ├── main.py                  # FastAPI entry point + CORS
│   ├── api/
│   │   ├── experiments.py       # CRUD for experiments
│   │   ├── assignment.py        # GET /assign · POST /events
│   │   └── results.py           # GET /results/{id}
│   ├── core/
│   │   ├── hashing.py           # Deterministic SHA-256 bucketing
│   │   ├── inference.py         # binary_test · continuous_test · SRM · fragility
│   │   └── diagnostics.py       # Balance checks · dropout flags
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM (Experiment, Variant, Assignment, Event)
│   │   ├── schemas.py           # Pydantic v2 request/response models
│   │   └── session.py           # DB engine + get_db dependency
│   └── services/
│       ├── assignment_service.py
│       ├── event_service.py
│       └── result_service.py    # Orchestrates inference + diagnostics + trends
├── seed.py                      # Seeds 800 users, realistic CVR split
├── render.yaml                  # Render deployment config
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

# 3. Seed demo data
python seed.py

# 4. View results
curl http://localhost:8000/results/exp_demo_001
```

### Live API

```bash
# Health check
curl https://ab-platform-p56v.onrender.com/health

# Get live experiment results
curl https://ab-platform-p56v.onrender.com/results/exp_eaf81ae8
```

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
curl -X POST https://ab-platform-p56v.onrender.com/experiments \
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
curl "https://ab-platform-p56v.onrender.com/assign?experiment_id=exp_XXXX&user_id=user_12345"
# → {"user_id":"user_12345","variant_name":"control","assigned_at":"..."}
```

Same call repeated = same variant. Always.

## Get results

```bash
curl https://ab-platform-p56v.onrender.com/results/exp_eaf81ae8
```

Returns:

```json
{
  "experiment_name": "Email Campaign Landing Page Test",
  "metric_name": "conversion",
  "metric_type": "binary",
  "control":   { "n": 396, "mean": 0.0984, "std": 0.298 },
  "treatment": { "n": 404, "mean": 0.1237, "std": 0.329 },
  "lift_absolute":  0.0253,
  "lift_relative":  0.257,
  "p_value":        0.256,
  "ci_lower":      -0.018,
  "ci_upper":       0.069,
  "statistically_significant": false,
  "practically_significant":   true,
  "interpretation": "Treatment increased conversion by 25.7% (not significant at α=0.05).",
  "sample_ratio_mismatch": false,
  "srm_p_value": 0.772,
  "fragility_warning": null,
  "dropout_info": { "flag": false },
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

## Methods notebook

Advanced statistical methods implemented and verified against the demo data:

| Method | What it shows |
|---|---|
| **Power analysis & MDE** | Required n per arm, achievable power at current n, power curves |
| **CUPED** | Variance reduction using pre-experiment covariates (Deng et al., 2013) |
| **Sequential testing** | O'Brien-Fleming alpha spending, rolling z-statistic vs. boundary |
| **Causal forest (HTE)** | Data-driven CATE estimation, feature importances, segment-level effects |
| **SQL patterns** | Production-grade warehouse queries for CVR, SRM, funnel, daily trends |

---

## Demo scenario

**"Email Campaign Landing Page Test"**

| | Control | Treatment |
|---|---|---|
| n | 396 | 404 |
| CVR (observed) | 9.84% | 12.37% |
| Lift | +25.7% | |
| p-value | 0.256 (n.s.) | |
| SRM | None (p=0.772) | |
| Interpretation | Promising lift but underpowered — need more data | |

---

 ## Completed (v0.2 Methods Layer)

- [x] Power analysis + sample size calculator
- [x] Covariate adjustment (CUPED) to reduce variance
- [x] Sequential testing with alpha spending
- [x] Subgroup breakdown (segment-level lift)
- [x] Heterogeneous treatment effects (causal forest)

## Next roadmap

- [ ] Dashboard UI (React + Plotly)
- [ ] PostgreSQL persistence for production
- [ ] Authentication + multi-tenant experiments
- [ ] Production monitoring + alerting
- 
