import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const cycleArtifact = {
  generation: {
    event_count: 444, fraud_event_count: 204, active_crew_count: 8, rail_counts: { card: 200, upi: 244 },
    grocery_ks_pvalue: 0.62, p2m_ks_pvalue: 0.55, dining_ks_pvalue: null, p2p_ks_pvalue: null,
    ist_business_hour_share: 0.81, ist_business_hours_pass: true, fidelity_gate_count: 2, fidelity_pass: true,
  },
  detection: {
    train_event_count: 310, validation_event_count: 67, test_event_count: 67, operating_point: 0.8,
    pr_auc: 0.97, roc_auc: 0.95, recall_at_1pct_fpr: 0.8, expected_loss_usd: 644.29,
    test_fpr_at_operating_point: 0.008, validation_fpr_at_operating_point: 0.0,
    decision_counts: { HOLD: 40, APPROVE: 27 }, shap_top_features: [{ feature: "last_5_amounts", mean_abs_shap: 3.89 }],
    zero_day_train_positive_count: 0, zero_day_validation_positive_count: 0,
    delayed_card_fraud_count: 31, delayed_card_fraud_share: 0.3,
    family_efficacy: [
      { family: "agentic_checkout", rail: "card", zero_day: true, test_positive_count: 12, test_caught_count: 9, test_recall: 0.75, approve_miss_count: 3 },
      { family: "first_party", rail: "card", zero_day: false, test_positive_count: 30, test_caught_count: 30, test_recall: 1.0, approve_miss_count: 0 },
    ],
  },
  mutation: { status: "no_in_sample_approve_miss", selected_family: null, in_sample_approve_miss_count: 0, original_pr_auc: 0.97, mutated_pr_auc: 0.97, delta_pr_auc: 0 },
  evidence: {
    top_catches: [
      {
        event_id: "e1", family: "first_party", vector_id: "Auto_Dispute_Farm", rail: "card", channel: "pos",
        timestamp: "2026-01-03T14:20:01+00:00", amount_usd: 45.82, entity_token: "tok_dispute_farm_1",
        genai_signal: null, score: 0.99, decision: "DECLINE",
        top_shap: [{ feature: "prior_tx_count", contribution: 9.56 }, { feature: "sum_amount_24h", contribution: 0.8 }],
      },
    ],
    approved_misses: [
      {
        event_id: "e2", family: "agentic_checkout", vector_id: "Agentic_Checkout", rail: "card", channel: "online",
        timestamp: "2026-01-03T15:00:00+00:00", amount_usd: 120.0, entity_token: "tok_agentic_checkout_2",
        genai_signal: "browser_dom_anomaly_score=0.95", score: 0.4, decision: "APPROVE",
        top_shap: [{ feature: "prior_tx_count", contribution: -3.29 }],
      },
    ],
  },
};

const ontologyVectors = [
  { id: "V-CIP_Mule", family: "deepfake_kyc", rail: "upi", status: "simulated" },
  { id: "Agentic_Checkout", family: "agentic_checkout", rail: "card", status: "simulated" },
  { id: "llm-automated-phishing-for-otp", family: "phishing", rail: "upi", status: "playbook" },
];

function secondRunArtifact() {
  const artifact = JSON.parse(JSON.stringify(cycleArtifact));
  artifact.detection.pr_auc = 0.91;
  return artifact;
}

describe("Crucible Lab", () => {
  let streamController;
  const encoder = new TextEncoder();

  beforeEach(() => {
    streamController = undefined;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url === "/api/ontology") {
        return Promise.resolve({ ok: true, json: async () => ontologyVectors });
      }
      if (url === "/api/cycle/stream") {
        return Promise.resolve({
          ok: true,
          body: new ReadableStream({ start(controller) { streamController = controller; } }),
        });
      }
      throw new Error(`Unexpected Lab HTTP request: ${url}`);
    }));
  });

  afterEach(() => vi.unstubAllGlobals());

  it("renders streamed real Cycle stages before rendering final evidence", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("V-CIP_Mule")).toBeInTheDocument();
    expect(screen.getByText(/GETTING STARTED/)).toBeInTheDocument();
    expect(screen.getByText("Identify")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run assessment" }));
    await waitFor(() => expect(streamController).toBeDefined());
    expect(screen.queryByText(/GETTING STARTED/)).not.toBeInTheDocument();

    await emitStreamEvent("stage", { stage: "Identify", status: "Selected 8 simulated crews from Attack Ontology.", elapsed_ms: 12 });
    const simulatePacket = streamPacket("stage", { stage: "Simulate", status: "Generating Background traffic and simulated crew payment Events.", elapsed_ms: 340 });
    await emitStreamChunk(simulatePacket.slice(0, -2));
    expect(screen.queryByText("Simulate / Generating Background traffic and simulated crew payment Events.")).not.toBeInTheDocument();
    await emitStreamChunk(simulatePacket.slice(-2));

    expect(await screen.findByText("Simulate / Generating Background traffic and simulated crew payment Events.")).toBeInTheDocument();
    expect(screen.getByText("+0.3s server-side")).toBeInTheDocument();
    expect(screen.queryByText("Screening outcome")).not.toBeInTheDocument();

    await emitStreamEvent("stage", { stage: "Detect", status: "Assembling causal features, training LightGBM, and scoring frozen Test.", elapsed_ms: 900 });
    await emitStreamEvent("stage", { stage: "Mutate", status: "Checking eligible in-sample APPROVE misses against frozen Test.", elapsed_ms: 1500 });
    await emitStreamEvent("result", cycleArtifact);
    await act(async () => streamController.close());

    expect(await screen.findByText("Screening outcome")).toBeInTheDocument();
    expect(screen.getByText("Attacks caught")).toBeInTheDocument();
    expect(screen.getByText("Approved fraud")).toBeInTheDocument();
    expect(screen.getByText("No retraining triggered this run")).toBeInTheDocument();
    expect(screen.getByLabelText("Completed assessment trace")).toBeInTheDocument();
    expect(screen.getByText("Assessment complete. 4 process stages recorded.")).toBeInTheDocument();
    expect(screen.getByText("Generating Background traffic and simulated crew payment Events.")).toBeInTheDocument();
    expect(screen.getByText("Traffic realism checks")).toBeInTheDocument();
    expect(screen.getByText("Dining KS — sample too small")).toBeInTheDocument();
    expect(screen.getByText(/Distributions match yes/)).toBeInTheDocument();
    expect(screen.getAllByText("agentic_checkout").length).toBeGreaterThan(0);
    expect(screen.getByText("Never seen in training")).toBeInTheDocument();
    expect(screen.getByText("Never seen in training — combined")).toBeInTheDocument();
    expect(screen.getByText("Fraudulent payments approved — review these first")).toBeInTheDocument();
    expect(screen.getByText("tok_dispute_farm_1")).toBeInTheDocument();
    expect(screen.getByText("tok_agentic_checkout_2")).toBeInTheDocument();
    expect(screen.getAllByText("Why this decision").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Account history length").length).toBeGreaterThan(0);
    expect(screen.getByText("+9.56")).toBeInTheDocument();
    expect(screen.getByText("-3.29")).toBeInTheDocument();
    expect(screen.getByLabelText("Assessment history")).toBeInTheDocument();
    expect(screen.getByText(/1 assessment/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View run 1" })).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/cycle/stream", expect.objectContaining({ method: "POST", body: JSON.stringify({ seed: 1, n_days: 3, num_users: 80 }) }));
  });

  it("retains compared runs in the ledger and revisits a previous artifact", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    );

    await screen.findByText("V-CIP_Mule");
    fireEvent.click(screen.getByRole("button", { name: "Run assessment" }));
    await waitFor(() => expect(streamController).toBeDefined());
    await emitStreamEvent("stage", { stage: "Identify", status: "Selected 8 simulated crews from Attack Ontology.", elapsed_ms: 10 });
    await emitStreamEvent("result", cycleArtifact);
    await act(async () => streamController.close());
    expect(await screen.findByText(/1 assessment — click a row to reopen/)).toBeInTheDocument();

    streamController = undefined;
    fireEvent.click(screen.getByRole("button", { name: "Run assessment" }));
    await waitFor(() => expect(streamController).toBeDefined());
    await emitStreamEvent("stage", { stage: "Identify", status: "Selected 8 simulated crews from Attack Ontology.", elapsed_ms: 9 });
    await emitStreamEvent("result", secondRunArtifact());
    await act(async () => streamController.close());

    expect(await screen.findByText(/2 assessments — click a row to reopen/)).toBeInTheDocument();
    expect(screen.getByText("-0.060")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View run 2" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View run 1" }));
    expect(await screen.findByText("Screening outcome")).toBeInTheDocument();
    expect(document.querySelector(".run-viewed button")?.getAttribute("aria-label")).toBe("View run 1");
  });

  it("shows a friendly message when the server rejects a concurrent cycle", async () => {
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url === "/api/ontology") {
        return Promise.resolve({ ok: true, json: async () => ontologyVectors });
      }
      if (url === "/api/cycle/stream") {
        return Promise.resolve({
          ok: false,
          status: 409,
          json: async () => ({ detail: "A full offline Cycle is already running. Wait for it to finish." }),
        });
      }
      throw new Error(`Unexpected Lab HTTP request: ${url}`);
    }));

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    );

    await screen.findByText("V-CIP_Mule");
    fireEvent.click(screen.getByRole("button", { name: "Run assessment" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already running");
    expect(screen.getByRole("button", { name: "Run assessment" })).toBeEnabled();
  });

  it("filters the attack-vector ledger by rail and mode", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("V-CIP_Mule")).toBeInTheDocument();
    expect(screen.getByText("Agentic_Checkout")).toBeInTheDocument();
    expect(screen.getByText("3 shown")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "card" }));
    expect(screen.getByText("1 shown")).toBeInTheDocument();
    expect(screen.queryByText("V-CIP_Mule")).not.toBeInTheDocument();
    expect(screen.getByText("Agentic_Checkout")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "playbook" }));
    expect(screen.getByText("0 shown")).toBeInTheDocument();
    expect(screen.queryByText("Agentic_Checkout")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "All rails" }));
    fireEvent.click(screen.getByRole("button", { name: "All modes" }));
    expect(screen.getByText("3 shown")).toBeInTheDocument();
  });

  async function emitStreamEvent(event, data) {
    await emitStreamChunk(streamPacket(event, data));
  }

  async function emitStreamChunk(chunk) {
    await act(async () => {
      streamController.enqueue(encoder.encode(chunk));
    });
  }

  function streamPacket(event, data) {
    return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  }
});
