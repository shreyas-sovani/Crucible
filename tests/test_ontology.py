from crucible.ontology.schema import Vector, load_ontology


def test_load_ontology_returns_refreshed_complete_catalog() -> None:
    vectors = load_ontology()

    assert len(vectors) == 30
    assert sum(vector.status == "simulated" for vector in vectors) == 8
    assert all(isinstance(vector, Vector) for vector in vectors)
    assert all(vector.genai_telemetry_requirements for vector in vectors)
    assert {(vector.id, vector.family, vector.rail) for vector in vectors if vector.status == "simulated"} == {
        ("V-CIP_Mule", "deepfake_kyc", "upi"),
        ("Agentic_Checkout", "agentic_checkout", "card"),
        ("Prompt_Inject_Copilot", "remittance_injection", "upi"),
        ("Synthetic_Triangulation", "synthetic_merchant", "card"),
        ("Scaled_Investment_APP", "app_scam", "upi"),
        ("LLM_Card_Testing", "cnp_testing", "card"),
        ("Auto_Dispute_Farm", "first_party", "card"),
        ("Voice_Clone_Exec", "bec", "upi"),
    }
    assert {vector.family for vector in vectors if vector.status == "playbook"} <= {
        "phishing",
        "synthetic_id",
        "adversarial_ml",
        "refund_abuse",
    }
