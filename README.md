# Crucible — Closed-Loop GenAI Payment-Fraud Lab

**Build the attack. Build the defense. Close the loop.**

Crucible is an offline, dual-rail (card + UPI) adversarial laboratory for the [Mastercard Innovation Challenge @ GFF 2026](https://www.globalfintechfest.com/) — *AI Defense Lab for Payment Security*. It identifies novel GenAI-powered payment-fraud attack vectors, simulates them at production scale against realistic legitimate traffic, trains a detector under strict anti-leakage rules, and feeds every defense gap back into the next generation of attacks.

One binary loop, real artifacts, zero external dependencies:

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│  IDENTIFY │ ──▶ │  SIMULATE │ ──▶ │  DETECT   │ ──▶ │  MUTATE   │
│ 30-vector │     │ 8 crews + │     │ causal    │     │ SHAP-guid │
│ ontology  │     │ background│     │ LightGBM  │     │ retrain   │
└───────────┘     └───────────┘     └─────┬─────┘     └─────┬─────┘
     ▲                                      │ gaps             │
     └──────────────────────────────────────┴──────────────────┘
                        frozen Test window
```

## Why it matters

GenAI compresses the cost of running payment fraud: deepfake KYC, agentic checkout bots, LLM-drafted BEC, prompt-injected remittance copilots. Defenses built only on yesterday's fraud fail against tomorrow's attack. Crucible turns that arms race into a **repeatable offline experiment** — attacks are simulated, not real; the defense is measured, not claimed; the feedback loop is auditable end-to-end.

## Quickstart

```bash
# backend (Python 3.12+, managed by uv)
uv sync
uv run uvicorn crucible.api.main:app --reload
open http://127.0.0.1:8000/

# tests
uv run pytest -q                    # 25 passing

# frontend (already served by FastAPI; rebuild after edits)
cd frontend && npm install && npm test && npm run build
```

No API keys. No network calls. No real PANs, banks, or rails — everything is synthetic by construction.

## The three pillars

### 1. Identify — 30-vector attack ontology

`data/ontology.yaml` defines the attack surface across channels, rails, and social-engineering surfaces:

- **8 behaviourally distinct simulated crews** (trainable adversaries): deepfake-KYC mule fan-out (`V-CIP_Mule`), browser-steered agentic checkout, prompt-injected remittance copilot notes, synthetic-merchant triangulation, scaled investment-app scams, LLM card testing, auto-dispute farms, voice-cloned executive transfers.
- **22 playbook vectors** spanning phishing, synthetic identity, adversarial ML, and refund abuse — catalogued with telemetry requirements for future simulation.

### 2. Simulate — high-fidelity dual-rail worlds

Deterministic, seeded generation of legitimate traffic plus scheduled fraud overlays:

- **Card rail (US):** MCC-mix amounts matching the declared distributions — 60% grocery N(45, 15), 20% dining N(30, 10), 20% uniform MCCs.
- **UPI rail (IN):** 70% P2M N(₹500, ₹200), 30% P2P N(₹2,000, ₹1,000); exactly **80% of volume inside 09:00–21:00 IST business hours** (off-peak sampled outside the window).
- **Graph realism:** merchant/payee in-degree follows Pareto (α = 1.5); users keep stable PAN/VPA entities so behavioral history is real.
- **Label realism:** 30% of card fraud labels arrive only after a **45-day chargeback lag**; UPI labels are immediate.
- **Fidelity is verified, not asserted:** four KS goodness-of-fit gates (grocery/dining/P2M/P2P vs their declared truncated-normal CDFs, p > 0.05) plus the IST-hours band — each run reports pass/fail chips in the Lab UI.
- **Scale:** fraud volume scales with world size (fresh mule entities per wave), holding near real-world rates from 3-day demos to the full spec scale below.

### 3. Detect — leakage-safe, imbalance-aware, honestly evaluated

- **Strictly causal features** (`features/assembler.py`): per-entity `last_5_amounts`, `last_10_mccs`, `sum_amount_24h`, `count_tx_1h`, capped `prior_tx_count` (new-account signal), `geo_mismatch`, `velocity_spike`, GenAI telemetry. Vectorized assembly keeps exact loop-reference semantics at ~4 s for 900k events.
- **LightGBM** with `scale_pos_weight` for ~0.6% fraud prevalence; native TreeSHAP for attribution.
- **Policy bands** straight from the spec: `DECLINE / HOLD / STEP_UP / APPROVE` at 1.0× / 0.9× / 0.7× of an **empirically selected 1%-FPR operating point** on validation.
- **Zero-day protocol:** `agentic_checkout` and `remittance_injection` are masked to label 0 in Train/Val and surface as fraud only in the frozen Test split — per-family recall is reported, never trained on.
- **Economics:** expected loss = USD sum of fraud APPROVEd by policy (INR at fixed 84/USD).

### 4. Mutate — SHAP-guided adversarial feedback

Approved in-sample misses on frozen Test drive TreeSHAP attribution → `CrewConfig` bound perturbation → **Train-window-only resimulation** → retraining → Δ PR-AUC on the untouched Test window. Holdout families are never mutated; the zero-day table stays honest. Negative deltas are reported as-is.

## Verified end-to-end (deterministic seeds)

| Scale | Events | Fraud | Test FPR @ OP | PR-AUC | Zero-day recall (agentic / remittance) | Mutation Δ PR-AUC |
|---|---|---|---|---|---|---|
| Demo — seed 1, 3d × 80 users | 444 | 204 | 0.0% | 0.988 | 1.00 / 0.75 | no eligible miss (honest) |
| **Spec — seed 1, 90d × 10,000 users** | 905,304 | 5,304 (0.59%) | 0.8% | 0.405 | 1.00 / 0.75 | **+0.077** |

Spec-scale cycle runs offline in ~28 s. The Lab UI ships both scales as one-click presets plus a free seed field.

## Lab UI

The Vite/React lab (`http://127.0.0.1:8000/`) streams **real backend stage events** over SSE while the cycle runs, then retains the completed trace above the full evidence tape:

- Fidelity gate chips (4 KS gates + IST band + overall verdict)
- Frozen-Test detection metrics, decision mix, delayed-label counts, TreeSHAP signal bars
- **Per-family efficacy table** with in-sample vs zero-day aggregates
- **Concrete attack evidence**: top DECLINE catches and APPROVE misses — token-only entities, GenAI signal, score, decision

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /api/ontology` | All 30 validated attack vectors |
| `POST /api/cycle` | Full seeded cycle → generation / detection / mutation / evidence artifact |
| `POST /api/cycle/stream` | Same cycle, SSE: real Identify → Simulate → Detect → Mutate boundaries first |

```bash
curl -s -X POST localhost:8000/api/cycle \
  -H 'Content-Type: application/json' \
  -d '{"seed": 1, "n_days": 90, "num_users": 10000}' | jq .detection.pr_auc
```

## Repository layout

```
src/crucible/
├── api/          # FastAPI surface + SSE stream
├── detector/     # LightGBM, policy bands, operating point
├── evaluation/   # Chronological split, zero-day masking, expected loss
├── features/     # Vectorized causal assembler (anti-leakage)
├── loop/         # Orchestrator + SHAP mutator
├── models/       # Event Envelope, payloads, CrewConfig
├── ontology/     # YAML loader + validation
└── simulator/    # Background, Pareto topology, 8 crews
tests/            # 25 public-interface pytest specs
frontend/         # Vite + React Lab UI
data/             # ontology.yaml
docs/             # PRD, backlog (CRU-01…CRU-20)
```

Every directory carries an `AGENTS.md` decision log — architecture, trade-offs, and rejected alternatives are documented at the module boundary.

## Guardrails

- **Simulation-only.** No live banks, NPCI, card networks, phishing infrastructure, faces, voices, real PANs, CVVs, or exploit kits. PANs are tokens and rejected at schema level if they contain 13–19 digit runs.
- **No leakage.** Features aggregate strictly `t − Δt`; a `future_*` column aborts assembly; Test is never resampled, rescored-after-regeneration, or used for threshold selection.
- **No metric theater.** Zero-recall outcomes, `no_in_sample_approve_miss`, and negative mutation deltas are reported honestly.

## Stack

Python 3.12 · FastAPI · Pydantic · pandas · NumPy · LightGBM (native TreeSHAP) · SciPy · scikit-learn · Vite · React · TanStack Query · Vitest.
