import json

from fastapi.testclient import TestClient

from crucible.api.main import app


def test_lab_http_surface_exposes_ontology_and_real_closed_cycle() -> None:
    client = TestClient(app)

    ontology = client.get("/api/ontology")
    cycle = client.post("/api/cycle", json={"seed": 1, "n_days": 3, "num_users": 80})
    lab = client.get("/")

    assert ontology.status_code == 200
    assert len(ontology.json()) == 30
    assert cycle.status_code == 200
    assert cycle.json()["generation"]["fraud_event_count"] > 0
    assert cycle.json()["generation"]["active_crew_count"] == 8
    assert cycle.json()["generation"]["grocery_ks_pvalue"] > 0.05
    assert cycle.json()["generation"]["p2m_ks_pvalue"] > 0.05
    assert cycle.json()["generation"]["fidelity_pass"] is True
    assert cycle.json()["generation"]["fidelity_gate_count"] >= 2
    assert cycle.json()["generation"]["ist_business_hours_pass"] is True
    assert 0.70 <= cycle.json()["generation"]["ist_business_hour_share"] <= 0.90
    detection = cycle.json()["detection"]
    assert 0.25 <= detection["delayed_card_fraud_share"] <= 0.35
    assert detection["delayed_card_fraud_count"] > 0
    efficacy = detection["family_efficacy"]
    assert efficacy
    families = {row["family"] for row in efficacy}
    assert "agentic_checkout" in families
    agentic = next(row for row in efficacy if row["family"] == "agentic_checkout")
    assert agentic["zero_day"] is True
    assert agentic["test_positive_count"] > 0
    in_sample = [row for row in efficacy if not row["zero_day"]]
    assert in_sample
    assert all(row["test_recall"] is not None for row in efficacy)
    assert cycle.json()["detection"]["train_event_count"] > 0
    assert cycle.json()["detection"]["test_event_count"] > 0
    assert cycle.json()["detection"]["train_labeled_event_count"] < cycle.json()["detection"]["train_event_count"]
    assert cycle.json()["detection"]["validation_fpr_at_operating_point"] <= 0.01
    assert cycle.json()["detection"]["recall_at_1pct_fpr"] is not None
    assert cycle.json()["detection"]["decision_counts"]
    assert cycle.json()["detection"]["shap_top_features"]
    assert cycle.json()["mutation"]["status"] in {"mutated_and_retrained", "no_in_sample_approve_miss"}
    assert cycle.json()["mutation"]["delta_pr_auc"] is not None
    evidence = cycle.json()["evidence"]
    assert evidence["top_catches"]
    catch = evidence["top_catches"][0]
    assert catch["decision"] == "DECLINE"
    assert catch["score"] >= detection["operating_point"]
    assert catch["family"] != "legitimate"
    assert catch["entity_token"]
    for miss in evidence["approved_misses"]:
        assert miss["decision"] == "APPROVE"
        assert miss["amount_usd"] >= 0
    assert lab.status_code == 200
    assert "Crucible Lab" in lab.text


def test_lab_http_surface_streams_real_cycle_stages_before_final_artifact() -> None:
    client = TestClient(app)

    with client.stream("POST", "/api/cycle/stream", json={"seed": 1, "n_days": 3, "num_users": 80}) as response:
        payload = "".join(response.iter_text())

    events = _sse_events(payload)
    stage_events = [data for event, data in events if event == "stage"]
    result = next(data for event, data in events if event == "result")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [event["stage"] for event in stage_events] == ["Identify", "Simulate", "Detect", "Mutate"]
    assert all(event["status"] for event in stage_events)
    assert result["generation"]["active_crew_count"] == 8
    assert result["detection"]["test_event_count"] > 0


def _sse_events(payload: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for packet in payload.strip().split("\n\n"):
        lines = packet.splitlines()
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events
