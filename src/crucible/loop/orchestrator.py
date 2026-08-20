"""Executable Identify → Simulate → Detect → Mutate cycle for Crucible Lab."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import kstest, norm
from sklearn.metrics import average_precision_score, roc_auc_score

from crucible.detector.model import Decision, LightGBMModel, OperatingPointMetrics, fit, predict, select_operating_point, threshold_metrics
from crucible.evaluation.harness import ZERO_DAY_HOLDOUTS, DatasetSplits, expected_loss, observed_supervision, split_chronologically
from crucible.features.assembler import FeatureSet, assemble_features
from crucible.models.config import CrewConfig
from crucible.simulator.crews import default_crew_configs
from crucible.simulator.topology import degree_histogram
from crucible.simulator.world import resimulate_train_window, simulate
from crucible.loop.mutator import mutate_config


@dataclass(frozen=True)
class GenerationReport:
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


@dataclass(frozen=True)
class FamilyEfficacy:
    """Frozen-Test detection outcome for one attack family."""

    family: str
    rail: str
    zero_day: bool
    test_positive_count: int
    test_caught_count: int
    test_recall: float | None
    approve_miss_count: int


@dataclass(frozen=True)
class DetectionReport:
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
    shap_top_features: list[tuple[str, float]]
    zero_day_train_positive_count: int
    zero_day_validation_positive_count: int
    delayed_card_fraud_count: int
    delayed_card_fraud_share: float
    family_efficacy: list[FamilyEfficacy]


@dataclass(frozen=True)
class MutationReport:
    status: str
    selected_family: str | None
    in_sample_approve_miss_count: int
    original_pr_auc: float | None
    mutated_pr_auc: float | None
    delta_pr_auc: float | None
    original_config: CrewConfig | None
    mutated_config: CrewConfig | None


@dataclass(frozen=True)
class EvidenceEvent:
    """One concrete frozen-Test fraud Event with its detector outcome."""

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


@dataclass(frozen=True)
class EvidenceReport:
    top_catches: list[EvidenceEvent]
    approved_misses: list[EvidenceEvent]


@dataclass(frozen=True)
class CycleRun:
    generation: GenerationReport
    detection: DetectionReport
    mutation: MutationReport
    evidence: EvidenceReport


def run_closed_loop(
    *,
    seed: int,
    n_days: int,
    num_users: int,
    crews: list[CrewConfig] | None = None,
    on_stage: Callable[[str, str], None] | None = None,
) -> CycleRun:
    """Execute a seeded, offline cycle and return inspectable real artifacts."""

    active_crews = crews or default_crew_configs()
    _report_stage(on_stage, "Identify", f"Selected {len(active_crews)} simulated crews from Attack Ontology.")
    _report_stage(on_stage, "Simulate", "Generating Background traffic and simulated crew payment Events.")
    events = simulate(seed, n_days, active_crews, num_users=num_users, schedule_crews=True)
    generation = _generation_report(events, len(active_crews))
    _report_stage(on_stage, "Detect", "Assembling causal features, training LightGBM, and scoring frozen Test.")
    features, splits = _feature_splits(events)
    model, operating_point, train_labeled_count, validation_labeled_count = _fit_initial_model(splits, features.names)
    detection, scored_test, test_matrix = _detect(
        model,
        operating_point,
        splits,
        features.names,
        train_labeled_count=train_labeled_count,
        validation_labeled_count=validation_labeled_count,
        events=events,
    )
    _report_stage(on_stage, "Mutate", "Checking eligible in-sample APPROVE misses against frozen Test.")
    mutation = _mutate_and_retrain(
        seed=seed,
        active_crews=active_crews,
        model=model,
        scored_test=scored_test,
        test_matrix=test_matrix,
        feature_names=features.names,
        original_pr_auc=detection.pr_auc,
        train_events=splits.train,
    )
    return CycleRun(
        generation=generation,
        detection=detection,
        mutation=mutation,
        evidence=_evidence_report(scored_test),
    )


def _report_stage(reporter: Callable[[str, str], None] | None, stage: str, status: str) -> None:
    if reporter is not None:
        reporter(stage, status)


def _feature_splits(events: pd.DataFrame) -> tuple[FeatureSet, DatasetSplits]:
    ordered = events.sort_values("timestamp", kind="stable").reset_index(drop=True)
    features = assemble_features(ordered)
    source_columns_replaced_by_features = [name for name in features.names if name in ordered.columns]
    enriched = pd.concat([ordered.drop(columns=source_columns_replaced_by_features), features.frame], axis=1)
    return features, split_chronologically(enriched)


def _fit_initial_model(
    splits: DatasetSplits, feature_names: tuple[str, ...]
) -> tuple[LightGBMModel, OperatingPointMetrics, int, int]:
    train = observed_supervision(splits.train)
    validation = observed_supervision(splits.validation)
    train_X = _feature_matrix(train, feature_names)
    train_y = _labels(train)
    validation_X = _feature_matrix(validation, feature_names)
    validation_y = _labels(validation)
    model = fit(train_X, train_y, holdout_families=list(ZERO_DAY_HOLDOUTS))
    return model, select_operating_point(validation_y, model.predict_scores(validation_X)), len(train), len(validation)


def _detect(
    model: LightGBMModel,
    operating_point: OperatingPointMetrics,
    splits: DatasetSplits,
    feature_names: tuple[str, ...],
    *,
    train_labeled_count: int,
    validation_labeled_count: int,
    events: pd.DataFrame,
) -> tuple[DetectionReport, pd.DataFrame, np.ndarray]:
    test_matrix = _feature_matrix(splits.test, feature_names)
    test_y = _labels(splits.test)
    scores = model.predict_scores(test_matrix)
    decisions = predict(model, test_matrix, operating_point.threshold)
    scored_test = splits.test.copy()
    scored_test["score"] = scores
    scored_test["decision"] = [decision.value for decision in decisions]
    shap = model.shap_values(test_matrix)
    delayed_count, delayed_share = _delayed_card_fraud(events)
    test_operating_metrics = threshold_metrics(test_y, scores, threshold=operating_point.threshold)
    test_one_percent_metrics = select_operating_point(test_y, scores)
    report = DetectionReport(
        train_event_count=len(splits.train),
        validation_event_count=len(splits.validation),
        test_event_count=len(splits.test),
        train_labeled_event_count=train_labeled_count,
        validation_labeled_event_count=validation_labeled_count,
        operating_point=operating_point.threshold,
        validation_fpr_at_operating_point=operating_point.false_positive_rate,
        validation_recall_at_operating_point=operating_point.recall,
        test_fpr_at_operating_point=test_operating_metrics.false_positive_rate,
        test_recall_at_operating_point=test_operating_metrics.recall,
        pr_auc=_safe_pr_auc(test_y, scores),
        roc_auc=_safe_roc_auc(test_y, scores),
        recall_at_1pct_fpr=test_one_percent_metrics.recall,
        expected_loss_usd=expected_loss(scored_test, decisions),
        decision_counts=dict(Counter(decision.value for decision in decisions)),
        shap_top_features=_top_features(shap, feature_names),
        zero_day_train_positive_count=_zero_day_positive_count(splits.train),
        zero_day_validation_positive_count=_zero_day_positive_count(splits.validation),
        delayed_card_fraud_count=delayed_count,
        delayed_card_fraud_share=delayed_share,
        family_efficacy=_family_efficacy(scored_test, operating_point.threshold),
    )
    return report, scored_test, test_matrix


def _mutate_and_retrain(
    *,
    seed: int,
    active_crews: list[CrewConfig],
    model: LightGBMModel,
    scored_test: pd.DataFrame,
    test_matrix: np.ndarray,
    feature_names: tuple[str, ...],
    original_pr_auc: float | None,
    train_events: pd.DataFrame,
) -> MutationReport:
    in_sample_misses = scored_test.loc[
        scored_test["family"].isin({config.family for config in active_crews if config.family not in ZERO_DAY_HOLDOUTS})
        & scored_test["label"].eq(1)
        & scored_test["decision"].eq(Decision.APPROVE.value)
    ]
    for index, config in enumerate(active_crews):
        mutated = mutate_config(model, scored_test, test_matrix, feature_names, config)
        if mutated == config:
            continue
        updated_crews = [mutated if position == index else crew for position, crew in enumerate(active_crews)]
        retrained_model = _retrain_on_resimulated_train(train_events, seed=seed, crews=updated_crews, feature_names=feature_names)
        frozen_scores = retrained_model.predict_scores(test_matrix)
        mutated_pr_auc = _safe_pr_auc(_labels(scored_test), frozen_scores)
        return MutationReport(
            status="mutated_and_retrained",
            selected_family=config.family,
            in_sample_approve_miss_count=len(in_sample_misses),
            original_pr_auc=original_pr_auc,
            mutated_pr_auc=mutated_pr_auc,
            delta_pr_auc=_delta(mutated_pr_auc, original_pr_auc),
            original_config=config,
            mutated_config=mutated,
        )
    return MutationReport(
        status="no_in_sample_approve_miss",
        selected_family=None,
        in_sample_approve_miss_count=len(in_sample_misses),
        original_pr_auc=original_pr_auc,
        mutated_pr_auc=original_pr_auc,
        delta_pr_auc=0.0 if original_pr_auc is not None else None,
        original_config=None,
        mutated_config=None,
    )


def _retrain_on_resimulated_train(
    train_events: pd.DataFrame,
    *,
    seed: int,
    crews: list[CrewConfig],
    feature_names: tuple[str, ...],
) -> LightGBMModel:
    """Resimulate original Train window only; frozen Test is never regenerated."""

    resimulated_train = resimulate_train_window(train_events, crews=crews, seed=seed)
    features = assemble_features(resimulated_train)
    replaced_columns = [name for name in features.names if name in resimulated_train.columns]
    training = pd.concat([resimulated_train.reset_index(drop=True).drop(columns=replaced_columns), features.frame], axis=1)
    training = observed_supervision(training)
    return fit(_feature_matrix(training, feature_names), _labels(training), holdout_families=list(ZERO_DAY_HOLDOUTS))


FIDELITY_MIN_SAMPLES = 50
IST_BUSINESS_HOURS = (0.70, 0.90)


def _generation_report(events: pd.DataFrame, crew_count: int) -> GenerationReport:
    legitimate = events.loc[events["label"].eq(0)]
    grocery = pd.to_numeric(legitimate.loc[legitimate["mcc"].eq(5411), "amount_usd"], errors="coerce").dropna()
    dining = pd.to_numeric(legitimate.loc[legitimate["mcc"].eq(5812), "amount_usd"], errors="coerce").dropna()
    p2m = pd.to_numeric(legitimate.loc[legitimate["tx_note"].eq("p2m"), "amount_inr"], errors="coerce").dropna()
    p2p = pd.to_numeric(legitimate.loc[legitimate["tx_note"].eq("p2p"), "amount_inr"], errors="coerce").dropna()
    gates = [
        _normal_ks_pvalue(grocery, mean=45.0, stddev=15.0),
        _normal_ks_pvalue(dining, mean=30.0, stddev=10.0),
        _normal_ks_pvalue(p2m, mean=500.0, stddev=200.0),
        _normal_ks_pvalue(p2p, mean=2000.0, stddev=1000.0),
    ]
    active_gates = [pvalue for pvalue in gates if pvalue is not None]
    ist_share = _ist_business_hour_share(legitimate)
    ist_pass = IST_BUSINESS_HOURS[0] <= ist_share <= IST_BUSINESS_HOURS[1]
    return GenerationReport(
        event_count=len(events),
        fraud_event_count=int(events["label"].eq(1).sum()),
        active_crew_count=crew_count,
        rail_counts={str(key): int(value) for key, value in events["rail"].value_counts().items()},
        topology=degree_histogram(events),
        grocery_ks_pvalue=gates[0],
        dining_ks_pvalue=gates[1],
        p2m_ks_pvalue=gates[2],
        p2p_ks_pvalue=gates[3],
        ist_business_hour_share=ist_share,
        ist_business_hours_pass=ist_pass,
        fidelity_gate_count=len(active_gates),
        fidelity_pass=all(pvalue > 0.05 for pvalue in active_gates) if active_gates else None,
    )


def _normal_ks_pvalue(values: pd.Series, *, mean: float, stddev: float) -> float | None:
    """KS p-value against the declared zero-truncated normal generating CDF."""

    if len(values) < FIDELITY_MIN_SAMPLES:
        return None
    lower_cdf = float(norm.cdf((0.0 - mean) / stddev))

    def cdf(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        return np.where(x <= 0, 0.0, (norm.cdf((x - mean) / stddev) - lower_cdf) / (1.0 - lower_cdf))

    return float(kstest(values.to_numpy(dtype=float), cdf).pvalue)


def _ist_business_hour_share(legitimate: pd.DataFrame) -> float:
    upi = legitimate.loc[legitimate["rail"].eq("upi")]
    if upi.empty:
        return 0.0
    timestamps = pd.to_datetime(upi["timestamp"], utc=True)
    ist_hour = (timestamps + pd.Timedelta(hours=5, minutes=30)).dt.hour
    return float(ist_hour.between(9, 20).mean())


def _delayed_card_fraud(events: pd.DataFrame) -> tuple[int, float]:
    card_fraud = events["rail"].eq("card") & events["label"].eq(1)
    total = int(card_fraud.sum())
    if not total or "label_available_at" not in events:
        return 0, 0.0
    available = pd.to_datetime(events.loc[card_fraud, "label_available_at"], utc=True)
    occurred = pd.to_datetime(events.loc[card_fraud, "timestamp"], utc=True)
    delayed = int((available - occurred > pd.Timedelta(days=0)).sum())
    return delayed, delayed / total


def _family_efficacy(scored_test: pd.DataFrame, operating_point: float) -> list[FamilyEfficacy]:
    fraud = scored_test.loc[scored_test["label"].eq(1)]
    efficacy: list[FamilyEfficacy] = []
    for family, group in fraud.groupby("family", sort=True):
        caught = int(group["score"].ge(operating_point).sum())
        approved = int(group["decision"].eq(Decision.APPROVE.value).sum())
        efficacy.append(
            FamilyEfficacy(
                family=str(family),
                rail=str(group["rail"].iloc[0]),
                zero_day=family in ZERO_DAY_HOLDOUTS,
                test_positive_count=len(group),
                test_caught_count=caught,
                test_recall=caught / len(group),
                approve_miss_count=approved,
            )
        )
    return efficacy


def _evidence_report(scored_test: pd.DataFrame, *, limit: int = 5) -> EvidenceReport:
    """Concrete token-only fraud samples judges can inspect per run."""

    fraud = scored_test.loc[scored_test["label"].eq(1)].copy()
    if fraud.empty:
        return EvidenceReport(top_catches=[], approved_misses=[])
    catches = fraud.sort_values("score", ascending=False).head(limit)
    misses = fraud.loc[fraud["decision"].eq(Decision.APPROVE.value)]
    misses = misses.sort_values(["score", "amount_usd", "amount_inr"], ascending=False).head(limit)
    return EvidenceReport(
        top_catches=[_evidence_event(row) for _, row in catches.iterrows()],
        approved_misses=[_evidence_event(row) for _, row in misses.iterrows()],
    )


def _evidence_event(row: pd.Series) -> EvidenceEvent:
    usd = pd.to_numeric(pd.Series([row.get("amount_usd")]), errors="coerce").iloc[0]
    inr = pd.to_numeric(pd.Series([row.get("amount_inr")]), errors="coerce").iloc[0]
    amount = float(usd) if pd.notna(usd) else float(inr) / 84.0 if pd.notna(inr) else 0.0
    token = row.get("pan_token") if row.get("pan_token") else row.get("payer_vpa")
    return EvidenceEvent(
        event_id=str(row.get("event_id")),
        family=str(row.get("family")),
        vector_id=str(row.get("vector_id")),
        rail=str(row.get("rail")),
        channel=str(row.get("channel")),
        timestamp=pd.Timestamp(row.get("timestamp")).isoformat(),
        amount_usd=round(amount, 2),
        entity_token=str(token or "masked"),
        genai_signal=_genai_signal(row),
        score=float(row.get("score") or 0.0),
        decision=str(row.get("decision")),
    )


def _genai_signal(row: pd.Series) -> str | None:
    if bool(row.get("v_cip_injection_flag") or False):
        return "v_cip_injection_flag"
    dom = pd.to_numeric(pd.Series([row.get("browser_dom_anomaly_score")]), errors="coerce").iloc[0]
    if pd.notna(dom) and float(dom) >= 0.5:
        return f"browser_dom_anomaly_score={float(dom):.2f}"
    prompt = pd.to_numeric(pd.Series([row.get("remittance_prompt_score")]), errors="coerce").iloc[0]
    if pd.notna(prompt) and float(prompt) >= 0.5:
        return f"remittance_prompt_score={float(prompt):.2f}"
    return None


def _feature_matrix(frame: pd.DataFrame, feature_names: tuple[str, ...]) -> np.ndarray:
    return frame.loc[:, list(feature_names)].to_numpy(dtype=float)


def _labels(frame: pd.DataFrame) -> np.ndarray:
    return pd.to_numeric(frame["label"], errors="coerce").fillna(0).to_numpy(dtype=int)


def _safe_pr_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(labels)) < 2:
        return None
    return float(average_precision_score(labels, scores))


def _safe_roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(labels)) < 2:
        return None
    return float(roc_auc_score(labels, scores))


def _top_features(shap_values: np.ndarray, feature_names: tuple[str, ...], count: int = 10) -> list[tuple[str, float]]:
    importance = np.abs(shap_values).mean(axis=0)
    order = np.argsort(importance)[::-1][:count]
    return [(feature_names[index], float(importance[index])) for index in order]


def _zero_day_positive_count(frame: pd.DataFrame) -> int:
    return int(frame.loc[frame["family"].isin(ZERO_DAY_HOLDOUTS), "label"].eq(1).sum())


def _delta(after: float | None, before: float | None) -> float | None:
    if after is None or before is None:
        return None
    return after - before
