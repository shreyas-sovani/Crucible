import numpy as np

from crucible.detector.model import Decision, fit, policy_from_scores, predict, select_operating_point


def test_lightgbm_scores_are_bounded_and_policy_uses_context_bands() -> None:
    X = np.array([[0.0], [0.1], [0.2], [0.8], [0.9], [1.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    model = fit(X, y, holdout_families=[])

    decisions = predict(model, X, operating_point=0.8)

    assert np.all((model.predict_scores(X) >= 0.0) & (model.predict_scores(X) <= 1.0))
    assert len(decisions) == len(X)
    assert policy_from_scores(np.array([0.69, 0.7, 0.9, 1.0]), operating_point=1.0) == [
        Decision.APPROVE,
        Decision.STEP_UP,
        Decision.HOLD,
        Decision.DECLINE,
    ]


def test_operating_point_reports_empirical_recall_and_fpr_at_one_percent_cap() -> None:
    labels = np.array([0, 0, 0, 1, 1])
    scores = np.array([0.10, 0.20, 0.30, 0.90, 0.95])

    metrics = select_operating_point(labels, scores, fpr_target=0.01)

    assert metrics.threshold == 0.9
    assert metrics.false_positive_rate == 0.0
    assert metrics.recall == 1.0
