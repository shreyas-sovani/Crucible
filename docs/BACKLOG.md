# Crucible Backlog

This queue was restored on 2026-08-20. The prior file duplicated `PRD.md`; these tickets map the refreshed PRD dependency order to test-backed implementation work.

| Ticket | Scope | Status | Evidence |
| --- | --- | --- | --- |
| CRU-01 | Canonical attack ontology | done | `tests/test_ontology.py` |
| CRU-02 | Event Envelope, rail payloads, CrewConfig | done | `tests/test_models.py` |
| CRU-03 | Background generator, Pareto topology, eight crew adapters, simulation facade | done | `tests/test_background.py`, `test_topology.py`, `test_crews.py`, `test_simulation.py` |
| CRU-04 | Strictly causal feature assembly | done | `tests/test_features.py` |
| CRU-05 | LightGBM detector and Context policy bands | done | `tests/test_detector.py` |
| CRU-06 | Chronological zero-day evaluation and expected-loss calculation | done | `tests/test_evaluation.py` |
| CRU-07 | In-sample-only SHAP mutation | done | `tests/test_mutator.py` |
| CRU-08 | Stateless FastAPI Lab surface and static mount | done | `tests/test_api.py` |
| CRU-09 | Vite/React Lab visualizer | done | `frontend/src/App.test.jsx` |
| CRU-10 | Executable seeded Cycle orchestration and judge-visible evidence tape | done | `tests/test_api.py`, `frontend/src/App.test.jsx` |
| CRU-11 | Honest crew diversity, fidelity, delayed labels, 1% FPR evidence, and Train-only mutation | done | `tests/test_crews.py`, `test_simulation.py`, `test_evaluation.py`, `test_detector.py`, `test_mutator.py`, `test_api.py` |
| CRU-12 | Real-time Cycle stage stream and progressive Lab trace (depends on CRU-08, CRU-10) | done | `tests/test_api.py`, `frontend/src/App.test.jsx` |
| CRU-13 | Persistent completed Cycle trace for judge review (depends on CRU-12) | done | `frontend/src/App.test.jsx` |
| CRU-14 | Per-family zero-day efficacy table on frozen Test (depends on CRU-10) | done | `tests/test_api.py` |
| CRU-15 | Fidelity gates with verdicts (4 KS gates, IST 80% window) and 45-day delayed-label evidence (depends on CRU-10) | done | `tests/test_api.py`, `tests/test_background.py` |
| CRU-16 | Stable per-user card PAN and UPI payer entities in Background (depends on CRU-03) | done | `tests/test_background.py` |
| CRU-17 | Vectorized strictly-causal windows with loop-reference equivalence; spec-scale 90d × 10,000 users runtime (depends on CRU-04) | done | `tests/test_features.py` |
| CRU-18 | Concrete frozen-Test evidence samples: top DECLINE catches and APPROVE misses, token-only (depends on CRU-10) | done | `tests/test_api.py` |
| CRU-19 | Lab cycle controls (seed, world-scale presets through spec scale) and efficacy/fidelity/evidence UI (depends on CRU-12, CRU-14, CRU-15, CRU-18) | done | `frontend/src/App.test.jsx` |
| CRU-20 | Spec-scale realism: exact 80% IST business-hour volume, truncated-normal amounts, world-scaled fraud rate, wave-rotated crew entities, imbalance-aware LightGBM, capped `prior_tx_count` (depends on CRU-03, CRU-04, CRU-05, CRU-17) | done | `tests/test_background.py`, `test_simulation.py`, `test_features.py` |

## Execution Rule

Pick tickets in order. A ticket can move to `done` only after its listed tests pass. New work must add an explicit ticket, dependency, and public-interface test before implementation.

## Next Review

No ready implementation ticket. Spec scale (`n_days=90`, `num_users=10,000`, ~905k Events, ~28 s offline Cycle) and demo scale (seed `1`, three days, 80 users, PR-AUC ~0.99) are both verified end-to-end; the Lab exposes both as presets. Demo may honestly return `no_in_sample_approve_miss` when the policy catches every eligible Test fraud event.
