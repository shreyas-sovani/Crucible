# AGENTS.md — src/crucible/detector/

## Ownership
LightGBM fraud scoring and business policy mapping.

## Purpose
Trains deterministic binary LightGBM, exposes bounded probabilities and native TreeSHAP contributions, and maps scores to Context-defined decisions.

## What This Controls
Fraud action outcomes. Wrong thresholds change DECLINE, HOLD, STEP_UP, and APPROVE decisions and corrupt expected-loss and mutation selection.

## Connections
- Depends on: `lightgbm`, `scikit-learn`, NumPy, and feature matrices from `features/assembler.py`.
- Depended on by: `evaluation/harness.py`, `loop/mutator.py`, API extensions, and detector tests.
- External systems touched: local Homebrew `libomp` supplies LightGBM runtime on macOS; no network or payment system is called.

## Current State
Working. `fit()` requires both classes and is imbalance-aware (`scale_pos_weight = negatives/positives`, 128 estimators); `predict()` uses exact Context 1.0/0.9/0.7 operating-point bands; `select_operating_point()` returns a threshold plus empirical FPR/recall under the 1% cap, and `threshold_metrics()` measures that fixed threshold on frozen Test. `shap_values()` uses native `pred_contrib` output.

## Decision Log

### 2026-08-20 — Imbalance-aware fit for spec-scale worlds (CRU-20)
- **Change**: `fit()` now sets `scale_pos_weight = negatives/positives` and raises `n_estimators` from 64 to 128.
- **Reasoning**: At 90d × 10,000 users fraud is ~0.6% of Events; the unweighted ensemble collapsed to PR-AUC 0.02 despite learnable signals. Weighting plus the `prior_tx_count` feature restores per-family recalls without touching the policy bands or evaluation protocol.
- **Rejected alternative(s)**: Resampling Train — prohibited. Calibrating on Test — label leakage. Keeping 64 estimators — underfit at the larger Train size.
- **Task/session**: Spec-scale technical-gap sweep ahead of feature freeze.

### 2026-08-20 — Made 1% FPR operating-point evidence measurable
- **Change**: Added `OperatingPointMetrics`, `select_operating_point()`, and `threshold_metrics()`; `get_operating_point()` delegates to selection for backwards-compatible threshold callers.
- **Reasoning**: A threshold alone cannot prove the FPR budget or distinguish validation policy selection from frozen-Test score evaluation.
- **Rejected alternative(s)**: Calling recall at a validation threshold “Recall @ 1% FPR” on Test — Test FPR can drift. Optimizing Test threshold for policy — leaks Test labels; Test selection is reported only as a score-efficacy metric.
- **Task/session**: Repair technical gaps in full Identify → Simulate → Detect → Mutate loop.

### 2026-08-20 — Added LightGBM detector and native SHAP seam
- **Change**: Added `model.py` with model wrapper, operating-point selection, policy mapping, and contribution access.
- **Reasoning**: PRD locks LightGBM; its native contributions avoid a separate SHAP/Numba runtime dependency.
- **Rejected alternative(s)**: Trained GNN or logistic fallback — violate locked model choice. Four-threshold mapping from stale docs — refreshed Context defines three boundaries and four actions.
- **Task/session**: Full refreshed-spec TDD implementation.

## Known Gotchas
macOS LightGBM wheel requires `libomp`; install with `brew install libomp` if import fails. Never resample before chronological split. Finite validation windows can satisfy a 1% cap with 0 observed false positives; report empirical rates, not an assumed exact 1%.
