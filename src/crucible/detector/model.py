"""LightGBM detector and policy mapping defined by CONTEXT.md."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from lightgbm import LGBMClassifier


class Decision(StrEnum):
    DECLINE = "DECLINE"
    HOLD = "HOLD"
    STEP_UP = "STEP_UP"
    APPROVE = "APPROVE"


@dataclass(frozen=True)
class OperatingPointMetrics:
    """One threshold's empirical validation or frozen-Test operating characteristics."""

    threshold: float
    false_positive_rate: float
    recall: float | None


@dataclass
class LightGBMModel:
    """Trained LightGBM classifier with native contribution access."""

    estimator: LGBMClassifier
    holdout_families: tuple[str, ...]

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        return np.clip(self.estimator.predict_proba(X)[:, 1], 0.0, 1.0)

    def shap_values(self, X: np.ndarray) -> np.ndarray:
        """Return native TreeSHAP feature contributions excluding expected value."""

        contributions = np.asarray(self.estimator.predict(X, pred_contrib=True))
        return contributions[:, :-1]


def fit(X_train: np.ndarray, y_train: np.ndarray, holdout_families: list[str]) -> LightGBMModel:
    """Fit a deterministic imbalance-aware LightGBM binary classifier on already-safe features."""

    labels = np.asarray(y_train, dtype=int)
    if set(np.unique(labels)).difference({0, 1}) or len(np.unique(labels)) < 2:
        msg = "y_train must contain both binary classes."
        raise ValueError(msg)
    positives = int((labels == 1).sum())
    negatives = int((labels == 0).sum())
    estimator = LGBMClassifier(
        objective="binary",
        n_estimators=128,
        learning_rate=0.08,
        num_leaves=15,
        min_child_samples=1,
        scale_pos_weight=(negatives / positives) if positives else 1.0,
        random_state=0,
        verbosity=-1,
    )
    estimator.fit(np.asarray(X_train, dtype=float), labels)
    return LightGBMModel(estimator=estimator, holdout_families=tuple(holdout_families))


def predict(model: LightGBMModel, X: np.ndarray, operating_point: float) -> list[Decision]:
    """Score rows and map them through the Context policy bands."""

    return policy_from_scores(model.predict_scores(X), operating_point)


def policy_from_scores(scores: np.ndarray, operating_point: float) -> list[Decision]:
    """Map scores to DECLINE, HOLD, STEP_UP, or APPROVE using exact thresholds."""

    if not 0 < operating_point <= 1:
        msg = "operating_point must be in (0, 1]."
        raise ValueError(msg)
    decisions: list[Decision] = []
    for score in np.asarray(scores, dtype=float):
        if score >= operating_point:
            decisions.append(Decision.DECLINE)
        elif score >= 0.9 * operating_point:
            decisions.append(Decision.HOLD)
        elif score >= 0.7 * operating_point:
            decisions.append(Decision.STEP_UP)
        else:
            decisions.append(Decision.APPROVE)
    return decisions


def get_operating_point(model: LightGBMModel, X_val: np.ndarray, y_val: np.ndarray, *, fpr_target: float = 0.01) -> float:
    """Choose highest-recall score threshold satisfying target false-positive rate."""

    scores = model.predict_scores(X_val)
    return select_operating_point(y_val, scores, fpr_target=fpr_target).threshold


def select_operating_point(labels: np.ndarray, scores: np.ndarray, *, fpr_target: float = 0.01) -> OperatingPointMetrics:
    """Select and report max-recall threshold under an empirical FPR cap."""

    if not 0 < fpr_target < 1:
        msg = "fpr_target must be in (0, 1)."
        raise ValueError(msg)
    labels_array = np.asarray(labels, dtype=int)
    scores_array = np.asarray(scores, dtype=float)
    if labels_array.shape != scores_array.shape:
        msg = "labels and scores must have matching shapes."
        raise ValueError(msg)
    best = threshold_metrics(labels_array, scores_array, threshold=1.0)
    best_recall = best.recall if best.recall is not None else -1.0
    for threshold in np.unique(np.r_[scores_array, 1.0]):
        candidate = threshold_metrics(labels_array, scores_array, threshold=float(threshold))
        candidate_recall = candidate.recall if candidate.recall is not None else -1.0
        if candidate.false_positive_rate > fpr_target:
            continue
        if candidate_recall > best_recall or (
            candidate_recall == best_recall and candidate.false_positive_rate < best.false_positive_rate
        ):
            best, best_recall = candidate, candidate_recall
    return best


def threshold_metrics(labels: np.ndarray, scores: np.ndarray, *, threshold: float) -> OperatingPointMetrics:
    """Measure one fixed threshold without reselecting it on this dataset."""

    labels_array = np.asarray(labels, dtype=int)
    scores_array = np.asarray(scores, dtype=float)
    predicted = scores_array >= threshold
    negatives = int((labels_array == 0).sum())
    positives = int((labels_array == 1).sum())
    fpr = float((predicted & (labels_array == 0)).sum() / negatives) if negatives else 0.0
    recall = float((predicted & (labels_array == 1)).sum() / positives) if positives else None
    return OperatingPointMetrics(threshold=float(threshold), false_positive_rate=fpr, recall=recall)
