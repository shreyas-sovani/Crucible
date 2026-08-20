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
      { event_id: "e1", family: "first_party", vector_id: "Auto_Dispute_Farm", rail: "card", channel: "pos", timestamp: "2026-01-03T14:20:01+00:00", amount_usd: 45.82, entity_token: "tok_dispute_farm_1", genai_signal: null, score: 0.99, decision: "DECLINE" },
    ],
    approved_misses: [
      { event_id: "e2", family: "agentic_checkout", vector_id: "Agentic_Checkout", rail: "card", channel: "online", timestamp: "2026-01-03T15:00:00+00:00", amount_usd: 120.0, entity_token: "tok_agentic_checkout_2", genai_signal: "browser_dom_anomaly_score=0.95", score: 0.4, decision: "APPROVE" },
    ],
  },
};

describe("Crucible Lab", () => {
  let streamController;
  const encoder = new TextEncoder();

  beforeEach(() => {
    streamController = undefined;
    vi.stubGlobal("fetch", vi.fn((url) => {
      if (url === "/api/ontology") {
        return Promise.resolve({
          ok: true,
          json: async () => [{ id: "V-CIP_Mule", family: "deepfake_kyc", rail: "upi", status: "simulated" }],
        });
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
    expect(screen.getByText("Identify")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run full offline cycle" }));
    await waitFor(() => expect(streamController).toBeDefined());

    await emitStreamEvent("stage", { stage: "Identify", status: "Selected 8 simulated crews from Attack Ontology." });
    const simulatePacket = streamPacket("stage", { stage: "Simulate", status: "Generating Background traffic and simulated crew payment Events." });
    await emitStreamChunk(simulatePacket.slice(0, -2));
    expect(screen.queryByText("Simulate / Generating Background traffic and simulated crew payment Events.")).not.toBeInTheDocument();
    await emitStreamChunk(simulatePacket.slice(-2));

    expect(await screen.findByText("Simulate / Generating Background traffic and simulated crew payment Events.")).toBeInTheDocument();
    expect(screen.queryByText("Detection / frozen Test")).not.toBeInTheDocument();

    await emitStreamEvent("stage", { stage: "Detect", status: "Assembling causal features, training LightGBM, and scoring frozen Test." });
    await emitStreamEvent("stage", { stage: "Mutate", status: "Checking eligible in-sample APPROVE misses against frozen Test." });
    await emitStreamEvent("result", cycleArtifact);
    await act(async () => streamController.close());

    expect(await screen.findByText("Detection / frozen Test")).toBeInTheDocument();
    expect(screen.getByText("PR-AUC")).toBeInTheDocument();
    expect(screen.getByText("No in-sample APPROVE misses")).toBeInTheDocument();
    expect(screen.getByLabelText("Completed Cycle trace")).toBeInTheDocument();
    expect(screen.getByText("Cycle complete. 4 backend stages retained for review.")).toBeInTheDocument();
    expect(screen.getByText("Generating Background traffic and simulated crew payment Events.")).toBeInTheDocument();
    expect(screen.getByText("Fidelity PASS (2 gates)")).toBeInTheDocument();
    expect(screen.getByText("Dining KS n<50 skip")).toBeInTheDocument();
    expect(screen.getByText(/delayed card labels: 31/)).toBeInTheDocument();
    expect(screen.getAllByText("agentic_checkout").length).toBeGreaterThan(0);
    expect(screen.getByText("zero-day")).toBeInTheDocument();
    expect(screen.getByText("Zero-day aggregate")).toBeInTheDocument();
    expect(screen.getByLabelText("Per-family frozen-Test efficacy")).toBeInTheDocument();
    expect(screen.getByText("tok_dispute_farm_1")).toBeInTheDocument();
    expect(screen.getByText("tok_agentic_checkout_2")).toBeInTheDocument();
    expect(screen.getByText("browser_dom_anomaly_score=0.95")).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/cycle/stream", expect.objectContaining({ method: "POST", body: JSON.stringify({ seed: 1, n_days: 3, num_users: 80 }) }));
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
