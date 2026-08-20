# Crucible — Domain Glossary, Schemas, and Constants

This document is the absolute source of truth for all types, schemas, and thresholds. Coding agents must use these exact variable names, constants, and math. Do not invent alternatives.

## 1. Constants & Magic Numbers (Strict)
* **Seed Generation:** `n_days = 90`, `num_users = 10,000`, `timezone = "UTC"`.
* **Policy Thresholds (Based on Operating Point `OP` at 1.0% FPR):**
  * `score >= OP` $\to$ `DECLINE`
  * `score >= (0.9 * OP) and score < OP` $\to$ `HOLD`
  * `score >= (0.7 * OP) and score < (0.9 * OP)` $\to$ `STEP_UP`
  * `score < (0.7 * OP)` $\to$ `APPROVE`
* **Chargeback Lag (Card only):** 45 days. 30% of card fraud events have their `label` delayed by 45 days. UPI has 0 delay.
* **Expected Loss Formula:** `sum(amount_usd)` for all fraud events where `decision == "APPROVE"`. (Convert UPI INR to USD at 84.0 fixed rate for total loss calculation).
* **Fidelity KS-Test Threshold:** $p > 0.05$ (meaning distributions are statistically similar).

## 2. Strict Data Schemas
Events are payment transactions. Non-transactional data (KYC, copilot sessions) are strictly **payload fields attached to the payment event**, not separate standalone events.

### Event Envelope
* `event_id` (str): UUIDv4.
* `timestamp` (datetime): UTC, tz-aware.
* `rail` (Literal["card", "upi"]): The payment rail.
* `channel` (Literal["online", "pos", "in_app"]): The origination channel.
* `device_country` (str): ISO 3166-1 alpha-2 (e.g., "US", "IN").
* `label` (int): `0` (legitimate), `1` (fraud). Set to `None` for inference.
* `family` (str): The attack family (e.g., "agentic_checkout").
* `vector_id` (str): Foreign key to the Attack Ontology.

### Rail-Specific Payloads
* **Card Payload:** `pan_token` (str, masked. Constructor MUST raise `ValueError` on 13-19 digits), `mcc` (int), `amount_usd` (float), `entry_mode` (str), `stan` (str), `merchant_country` (str).
* **UPI Payload:** `payer_vpa` (str), `payee_vpa` (str), `amount_inr` (float), `tx_note` (str).

### GenAI Artifact Telemetry (Optional Payload)
* `v_cip_injection_flag` (bool): Deepfake camera hooks detected.
* `browser_dom_anomaly_score` (float, [0,1]): Headless/agentic steering probability.
* `remittance_prompt_score` (float, [0,1]): NLP risk score for malicious note intent.

## 3. Simulation & Fidelity Distributions
Agents must use these exact distributions for the Background Generator and Fidelity tests.
* **Card Background (Matches Sparkov):** 
  * Geo: `US` only.
  * Amounts: 60% MCC 5411 (Grocery, $\mu=\$45$, $\sigma=\$15$), 20% MCC 5812 (Dining, $\mu=\$30$, $\sigma=\$10$), 20% Uniform random MCCs.
* **UPI Background (Internal Indian Context):**
  * Geo: `IN` only.
  * Time: 80% volume during IST business hours (09:00 - 21:00).
  * Amounts: 70% P2M ($\mu=₹500$, $\sigma=₹200$), 30% P2P ($\mu=₹2000$, $\sigma=₹1000$).
* **Power-Law Graph:** Merchant and payee in-degree connectivity must follow a Pareto distribution ($a=1.5$).