
---
product: Crucible
status: ready-for-implementation
audience: [LLM coding agents, PMs, engineers]
glossary: CONTEXT.md
---

# PRD: Crucible — Closed-Loop GenAI Payment-Fraud Lab

## 1. System Architecture & Directory Tree
The project must strictly adhere to this package tree. Do not invent new root directories.
 ⁠text
crucible/
├── src/crucible/
│   ├── api/          # FastAPI surface
│   ├── detector/     # LightGBM, policy, baselines
│   ├── evaluation/   # Splits, metrics, hold-out logic
│   ├── features/     # Anti-leakage assembler, rolling windows
│   ├── loop/         # SHAP mutator, retraining orchestrator
│   ├── models/       # Pydantic schemas (Event, Config)
│   ├── ontology/     # YAML loader, schema validation
│   └── simulator/    # Background, graph overlay, crews
├── tests/            # pytest suite (1:1 with src modules)
├── data/             # ontology.yaml, fixed seeds
└── frontend/         # Vite + React (UI)



## 2. Module Rules & Invariants

### 2.1 Attack Ontology & Vectors

The `data/ontology.yaml` must contain exactly 30 vectors.

* **The 8 Simulated Crews (Must implement `BaseCrew`):**
1. `V-CIP_Mule` (family: deepfake_kyc, rail: upi)
2. `Agentic_Checkout` (family: agentic_checkout, rail: card)
3. `Prompt_Inject_Copilot` (family: remittance_injection, rail: upi)
4. `Synthetic_Triangulation` (family: synthetic_merchant, rail: card)
5. `Scaled_Investment_APP` (family: app_scam, rail: upi)
6. `LLM_Card_Testing` (family: cnp_testing, rail: card)
7. `Auto_Dispute_Farm` (family: first_party, rail: card)
8. `Voice_Clone_Exec` (family: bec, rail: upi)


* **The 22 Playbook-Only Vectors:** Must be listed with valid schemas, using families: `phishing, synthetic_id, adversarial_ml, refund_abuse`. (Agents: auto-generate these 22 exactly matching the YAML schema with `status: playbook`).

### 2.2 Feature Assembler

* **Rolling Windows:** `last_5_amounts`, `last_10_mccs`, `sum_amount_24h`, `count_tx_1h`.
* **Causal Invariant:** All windows must strictly aggregate $t - \Delta t$.
* **Rules Baseline:** Include boolean features for `geo_mismatch` (`device_country != merchant_country`) and `velocity_spike` (`count_tx_1h > 5`).

### 2.3 Evaluation & The Hold-Out Contradiction (Patched)

* **Chronological Split:** Train (0-70%), Val (70-85%), Test (85-100%).
* **Zero-Day Holdout Families:** `agentic_checkout` and `remittance_injection`.
* **Strict Masking:** Events from these two families must be forced to `label = 0` (or dropped) in Train and Validation splits. They appear as `label = 1` ONLY in the Test split to evaluate zero-day efficacy.

### 2.4 Adversarial Loop & Mutation

* **Mutation Inclusion Rule:** The Mutator must ONLY harvest missed events from the 6 *in-sample* simulated families. **Missed hold-out families must never be mutated or added to the next training cycle.** Adding them destroys the zero-day honesty table.
* **Mutation Logic:**
1. Harvest misses (`label == 1` and `decision == APPROVE`) for in-sample families on the Test set.
2. Compute SHAP top-3 features for those rows.
3. Perturb the corresponding `CrewConfig` bounds to invert the SHAP value.
4. Resimulate *only* the Train window with the new config.
5. Retrain. Calculate $\Delta$ PR-AUC on the *frozen* Test window.





---
