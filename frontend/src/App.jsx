import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

const CYCLE_STEPS = ["Identify", "Simulate", "Detect", "Mutate"];

const SCALE_PRESETS = [
  { id: "demo", label: "Small · 3 days · 80 accounts", n_days: 3, num_users: 80 },
  { id: "gff", label: "Pilot · 30 days · 1,500 accounts", n_days: 30, num_users: 1500 },
  { id: "spec", label: "Full scale · 90 days · 10,000 accounts", n_days: 90, num_users: 10000 },
];

const MAX_RETAINED_RUNS = 8;

const FEATURE_LABELS = {
  prior_tx_count: "Account history length",
  count_tx_1h: "Payments in the last hour",
  sum_amount_24h: "24-hour spend total",
  last_5_amounts: "Average of last 5 payments",
  last_10_mccs: "Merchant variety, last 10 payments",
  geo_mismatch: "Device/merchant country mismatch",
  velocity_spike: "Unusual payment velocity",
  v_cip_injection_flag: "V-CIP deepfake injection flag",
  browser_dom_anomaly_score: "Browser automation score",
  remittance_prompt_score: "Payment-note risk score",
};

function featureLabel(name) {
  return FEATURE_LABELS[name] ?? name;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function requestCycleStream(onStage, request) {
  const response = await fetch("/api/cycle/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // keep status-line fallback
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  if (!response.body) throw new Error("Lab stage stream is unavailable.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result;

  const consume = async (packet) => {
    if (!packet.trim()) return;
    const fields = Object.fromEntries(packet.split("\n").flatMap((line) => {
      const separator = line.indexOf(": ");
      return separator === -1 ? [] : [[line.slice(0, separator), line.slice(separator + 2)]];
    }));
    const data = JSON.parse(fields.data);
    if (fields.event === "stage") await onStage(data);
    if (fields.event === "result") result = data;
    if (fields.event === "error") throw new Error(data.detail);
  };

  while (true) {
    const { value, done } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: !done });
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      await consume(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  await consume(buffer);
  if (!result) throw new Error("Lab stage stream ended before the Cycle artifact.");
  return result;
}

function decimal(value, digits = 3) {
  return value == null ? "Unavailable" : Number(value).toFixed(digits);
}

export default function App() {
  const ontology = useQuery({ queryKey: ["ontology"], queryFn: () => requestJson("/api/ontology") });
  const [stageEvents, setStageEvents] = useState([]);
  const [runs, setRuns] = useState([]);
  const [viewedRunId, setViewedRunId] = useState(null);
  const [seed, setSeed] = useState(1);
  const [scaleId, setScaleId] = useState("demo");
  const [railFilter, setRailFilter] = useState("all");
  const [modeFilter, setModeFilter] = useState("all");
  const stageRef = useRef([]);
  const cycle = useMutation({
    mutationFn: () => {
      const preset = SCALE_PRESETS.find((preset) => preset.id === scaleId) ?? SCALE_PRESETS[0];
      const startedAt = Date.now();
      return requestCycleStream(async (event) => {
        setStageEvents((events) => {
          const next = [...events, event];
          stageRef.current = next;
          return next;
        });
        await afterPaint();
      }, { seed, n_days: preset.n_days, num_users: preset.num_users }).then((artifact) => ({ artifact, meta: { seed, preset, startedAt } }));
    },
    onMutate: () => {
      stageRef.current = [];
      setStageEvents([]);
      setViewedRunId(null);
    },
    onSuccess: ({ artifact, meta }) => {
      const run = {
        id: `${meta.startedAt}-${meta.seed}`,
        seed: meta.seed,
        scaleLabel: meta.preset.label,
        startedAt: meta.startedAt,
        artifact,
        stageEvents: stageRef.current,
      };
      setRuns((previous) => [...previous, run].slice(-MAX_RETAINED_RUNS));
      setViewedRunId(run.id);
    },
  });
  const viewedRun = runs.find((run) => run.id === viewedRunId) ?? runs.at(-1) ?? null;
  const result = viewedRun?.artifact ?? null;
  const vectors = ontology.data ?? [];
  const simulated = vectors.filter((vector) => vector.status === "simulated").length;
  const activeStage = stageEvents.at(-1)?.stage;
  const filteredVectors = vectors.filter(
    (vector) => (railFilter === "all" || vector.rail === railFilter) && (modeFilter === "all" || vector.status === modeFilter),
  );

  function startCycle() {
    cycle.mutate();
  }

  function selectRun(run) {
    setViewedRunId(run.id);
    setStageEvents(run.stageEvents);
  }

  return (
    <main className="lab-shell">
      <header className="masthead">
        <p className="eyebrow">CRUCIBLE / PAYMENT FRAUD READINESS</p>
        <div className="masthead-line">
          <h1>Find out how your payments hold up to AI-driven fraud — before it happens.</h1>
          <p>
            Crucible generates realistic card and UPI payment traffic, injects AI-driven attack crews, screens every
            payment with a live detection policy, and shows you exactly what was decided and why. Everything runs
            offline on this server; no real payment data is used.
          </p>
        </div>
      </header>

      <section className="cycle-panel" aria-label="Run an assessment">
        <div className="cycle-track">
          {CYCLE_STEPS.map((step, index) => (
            <div className={`cycle-step ${stageClass(index, stageEvents, cycle.isPending, Boolean(result) && !cycle.isPending)}`} key={step}>
              <span>{stageMark(index, stageEvents, cycle.isPending, Boolean(result) && !cycle.isPending)}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
        <div className="cycle-action">
          <div className="cycle-controls">
            <label className="seed-control">
              Scenario seed
              <input
                aria-label="Scenario seed"
                type="number"
                min={1}
                value={seed}
                disabled={cycle.isPending}
                onChange={(event) => setSeed(Number(event.target.value) || 1)}
              />
            </label>
            <label className="scale-control">
              Traffic volume
              <select
                aria-label="Traffic volume"
                value={scaleId}
                disabled={cycle.isPending}
                onChange={(event) => setScaleId(event.target.value)}
              >
                {SCALE_PRESETS.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}
              </select>
            </label>
            <button type="button" onClick={startCycle} disabled={cycle.isPending}>
              {cycle.isPending ? "Running assessment…" : "Run assessment"}
            </button>
          </div>
          <p>
            {cycle.isPending
              ? "Generating traffic and screening payments — progress streams in below."
              : result
                ? "Results below. Change the seed or volume and run again to compare scenarios."
                : "Each seed produces a different attack scenario. The same seed always reproduces the same scenario."}
          </p>
        </div>
      </section>

      {cycle.isError && <ErrorPanel error={cycle.error} />}
      {runs.length === 0 && !cycle.isPending && !cycle.isError && <GetStarted />}
      {(cycle.isPending || (result && stageEvents.length > 0)) && (
        <LiveCycleTrace events={stageEvents} activeStage={activeStage} complete={!cycle.isPending && Boolean(result)} />
      )}
      {result && <AssessmentOutcome result={result} />}
      {runs.length > 0 && <RunLedger runs={runs} viewedRunId={viewedRun?.id} onSelect={selectRun} pending={cycle.isPending} />}

      <section className="ledger" aria-label="Attack library">
        <div className="ledger-head">
          <div>
            <p className="eyebrow">ATTACK LIBRARY</p>
            <h2>Attack types Crucible can simulate</h2>
            <p className="stage-note">
              Simulated crews generate realistic fraudulent payments. Playbook types are catalogued attack patterns
              available for future simulation.
            </p>
          </div>
          <div className="readouts" aria-live="polite">
            <span><b>{vectors.length}</b> attack types</span>
            <span><b>{simulated}</b> simulated now</span>
            <span><b>{Math.max(0, vectors.length - simulated)}</b> in playbook</span>
          </div>
        </div>

        {ontology.isError && <p className="error">Attack library unavailable: {ontology.error.message}. Start Crucible API and retry.</p>}
        {ontology.isLoading && <p className="loading">Loading attack library…</p>}
        {!ontology.isLoading && !ontology.isError && (
          <>
            <div className="filter-chips" aria-label="Attack library filters">
              {["all", "card", "upi"].map((rail) => (
                <button type="button" key={rail} className={`chip ${railFilter === rail ? "chip-active" : ""}`} onClick={() => setRailFilter(rail)}>
                  {rail === "all" ? "All rails" : rail}
                </button>
              ))}
              {["all", "simulated", "playbook"].map((mode) => (
                <button type="button" key={mode} className={`chip ${modeFilter === mode ? "chip-active" : ""}`} onClick={() => setModeFilter(mode)}>
                  {mode === "all" ? "All modes" : mode}
                </button>
              ))}
              <span className="filter-count">{filteredVectors.length} shown</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Attack</th><th>Family</th><th>Rail</th><th>Mode</th></tr></thead>
                <tbody>
                  {filteredVectors.map((vector) => (
                    <tr key={vector.id}>
                      <td><code>{vector.id}</code></td>
                      <td>{vector.family}</td>
                      <td><span className={`rail rail-${vector.rail}`}>{vector.rail}</span></td>
                      <td><span className={`mode mode-${vector.status}`}>{vector.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

function afterPaint() {
  const schedule = globalThis.requestAnimationFrame ?? ((callback) => setTimeout(callback, 0));
  return new Promise((resolve) => schedule(() => schedule(resolve)));
}

function ErrorPanel({ error }) {
  if (error?.status === 409) {
    return (
      <p className="error" role="alert">
        An assessment is already running — only one executes at a time so results stay reproducible.
        Wait for it to finish, then run again.
      </p>
    );
  }
  if (error?.status === 429) {
    return (
      <p className="error" role="alert">
        Too many assessments in a short window (8 per minute). Wait a moment, then run again.
      </p>
    );
  }
  return <p className="error" role="alert">Assessment failed: {error?.message ?? "unknown error"}. Check API output and retry.</p>;
}

function GetStarted() {
  return (
    <section className="first-run" aria-label="Getting started">
      <p className="eyebrow">GETTING STARTED</p>
      <h2>Run your first assessment in three steps.</h2>
      <ol className="first-run-steps">
        <li><strong>Run an assessment.</strong> Crucible generates dual-rail payment traffic, injects eight AI-driven attack crews, and screens every payment against the policy: DECLINE, HOLD, STEP_UP, or APPROVE.</li>
        <li><strong>Review the outcome.</strong> See how many attacks were caught, what fraud was approved and at what loss, and how many legitimate payments were affected.</li>
        <li><strong>Investigate any decision.</strong> Open a flagged or missed payment to see what drove its risk score — then change the seed and compare runs in the history below.</li>
      </ol>
    </section>
  );
}

function LiveCycleTrace({ events, activeStage, complete }) {
  const activeIndex = CYCLE_STEPS.indexOf(activeStage);
  const activeEvent = events.at(-1);
  return (
    <section className={`live-cycle ${complete ? "trace-finished" : ""}`} aria-label={complete ? "Completed assessment trace" : "Assessment progress"} aria-live="polite">
      <div className="trace-scan" aria-hidden="true" />
      <p className="eyebrow">{complete ? "ASSESSMENT COMPLETE / PROCESS RECORD" : "IN PROGRESS / SERVER EVENTS"}</p>
      {complete ? <h2>Assessment complete. {events.length} process stages recorded.</h2> : activeEvent ? <h2>{activeEvent.stage} / {activeEvent.status}</h2> : <h2>Opening server event stream…</h2>}
      <ol className="trace-list">
        {CYCLE_STEPS.map((stage, index) => {
          const event = events.find((entry) => entry.stage === stage);
          const state = complete || index < activeIndex ? "complete" : index === activeIndex ? "active" : "queued";
          return (
            <li className={`trace-event trace-${state}`} key={stage}>
              <span>{state === "complete" ? "✓" : String(index + 1).padStart(2, "0")}</span>
              <div>
                <strong>{stage}</strong>
                {event && (
                  <p>
                    {event.status}
                    {event.elapsed_ms != null && <span className="stage-elapsed"> +{(event.elapsed_ms / 1000).toFixed(1)}s server-side</span>}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function stageClass(index, events, isRunning, hasResult) {
  const activeIndex = CYCLE_STEPS.indexOf(events.at(-1)?.stage);
  if (hasResult) return "stage-complete";
  if (!isRunning) return index === 0 ? "stage-ready" : "stage-queued";
  if (index < activeIndex) return "stage-complete";
  if (index === activeIndex) return "stage-active";
  return "stage-queued";
}

function stageMark(index, events, isRunning, hasResult) {
  return stageClass(index, events, isRunning, hasResult) === "stage-complete"
    ? "✓"
    : String(index + 1).padStart(2, "0");
}

function AssessmentOutcome({ result }) {
  const { generation, detection, mutation, evidence } = result;
  const attacks = detection.family_efficacy ?? [];
  const attackTotal = attacks.reduce((total, row) => total + row.test_positive_count, 0);
  const attackCaught = attacks.reduce((total, row) => total + row.test_caught_count, 0);
  const approvedFraud = attacks.reduce((total, row) => total + row.approve_miss_count, 0);
  const caughtPct = attackTotal ? Math.round((attackCaught / attackTotal) * 100) : null;
  const fidelityGates = [
    { name: "Grocery KS", pvalue: generation.grocery_ks_pvalue },
    { name: "Dining KS", pvalue: generation.dining_ks_pvalue },
    { name: "P2M KS", pvalue: generation.p2m_ks_pvalue },
    { name: "P2P KS", pvalue: generation.p2p_ks_pvalue },
  ];
  const maxShap = Math.max(...detection.shap_top_features.map((feature) => feature.mean_abs_shap), 1);

  return (
    <section className="evidence" aria-label="Assessment results" aria-live="polite">
      <header className="evidence-head">
        <p className="eyebrow">RESULTS / MOST RECENT ASSESSMENT</p>
        <h2>Screening outcome</h2>
      </header>

      <div className="outcome-strip" aria-label="Outcome summary">
        <div className="outcome-cell">
          <dt>Attacks caught</dt>
          <dd>{caughtPct == null ? "—" : `${caughtPct}%`}</dd>
          <p>{attackCaught} of {attackTotal} fraudulent payments scored above the decline threshold</p>
        </div>
        <div className="outcome-cell">
          <dt>Approved fraud</dt>
          <dd>{approvedFraud}</dd>
          <p>${decimal(detection.expected_loss_usd, 2)} in fraudulent payments approved</p>
        </div>
        <div className="outcome-cell">
          <dt>Legitimate declined</dt>
          <dd>{detection.test_fpr_at_operating_point == null ? "—" : `${(detection.test_fpr_at_operating_point * 100).toFixed(2)}%`}</dd>
          <p>Share of legitimate payments declined on the held-out window</p>
        </div>
        <div className="outcome-cell">
          <dt>Payments screened</dt>
          <dd>{generation.event_count.toLocaleString()}</dd>
          <p>{generation.fraud_event_count.toLocaleString()} fraudulent · {detection.test_event_count.toLocaleString()} in held-out window</p>
        </div>
      </div>

      <div className="decision-strip outcome-decisions">
        {Object.entries(detection.decision_counts).map(([decision, count]) => <span key={decision}><b>{count}</b> {decision}</span>)}
      </div>

      {evidence && <TransactionReview evidence={evidence} />}
      {attacks.length > 0 && <AttackTypeTable rows={attacks} />}

      <div className="evidence-tape">
        <article className="evidence-stage stage-generate">
          <p className="stage-index">02 / SIMULATE</p>
          <h3>Test traffic</h3>
          <dl className="metric-grid">
            <div><dt>Payments</dt><dd>{generation.event_count.toLocaleString()}</dd></div>
            <div><dt>Attack payments</dt><dd>{generation.fraud_event_count.toLocaleString()}</dd></div>
            <div><dt>Attack crews</dt><dd>{generation.active_crew_count}</dd></div>
          </dl>
          <div className="rail-split">
            {Object.entries(generation.rail_counts).map(([rail, count]) => <span key={rail}><b>{count.toLocaleString()}</b> {rail}</span>)}
          </div>
          <details className="tech-detail">
            <summary>Traffic realism checks</summary>
            <div className="fidelity-gates" aria-label="Fidelity gates">
              {fidelityGates.map((gate) => <GateChip key={gate.name} name={gate.name} pvalue={gate.pvalue} />)}
              <span className={`gate ${generation.ist_business_hours_pass ? "gate-pass" : "gate-fail"}`}>
                IST business hours {generation.ist_business_hour_share != null ? `${Math.round(generation.ist_business_hour_share * 100)}%` : "—"}
              </span>
              <span className={`gate gate-overall ${generation.fidelity_pass == null ? "gate-skip" : generation.fidelity_pass ? "gate-pass" : "gate-fail"}`}>
                {generation.fidelity_pass == null ? "Sample too small" : `Distributions match ${generation.fidelity_pass ? "yes" : "no"} (${generation.fidelity_gate_count} checks)`}
              </span>
            </div>
            <p className="stage-note">KS goodness-of-fit against the declared generating distributions; p &gt; 0.05 means the simulated traffic is statistically consistent with its specification.</p>
          </details>
        </article>

        <article className="evidence-stage stage-detect">
          <p className="stage-index">03 / DETECT</p>
          <h3>Screening policy</h3>
          <p className="split-line"><b>{detection.train_event_count.toLocaleString()}</b> Train · <b>{detection.validation_event_count.toLocaleString()}</b> Val · <b>{detection.test_event_count.toLocaleString()}</b> held-out Test</p>
          <div className="shap-list">
            <p className="shap-label">Strongest risk signals this run</p>
            {detection.shap_top_features.slice(0, 5).map((feature) => (
              <div className="shap-row" key={feature.feature}>
                <code>{featureLabel(feature.feature)}</code>
                <span><i style={{ width: `${(feature.mean_abs_shap / maxShap) * 100}%` }} /></span>
                <b>{decimal(feature.mean_abs_shap)}</b>
              </div>
            ))}
          </div>
          <details className="tech-detail">
            <summary>Model detail</summary>
            <p className="stage-note">
              Decline threshold {decimal(detection.operating_point)} — selected on validation at a 1% false-positive
              budget ({(detection.validation_fpr_at_operating_point * 100).toFixed(2)}% observed). Held-out test FPR
              {(detection.test_fpr_at_operating_point * 100).toFixed(2)}%. {detection.delayed_card_fraud_count} card
              fraud labels ({Math.round(detection.delayed_card_fraud_share * 100)}%) only became available after a
              45-day chargeback lag and were excluded from training.
            </p>
          </details>
        </article>

        <article className="evidence-stage stage-mutate">
          <p className="stage-index">04 / MUTATE</p>
          <h3>Feedback pass</h3>
          <p className="mutation-status"><MutationMessage mutation={mutation} /></p>
          <dl className="metric-grid">
            <div><dt>Approved fraud reviewed</dt><dd>{mutation.in_sample_approve_miss_count}</dd></div>
            <div><dt>Retraining result</dt><dd>{mutation.delta_pr_auc == null ? "—" : `${mutation.delta_pr_auc >= 0 ? "+" : ""}${decimal(mutation.delta_pr_auc)}`}</dd></div>
          </dl>
          {mutation.mutated_config && <p className="stage-note">The attack crew was tightened and the detector retrained on the original training window only; the held-out test was never regenerated.</p>}
          {!mutation.mutated_config && <p className="stage-note">No crew was changed — either no eligible approved fraud existed, or holdout attacks are excluded from retraining by design.</p>}
          <details className="tech-detail">
            <summary>Model detail</summary>
            <p className="stage-note">Δ PR-AUC on the frozen held-out window after SHAP-guided crew mutation and retraining. Negative or zero deltas are reported as-is.</p>
          </details>
        </article>
      </div>
    </section>
  );
}

function MutationMessage({ mutation }) {
  if (mutation.status === "mutated_and_retrained") {
    return <>Crew <code>{mutation.selected_family}</code> tightened and detector retrained.</>;
  }
  return <>No retraining triggered this run</>;
}

function GateChip({ name, pvalue }) {
  const state = pvalue == null ? "gate-skip" : pvalue > 0.05 ? "gate-pass" : "gate-fail";
  const label = pvalue == null ? `${name} — sample too small` : `${name} p=${decimal(pvalue, 2)}`;
  return <span className={`gate ${state}`}>{label}</span>;
}

function AttackTypeTable({ rows }) {
  const ordered = [...rows].sort((a, b) => Number(b.zero_day) - Number(a.zero_day) || (b.test_recall ?? 0) - (a.test_recall ?? 0));
  const group = (rows_) => {
    const positives = rows_.reduce((total, row) => total + row.test_positive_count, 0);
    const caught = rows_.reduce((total, row) => total + row.test_caught_count, 0);
    return positives ? caught / positives : null;
  };
  const seen = ordered.filter((row) => !row.zero_day);
  const unseen = ordered.filter((row) => row.zero_day);
  return (
    <div className="table-wrap efficacy-wrap" aria-label="Results by attack type">
      <p className="shap-label">Results by attack type</p>
      <table>
        <thead>
          <tr><th>Attack type</th><th>Rail</th><th>Training exposure</th><th>In held-out test</th><th>Caught</th><th>Approved (missed)</th></tr>
        </thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row.family}>
              <td><code>{row.family}</code></td>
              <td><span className={`rail rail-${row.rail}`}>{row.rail}</span></td>
              <td>{row.zero_day ? "Never seen in training" : "Seen in training"}</td>
              <td>{row.test_positive_count}</td>
              <td>{row.test_recall == null ? "—" : `${Math.round(row.test_recall * 100)}%`}</td>
              <td>{row.approve_miss_count}</td>
            </tr>
          ))}
          <tr className="efficacy-summary">
            <td colSpan={3}>Seen in training — combined</td>
            <td>{seen.reduce((total, row) => total + row.test_positive_count, 0)}</td>
            <td>{group(seen) == null ? "—" : `${Math.round(group(seen) * 100)}%`}</td>
            <td>{seen.reduce((total, row) => total + row.approve_miss_count, 0)}</td>
          </tr>
          <tr className="efficacy-summary">
            <td colSpan={3}>Never seen in training — combined</td>
            <td>{unseen.reduce((total, row) => total + row.test_positive_count, 0)}</td>
            <td>{group(unseen) == null ? "—" : `${Math.round(group(unseen) * 100)}%`}</td>
            <td>{unseen.reduce((total, row) => total + row.approve_miss_count, 0)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function WhyDetails({ event }) {
  if (!event.top_shap?.length) return <span className="stage-note">—</span>;
  return (
    <details className="why-details">
      <summary>Why this decision</summary>
      <span className="why-cell">
        {event.top_shap.map((item) => (
          <span key={item.feature} className={`shap-chip ${item.contribution >= 0 ? "shap-pos" : "shap-neg"}`}>
            <span className="why-label">{featureLabel(item.feature)}</span>
            <code>{item.feature}</code>
            <b>{item.contribution >= 0 ? "+" : ""}{item.contribution.toFixed(2)}</b>
          </span>
        ))}
      </span>
      <p className="stage-note">
        Signed contributions to this payment&apos;s risk score — positive pushed the score up, negative pulled it down.
      </p>
    </details>
  );
}

function TransactionReview({ evidence }) {
  const header = (
    <tr><th>Account token</th><th>Attack type</th><th>Rail</th><th>Amount</th><th>Decision</th><th>Risk score</th><th>Reasoning</th></tr>
  );
  return (
    <div className="event-evidence" aria-label="Payment decisions to inspect">
      <div className="event-evidence-block">
        <p className="shap-label">Highest-risk declined payments</p>
        <div className="table-wrap">
          <table>
            <thead>{header}</thead>
            <tbody>
              {evidence.top_catches.map((event) => (
                <tr key={event.event_id}>
                  <td><code>{event.entity_token}</code></td>
                  <td>{event.family}</td>
                  <td><span className={`rail rail-${event.rail}`}>{event.rail}</span></td>
                  <td>${decimal(event.amount_usd, 2)}</td>
                  <td><span className={`decision-${event.decision.toLowerCase()}`}>{event.decision}</span></td>
                  <td>{decimal(event.score)}</td>
                  <td><WhyDetails event={event} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="event-evidence-block">
        <p className="shap-label">Fraudulent payments approved — review these first</p>
        {evidence.approved_misses.length === 0
          ? <p className="stage-note">No fraudulent payments were approved this run.</p>
          : (
            <div className="table-wrap">
              <table>
                <thead>{header}</thead>
                <tbody>
                  {evidence.approved_misses.map((event) => (
                    <tr key={event.event_id}>
                      <td><code>{event.entity_token}</code></td>
                      <td>{event.family}</td>
                      <td><span className={`rail rail-${event.rail}`}>{event.rail}</span></td>
                      <td>${decimal(event.amount_usd, 2)}</td>
                      <td><span className="decision-approve">{event.decision}</span></td>
                      <td>{decimal(event.score)}</td>
                      <td><WhyDetails event={event} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}

function RunLedger({ runs, viewedRunId, onSelect, pending }) {
  return (
    <section className="run-ledger" aria-label="Assessment history">
      <div className="ledger-head">
        <div>
          <p className="eyebrow">HISTORY</p>
          <h2>{runs.length} assessment{runs.length === 1 ? "" : "s"} — click a row to reopen</h2>
        </div>
        <p className="stage-note">Each row compares its detection quality against the run above it, so you can see what a seed or volume change did.</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>#</th><th>Seed</th><th>Volume</th><th>Detection quality (PR-AUC)</th><th>Legitimate declined</th><th>Attacks caught @ 1% FPR</th><th>Change vs previous</th><th>Started</th></tr>
          </thead>
          <tbody>
            {runs.map((run, index) => {
              const detection = run.artifact.detection;
              const previous = index > 0 ? runs[index - 1].artifact.detection : null;
              const delta = previous?.pr_auc != null && detection.pr_auc != null ? detection.pr_auc - previous.pr_auc : null;
              return (
                <tr className={run.id === viewedRunId && !pending ? "run-viewed" : ""} key={run.id}>
                  <td><button type="button" className="run-select" onClick={() => onSelect(run)} aria-label={`View run ${index + 1}`}>{index + 1}</button></td>
                  <td>{run.seed}</td>
                  <td>{run.scaleLabel}</td>
                  <td>{decimal(detection.pr_auc)}</td>
                  <td>{detection.test_fpr_at_operating_point == null ? "—" : `${(detection.test_fpr_at_operating_point * 100).toFixed(2)}%`}</td>
                  <td>{detection.recall_at_1pct_fpr == null ? "—" : `${Math.round(detection.recall_at_1pct_fpr * 100)}%`}</td>
                  <td>{delta == null ? "—" : <span className={delta >= 0 ? "delta-pos" : "delta-neg"}>{delta >= 0 ? "+" : ""}{delta.toFixed(3)}</span>}</td>
                  <td>{new Date(run.startedAt).toLocaleTimeString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
