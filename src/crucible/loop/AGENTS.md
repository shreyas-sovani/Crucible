# AGENTS.md — src/crucible/loop/

## Ownership
Adversarial feedback mutation constrained by zero-day evaluation rules.

## Purpose
Runs the closed feedback loop: joins features to simulated Events, trains LightGBM chronologically, scores frozen Test, then mutates and retrains only when eligible misses exist.

## What This Controls
Feedback-loop validity, metrics, and judge evidence. If holdout misses mutate crews or resimulation alters Test, zero-day and Δ PR-AUC claims become contaminated.

## Connections
- Depends on: `evaluation/harness.py`, `features/assembler.py`, `detector/model.py`, `simulator/world.py`, `models/config.py`, NumPy/Pandas, SciPy, and scikit-learn metrics.
- Depended on by: `api/main.py` and `tests/test_api.py`.
- External systems touched: none.

## Current State
Working complete Cycle. `run_closed_loop()` produces generation, detection, mutation, and evidence reports and can report real Identify, Simulate, Detect, and Mutate boundaries to an injected callback. Generation reports four zero-truncated KS gates (`FIDELITY_MIN_SAMPLES = 50`; smaller samples report `None` and are excluded from the verdict), realized IST business-hour share with pass band 0.70–0.90, and `fidelity_pass`. Detection reports 45-day delayed card-label count/share and per-family `FamilyEfficacy` rows on frozen Test, plus prior metrics. `EvidenceReport` exposes token-only top DECLINE catches and APPROVE misses. Fidelity KS samples only legitimate Background rows. Train/Val fit use observed labels; it reports both validation selection and frozen-Test characteristics for the 1% FPR policy, plus frozen-Test score efficacy. Only six in-sample simulated families can mutate; retraining resimulates the exact original Train window and evaluates the replacement model on original frozen Test features.

## Decision Log

### 2026-08-21 — Per-event TreeSHAP on evidence samples (CRU-22)
- **Change**: `_evidence_report` now takes the model, feature names, and frozen Test matrix; selected catch/miss rows get `top_shap` (top-3 signed contributions, strongest first) computed from one batched `shap_values` call on ≤10 rows. Row lookup maps frame index labels to matrix positions via ordinal enumeration because Test-slice labels are global Event positions.
- **Reasoning**: "Why did the detector decide this?" is the natural judge question; per-row native TreeSHAP already existed at this seam. Batched-subset computation avoids a second full-matrix SHAP pass at spec scale.
- **Rejected alternative(s)**: Attributions from the global mean-|SHAP| list — row-agnostic, explains nothing. Recomputing SHAP per row in a loop — N predict calls for no benefit.
- **Task/session**: Judge-interaction UX pass.

### 2026-08-20 — Fidelity gates, family efficacy, delayed-label counts, evidence samples (CRU-14/15/18)
- **Change**: `GenerationReport` gained `dining_ks_pvalue`, `p2p_ks_pvalue`, `ist_business_hour_share`, `ist_business_hours_pass`, `fidelity_gate_count`, `fidelity_pass`; KS gates compare against the zero-truncated normal CDF with a 50-sample minimum. `DetectionReport` gained `delayed_card_fraud_count/share` and `family_efficacy` rows (recall at the validation-selected operating point). New `EvidenceReport`/`EvidenceEvent` serialize concrete frozen-Test fraud Events with masked tokens, GenAI signal, score, and decision.
- **Reasoning**: CONTEXT defines the p > 0.05 fidelity threshold as a verdict, not just reported p-values; PRD 2.3 requires zero-day efficacy per held-out family, which an aggregate PR-AUC hides; the 45-day chargeback lag and concrete attack samples are judge-visible proof the loop is real. Small-sample KS p-values are uniform draws, so gates under 50 samples report `None` instead of flaking `fidelity_pass`.
- **Rejected alternative(s)**: Plain-normal reference CDF — the generator is zero-truncated, so spec-scale KS fails at p=0.000 against it. Threshold-shopping unlucky demo gates — dishonest. Sampling evidence rows from Train — evidence must describe frozen-Test outcomes.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Added work-boundary callback seam
- **Change**: `run_closed_loop()` accepts optional `on_stage(stage, status)` and calls it immediately before real Identify, Simulate, Detect, and Mutate work.
- **Reasoning**: Orchestration owns the only honest point at which stage progress is known. The callback keeps reporting optional and leaves its returned `CycleRun`/offline behavior unchanged.
- **Rejected alternative(s)**: Timing estimates in UI — not evidence. Returning partial model artifacts from loop internals — widens the module contract and risks Test leakage.
- **Task/session**: Make full offline Cycle visibly unfold from real work.

### 2026-08-20 — Corrected fidelity, operating point, and feedback-loop boundaries
- **Change**: `orchestrator.py` filters fidelity samples to legitimate rows, filters delayed labels before fit, reports labeled counts and validation/Test operating characteristics, retains frozen Test matrices, and passes the original Train frame into `resimulate_train_window()`. `mutator.py` now computes TreeSHAP only on eligible APPROVE-miss rows.
- **Reasoning**: Fraud rows must not change the stated Background distributions; policy selection and Test evaluation need separate metrics; mutation must not regenerate or inspect Test; SHAP must describe the misses it mutates.
- **Rejected alternative(s)**: Full-window duration resimulation — violates Train-only claim. Whole-Test SHAP — attributes unrelated holdouts and caught events. Hiding zero eligible misses or negative Δ PR-AUC — fabricates feedback evidence.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Added executable seeded Cycle orchestrator
- **Change**: Added `orchestrator.py` and public `run_closed_loop()`; it assembles causal features, splits chronologically, fits LightGBM, derives OP, reports policy/SHAP/loss, and retrains after eligible mutation.
- **Reasoning**: Existing modules were isolated with no caller, making the Cycle button a no-op acknowledgement. Orchestration belongs at the loop seam because it owns frozen-Test and mutation rules.
- **Rejected alternative(s)**: Client orchestration — violates Lab HTTP boundary. Synthetic report fields — would hide whether the detector actually found a miss. Rescoring regenerated Test — violates frozen-Test requirement.
- **Task/session**: Diagnose and complete no-op Run Offline Cycle.

### 2026-08-20 — Added zero-day-safe SHAP mutator
- **Change**: Added `mutate_config()` and explicit in-sample family allowlist.
- **Reasoning**: Excluding `agentic_checkout` and `remittance_injection` before any attribution preserves PRD zero-day honesty.
- **Rejected alternative(s)**: Mutating every miss — leaks zero-day families into next training cycle. Unbounded increments — can produce invalid CrewConfig values.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
Pass feature names in exact matrix column order. Before joining a FeatureSet, replace source telemetry columns with derived feature columns; duplicate names change LightGBM dimensionality and break frozen-Test scoring. A negative Δ PR-AUC is a real result, never a failure to be hidden. `recall_at_1pct_fpr` is a frozen-Test ranking metric; `test_*_at_operating_point` describes deployed validation-selected policy. `on_stage` is observational only: it must never alter config, scores, split, or Test contents.
