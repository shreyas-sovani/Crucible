import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

const CYCLE_STEPS = ["Identify", "Simulate", "Detect", "Mutate"];

const SCALE_PRESETS = [
  { id: "demo", label: "Demo · 3d × 80 users", n_days: 3, num_users: 80 },
  { id: "gff", label: "GFF scale · 30d × 1,500 users", n_days: 30, num_users: 1500 },
  { id: "spec", label: "Spec scale · 90d × 10,000 users", n_days: 90, num_users: 10000 },
];

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
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
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

function MutationMessage({ mutation }) {
  if (mutation.status === "mutated_and_retrained") {
    return <>Mutated <code>{mutation.selected_family}</code>; frozen-Test Δ PR-AUC {decimal(mutation.delta_pr_auc)}.</>;
  }
  return <>No in-sample APPROVE misses</>;
}

export default function App() {
  const ontology = useQuery({ queryKey: ["ontology"], queryFn: () => requestJson("/api/ontology") });
  const [stageEvents, setStageEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [seed, setSeed] = useState(1);
  const [scaleId, setScaleId] = useState("demo");
  const cycle = useMutation({
    mutationFn: () => {
      const preset = SCALE_PRESETS.find((preset) => preset.id === scaleId) ?? SCALE_PRESETS[0];
      return requestCycleStream(async (event) => {
        setStageEvents((events) => [...events, event]);
        await afterPaint();
      }, { seed, n_days: preset.n_days, num_users: preset.num_users });
    },
    onMutate: () => {
      setStageEvents([]);
      setResult(null);
    },
    onSuccess: setResult,
  });
  const vectors = ontology.data ?? [];
  const simulated = vectors.filter((vector) => vector.status === "simulated").length;
  const activeStage = stageEvents.at(-1)?.stage;

  function startCycle() {
    cycle.mutate();
  }

  return (
    <main className="lab-shell">
      <header className="masthead">
        <p className="eyebrow">CRUCIBLE / CLOSED-LOOP FRAUD LAB</p>
        <div className="masthead-line">
          <h1>Adversarial payment signals, under glass.</h1>
          <p>Offline dual-rail simulation. Each run shows generated Evidence, frozen-Test defense, and honest mutation outcome.</p>
        </div>
      </header>

      <section className="cycle-panel" aria-label="Crucible closed loop">
        <div className="cycle-track">
          {CYCLE_STEPS.map((step, index) => (
            <div className={`cycle-step ${stageClass(index, stageEvents, cycle.isPending, Boolean(result))}`} key={step}>
              <span>{stageMark(index, stageEvents, cycle.isPending, Boolean(result))}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
        <div className="cycle-action">
          <div className="cycle-controls">
            <label className="seed-control">
              Seed
              <input
                aria-label="Cycle seed"
                type="number"
                min={1}
                value={seed}
                disabled={cycle.isPending}
                onChange={(event) => setSeed(Number(event.target.value) || 1)}
              />
            </label>
            <label className="scale-control">
              World scale
              <select
                aria-label="World scale"
                value={scaleId}
                disabled={cycle.isPending}
                onChange={(event) => setScaleId(event.target.value)}
              >
                {SCALE_PRESETS.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}
              </select>
            </label>
            <button type="button" onClick={startCycle} disabled={cycle.isPending}>
              {cycle.isPending ? "Running real cycle…" : "Run full offline cycle"}
            </button>
          </div>
          <p>{cycle.isPending ? "Streaming actual backend stage events." : result ? "Seeded Evidence below. Test window stays frozen through mutation." : "Uses eight simulated crews. No external rails. No API key."}</p>
        </div>
      </section>

      {cycle.isError && <p className="error">Cycle failed: {cycle.error.message}. Check API output and retry.</p>}
      {(cycle.isPending || (result && stageEvents.length > 0)) && <LiveCycleTrace events={stageEvents} activeStage={activeStage} complete={Boolean(result)} />}
      {result && <CycleEvidence result={result} />}

      <section className="ledger" aria-label="Attack ontology">
        <div className="ledger-head">
          <div>
            <p className="eyebrow">IDENTIFY / ONTOLOGY</p>
            <h2>Attack vector ledger</h2>
          </div>
          <div className="readouts" aria-live="polite">
            <span><b>{vectors.length}</b> vectors</span>
            <span><b>{simulated}</b> simulated crews</span>
            <span><b>{Math.max(0, vectors.length - simulated)}</b> playbooks</span>
          </div>
        </div>

        {ontology.isError && <p className="error">Ontology unavailable: {ontology.error.message}. Start Crucible API and retry.</p>}
        {ontology.isLoading && <p className="loading">Loading validated ontology…</p>}
        {!ontology.isLoading && !ontology.isError && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Vector</th><th>Family</th><th>Rail</th><th>Mode</th></tr></thead>
              <tbody>
                {vectors.map((vector) => (
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
        )}
      </section>
    </main>
  );
}

function afterPaint() {
  const schedule = globalThis.requestAnimationFrame ?? ((callback) => setTimeout(callback, 0));
  return new Promise((resolve) => schedule(() => schedule(resolve)));
}

function LiveCycleTrace({ events, activeStage, complete }) {
  const activeIndex = CYCLE_STEPS.indexOf(activeStage);
  const activeEvent = events.at(-1);
  return (
    <section className={`live-cycle ${complete ? "trace-finished" : ""}`} aria-label={complete ? "Completed Cycle trace" : "Live Cycle trace"} aria-live="polite">
      <div className="trace-scan" aria-hidden="true" />
      <p className="eyebrow">{complete ? "CYCLE COMPLETE / RETAINED BACKEND TRACE" : "LIVE LAB TRACE / BACKEND EVENT STREAM"}</p>
      {complete ? <h2>Cycle complete. {events.length} backend stages retained for review.</h2> : activeEvent ? <h2>{activeEvent.stage} / {activeEvent.status}</h2> : <h2>Opening Lab stage stream…</h2>}
      <ol className="trace-list">
        {CYCLE_STEPS.map((stage, index) => {
          const event = events.find((entry) => entry.stage === stage);
          const state = complete || index < activeIndex ? "complete" : index === activeIndex ? "active" : "queued";
          return (
            <li className={`trace-event trace-${state}`} key={stage}>
              <span>{state === "complete" ? "✓" : String(index + 1).padStart(2, "0")}</span>
              <div><strong>{stage}</strong>{event && <p>{event.status}</p>}</div>
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

function CycleEvidence({ result }) {
  const { generation, detection, mutation, evidence } = result;
  const maxShap = Math.max(...detection.shap_top_features.map((feature) => feature.mean_abs_shap), 1);
  const fidelityGates = [
    { name: "Grocery KS", pvalue: generation.grocery_ks_pvalue },
    { name: "Dining KS", pvalue: generation.dining_ks_pvalue },
    { name: "P2M KS", pvalue: generation.p2m_ks_pvalue },
    { name: "P2P KS", pvalue: generation.p2p_ks_pvalue },
  ];
  return (
    <section className="evidence" aria-label="Closed cycle evidence" aria-live="polite">
      <header className="evidence-head">
        <p className="eyebrow">EVIDENCE TAPE / SEE EACH REAL STAGE</p>
        <h2>One run. One frozen Test.</h2>
      </header>
      <div className="evidence-tape">
        <article className="evidence-stage stage-generate">
          <p className="stage-index">02 / SIMULATE</p>
          <h3>Generated world</h3>
          <dl className="metric-grid">
            <div><dt>Events</dt><dd>{generation.event_count}</dd></div>
            <div><dt>Fraud overlays</dt><dd>{generation.fraud_event_count}</dd></div>
            <div><dt>Active crews</dt><dd>{generation.active_crew_count}</dd></div>
          </dl>
          <div className="fidelity-gates" aria-label="Fidelity gates">
            {fidelityGates.map((gate) => <GateChip key={gate.name} name={gate.name} pvalue={gate.pvalue} />)}
            <span className={`gate ${generation.ist_business_hours_pass ? "gate-pass" : "gate-fail"}`}>
              IST hours {generation.ist_business_hour_share != null ? `${Math.round(generation.ist_business_hour_share * 100)}%` : "—"}
            </span>
            <span className={`gate gate-overall ${generation.fidelity_pass == null ? "gate-skip" : generation.fidelity_pass ? "gate-pass" : "gate-fail"}`}>
              {generation.fidelity_pass == null ? "Fidelity: sample too small" : `Fidelity ${generation.fidelity_pass ? "PASS" : "FAIL"} (${generation.fidelity_gate_count} gates)`}
            </span>
          </div>
          <div className="rail-split">
            {Object.entries(generation.rail_counts).map(([rail, count]) => <span key={rail}><b>{count}</b> {rail}</span>)}
          </div>
        </article>

        <article className="evidence-stage stage-detect">
          <p className="stage-index">03 / DETECT</p>
          <h2>Detection / frozen Test</h2>
          <p className="split-line"><b>{detection.train_event_count}</b> Train · <b>{detection.validation_event_count}</b> Val · <b>{detection.test_event_count}</b> Test</p>
          <dl className="metric-grid metric-grid-wide">
            <div><dt>PR-AUC</dt><dd>{decimal(detection.pr_auc)}</dd></div>
            <div><dt>ROC-AUC</dt><dd>{decimal(detection.roc_auc)}</dd></div>
            <div><dt>Recall @ 1% FPR</dt><dd>{decimal(detection.recall_at_1pct_fpr)}</dd></div>
            <div><dt>Expected loss</dt><dd>${decimal(detection.expected_loss_usd, 2)}</dd></div>
          </dl>
          <p className="stage-note">OP {decimal(detection.operating_point)} · zero-day positives in Train/Val: {detection.zero_day_train_positive_count}/{detection.zero_day_validation_positive_count} · delayed card labels: {detection.delayed_card_fraud_count} ({Math.round(detection.delayed_card_fraud_share * 100)}% of card fraud, 45-day chargeback lag).</p>
          <div className="decision-strip">
            {Object.entries(detection.decision_counts).map(([decision, count]) => <span key={decision}><b>{count}</b> {decision}</span>)}
          </div>
          <div className="shap-list">
            <p className="shap-label">Top TreeSHAP signals</p>
            {detection.shap_top_features.slice(0, 5).map((feature) => (
              <div className="shap-row" key={feature.feature}>
                <code>{feature.feature}</code>
                <span><i style={{ width: `${(feature.mean_abs_shap / maxShap) * 100}%` }} /></span>
                <b>{decimal(feature.mean_abs_shap)}</b>
              </div>
            ))}
          </div>
        </article>

        <article className="evidence-stage stage-mutate">
          <p className="stage-index">04 / MUTATE</p>
          <h3>Feedback outcome</h3>
          <p className="mutation-status"><MutationMessage mutation={mutation} /></p>
          <dl className="metric-grid">
            <div><dt>Eligible misses</dt><dd>{mutation.in_sample_approve_miss_count}</dd></div>
            <div><dt>Δ PR-AUC</dt><dd>{decimal(mutation.delta_pr_auc)}</dd></div>
          </dl>
          {mutation.mutated_config && <p className="stage-note">Bound changed: {mutation.original_config.amount_bounds[1]} → {mutation.mutated_config.amount_bounds[1]}. Only Train was resimulated; Test scores stay frozen.</p>}
          {!mutation.mutated_config && <p className="stage-note">No config changed. Holdout families are never eligible for mutation.</p>}
        </article>
      </div>

      {detection.family_efficacy?.length > 0 && <FamilyEfficacyTable rows={detection.family_efficacy} />}
      {evidence && <EventEvidence evidence={evidence} />}
    </section>
  );
}

function GateChip({ name, pvalue }) {
  const state = pvalue == null ? "gate-skip" : pvalue > 0.05 ? "gate-pass" : "gate-fail";
  const label = pvalue == null ? `${name} n<50 skip` : `${name} p=${decimal(pvalue, 2)}`;
  return <span className={`gate ${state}`}>{label}</span>;
}

function FamilyEfficacyTable({ rows }) {
  const ordered = [...rows].sort((a, b) => Number(b.zero_day) - Number(a.zero_day) || (b.test_recall ?? 0) - (a.test_recall ?? 0));
  const inSample = ordered.filter((row) => !row.zero_day);
  const zeroDay = ordered.filter((row) => row.zero_day);
  const recall = (rows_) => {
    const positives = rows_.reduce((total, row) => total + row.test_positive_count, 0);
    const caught = rows_.reduce((total, row) => total + row.test_caught_count, 0);
    return positives ? caught / positives : null;
  };
  return (
    <div className="table-wrap efficacy-wrap" aria-label="Per-family frozen-Test efficacy">
      <table>
        <thead>
          <tr><th>Family</th><th>Rail</th><th>Mode</th><th>Test positives</th><th>Recall @ OP</th><th>APPROVE misses</th></tr>
        </thead>
        <tbody>
          {ordered.map((row) => (
            <tr key={row.family}>
              <td><code>{row.family}</code></td>
              <td><span className={`rail rail-${row.rail}`}>{row.rail}</span></td>
              <td><span className={`mode ${row.zero_day ? "mode-zero-day" : "mode-in-sample"}`}>{row.zero_day ? "zero-day" : "in-sample"}</span></td>
              <td>{row.test_positive_count}</td>
              <td>{row.test_recall == null ? "—" : `${Math.round(row.test_recall * 100)}%`}</td>
              <td>{row.approve_miss_count}</td>
            </tr>
          ))}
          <tr className="efficacy-summary">
            <td colSpan={3}>In-sample aggregate</td>
            <td>{inSample.reduce((total, row) => total + row.test_positive_count, 0)}</td>
            <td>{recall(inSample) == null ? "—" : `${Math.round(recall(inSample) * 100)}%`}</td>
            <td>{inSample.reduce((total, row) => total + row.approve_miss_count, 0)}</td>
          </tr>
          <tr className="efficacy-summary">
            <td colSpan={3}>Zero-day aggregate</td>
            <td>{zeroDay.reduce((total, row) => total + row.test_positive_count, 0)}</td>
            <td>{recall(zeroDay) == null ? "—" : `${Math.round(recall(zeroDay) * 100)}%`}</td>
            <td>{zeroDay.reduce((total, row) => total + row.approve_miss_count, 0)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function EventEvidence({ evidence }) {
  return (
    <div className="event-evidence" aria-label="Concrete frozen-Test event samples">
      <div className="event-evidence-block">
        <p className="shap-label">Top DECLINE catches (highest score first)</p>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Entity token</th><th>Family</th><th>Rail</th><th>Amount</th><th>GenAI signal</th><th>Score</th><th>Decision</th></tr></thead>
            <tbody>
              {evidence.top_catches.map((event) => (
                <tr key={event.event_id}>
                  <td><code>{event.entity_token}</code></td>
                  <td>{event.family}</td>
                  <td><span className={`rail rail-${event.rail}`}>{event.rail}</span></td>
                  <td>${decimal(event.amount_usd, 2)}</td>
                  <td>{event.genai_signal ? <code>{event.genai_signal}</code> : "—"}</td>
                  <td>{decimal(event.score)}</td>
                  <td><span className={`decision-${event.decision.toLowerCase()}`}>{event.decision}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="event-evidence-block">
        <p className="shap-label">APPROVE misses (label = fraud, policy approved)</p>
        {evidence.approved_misses.length === 0
          ? <p className="stage-note">No APPROVE misses on frozen Test this run.</p>
          : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Entity token</th><th>Family</th><th>Rail</th><th>Amount</th><th>GenAI signal</th><th>Score</th><th>Decision</th></tr></thead>
                <tbody>
                  {evidence.approved_misses.map((event) => (
                    <tr key={event.event_id}>
                      <td><code>{event.entity_token}</code></td>
                      <td>{event.family}</td>
                      <td><span className={`rail rail-${event.rail}`}>{event.rail}</span></td>
                      <td>${decimal(event.amount_usd, 2)}</td>
                      <td>{event.genai_signal ? <code>{event.genai_signal}</code> : "—"}</td>
                      <td>{decimal(event.score)}</td>
                      <td><span className="decision-approve">{event.decision}</span></td>
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
