import pandas as pd

from crucible.detector.model import Decision
from crucible.evaluation.harness import expected_loss, split_chronologically


def test_chronological_split_masks_zero_day_families_before_test() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC"),
            "family": ["agentic_checkout"] * 6 + ["legitimate"] * 8 + ["remittance_injection"] * 3 + ["agentic_checkout"] * 3,
            "label": [1] * 20,
        }
    )

    splits = split_chronologically(frame)

    assert len(splits.train) == 14
    assert len(splits.validation) == 3
    assert len(splits.test) == 3
    assert splits.train.loc[splits.train["family"].eq("agentic_checkout"), "label"].eq(0).all()
    assert splits.validation.loc[splits.validation["family"].eq("remittance_injection"), "label"].eq(0).all()
    assert splits.test.loc[splits.test["family"].eq("agentic_checkout"), "label"].eq(1).all()


def test_expected_loss_uses_fixed_upi_conversion_and_only_approved_fraud() -> None:
    events = pd.DataFrame(
        {
            "rail": ["card", "upi", "card"],
            "label": [1, 1, 0],
            "amount_usd": [100.0, None, 20.0],
            "amount_inr": [None, 8400.0, None],
        }
    )

    loss = expected_loss(events, [Decision.APPROVE, Decision.APPROVE, Decision.APPROVE])

    assert loss == 200.0


def test_split_marks_delayed_fraud_labels_unavailable_for_train_but_keeps_upi_immediate() -> None:
    timestamps = pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "family": ["cnp_testing", "deepfake_kyc"] + ["legitimate"] * 18,
            "rail": ["card", "upi"] + ["card"] * 18,
            "label": [1, 1] + [0] * 18,
            "label_available_at": [timestamps[0] + pd.Timedelta(days=45), timestamps[1]] + list(timestamps[2:]),
        }
    )

    splits = split_chronologically(frame)

    assert splits.train.loc[splits.train["rail"].eq("card") & splits.train["label"].eq(1), "label_observed"].eq(False).all()
    assert splits.train.loc[splits.train["rail"].eq("upi") & splits.train["label"].eq(1), "label_observed"].eq(True).all()
