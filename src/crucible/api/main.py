"""Offline-only HTTP surface for the Crucible Lab."""

from __future__ import annotations

import json
from pathlib import Path
from queue import Queue
from threading import Thread
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from crucible.models.config import CrewConfig
from crucible.ontology.schema import Vector, load_ontology
from crucible.loop.orchestrator import CycleRun, run_closed_loop


app = FastAPI(title="Crucible Lab", version="0.1.0")


class CycleRequest(BaseModel):
    """Offline world-generation request accepted by the Lab."""

    model_config = ConfigDict(extra="forbid")

    seed: int = 7
    n_days: int = Field(default=1, ge=1, le=90)
    num_users: int = Field(default=100, ge=1, le=10_000)
    crews: list[CrewConfig] | None = None


class FeatureAttribution(BaseModel):
    feature: str
    mean_abs_shap: float


class GenerationSummary(BaseModel):
    event_count: int
    fraud_event_count: int
    active_crew_count: int
    rail_counts: dict[str, int]
    topology: dict[str, dict[str, int]]
    grocery_ks_pvalue: float | None
    p2m_ks_pvalue: float | None
    dining_ks_pvalue: float | None
    p2p_ks_pvalue: float | None
    ist_business_hour_share: float
    ist_business_hours_pass: bool
    fidelity_gate_count: int
    fidelity_pass: bool | None


class FamilyEfficacySummary(BaseModel):
    family: str
    rail: str
    zero_day: bool
    test_positive_count: int
    test_caught_count: int
    test_recall: float | None
    approve_miss_count: int


class DetectionSummary(BaseModel):
    train_event_count: int
    validation_event_count: int
    test_event_count: int
    train_labeled_event_count: int
    validation_labeled_event_count: int
    operating_point: float
    validation_fpr_at_operating_point: float
    validation_recall_at_operating_point: float | None
    test_fpr_at_operating_point: float
    test_recall_at_operating_point: float | None
    pr_auc: float | None
    roc_auc: float | None
    recall_at_1pct_fpr: float | None
    expected_loss_usd: float
    decision_counts: dict[str, int]
    shap_top_features: list[FeatureAttribution]
    zero_day_train_positive_count: int
    zero_day_validation_positive_count: int
    delayed_card_fraud_count: int
    delayed_card_fraud_share: float
    family_efficacy: list[FamilyEfficacySummary]


class MutationSummary(BaseModel):
    status: str
    selected_family: str | None
    in_sample_approve_miss_count: int
    original_pr_auc: float | None
    mutated_pr_auc: float | None
    delta_pr_auc: float | None
    original_config: CrewConfig | None
    mutated_config: CrewConfig | None


class EvidenceEventSummary(BaseModel):
    event_id: str
    family: str
    vector_id: str
    rail: str
    channel: str
    timestamp: str
    amount_usd: float
    entity_token: str
    genai_signal: str | None
    score: float
    decision: str


class EvidenceSummary(BaseModel):
    top_catches: list[EvidenceEventSummary]
    approved_misses: list[EvidenceEventSummary]


class CycleSummary(BaseModel):
    generation: GenerationSummary
    detection: DetectionSummary
    mutation: MutationSummary
    evidence: EvidenceSummary


@app.get("/api/ontology", response_model=list[Vector])
def get_ontology() -> list[Vector]:
    """Return all validated attack vectors for Identify view."""

    return load_ontology()


@app.post("/api/cycle", response_model=CycleSummary)
def run_cycle(request: CycleRequest) -> CycleSummary:
    """Execute real seeded generation, detection, and mutation against frozen Test."""

    run = run_closed_loop(
        seed=request.seed,
        n_days=request.n_days,
        num_users=request.num_users,
        crews=request.crews,
    )
    return _cycle_summary(run)


@app.post("/api/cycle/stream")
def stream_cycle(request: CycleRequest) -> StreamingResponse:
    """Stream actual Cycle stage boundaries, then the unchanged final Cycle artifact."""

    return StreamingResponse(
        _cycle_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _cycle_summary(run: CycleRun) -> CycleSummary:
    """Serialize a completed CycleRun for both JSON and stream endpoints."""

    return CycleSummary(
        generation=GenerationSummary(**run.generation.__dict__),
        detection=DetectionSummary(
            **{
                **run.detection.__dict__,
                "shap_top_features": [
                    FeatureAttribution(feature=feature, mean_abs_shap=importance)
                    for feature, importance in run.detection.shap_top_features
                ],
                "family_efficacy": [FamilyEfficacySummary(**family.__dict__) for family in run.detection.family_efficacy],
            }
        ),
        mutation=MutationSummary(**run.mutation.__dict__),
        evidence=EvidenceSummary(
            top_catches=[EvidenceEventSummary(**event.__dict__) for event in run.evidence.top_catches],
            approved_misses=[EvidenceEventSummary(**event.__dict__) for event in run.evidence.approved_misses],
        ),
    )


def _cycle_stream(request: CycleRequest) -> Iterator[str]:
    messages: Queue[tuple[str, dict[str, object] | None]] = Queue()

    def execute_cycle() -> None:
        try:
            run = run_closed_loop(
                seed=request.seed,
                n_days=request.n_days,
                num_users=request.num_users,
                crews=request.crews,
                on_stage=lambda stage, status: messages.put(("stage", {"stage": stage, "status": status})),
            )
            messages.put(("result", _cycle_summary(run).model_dump(mode="json")))
        except Exception as error:  # pragma: no cover - browser-facing failure path
            messages.put(("error", {"detail": str(error)}))
        finally:
            messages.put(("end", None))

    Thread(target=execute_cycle, daemon=True).start()
    while True:
        event, data = messages.get()
        if event == "end":
            return
        yield _sse_packet(event, data or {})


def _sse_packet(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="lab-ui")
