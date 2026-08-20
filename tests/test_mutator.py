import numpy as np
import pandas as pd

from crucible.models.config import CrewConfig
from crucible.loop.mutator import mutate_config


class AmountSHAPModel:
    def shap_values(self, X: np.ndarray) -> np.ndarray:
        return np.full_like(X, 4.0, dtype=float)


class RowSelectiveSHAPModel:
    def shap_values(self, X: np.ndarray) -> np.ndarray:
        return X


def test_mutator_uses_only_in_sample_misses_and_caps_amount_bound() -> None:
    misses = pd.DataFrame(
        {
            "family": ["cnp_testing", "agentic_checkout"],
            "label": [1, 1],
            "decision": ["APPROVE", "APPROVE"],
            "amount_usd": [499.0, 499.0],
        }
    )
    config = CrewConfig(
        vector_id="LLM_Card_Testing",
        family="cnp_testing",
        rail="card",
        amount_bounds=(10.0, 500.0),
        velocity_per_hour=3,
        max_hop_count=2,
    )

    mutated = mutate_config(
        AmountSHAPModel(),
        misses,
        np.array([[1.0], [1.0]]),
        ("sum_amount_24h",),
        config,
    )

    assert mutated.amount_bounds == (10.0, 499.0)

    holdout_config = config.model_copy(update={"vector_id": "Agentic_Checkout", "family": "agentic_checkout"})
    assert mutate_config(AmountSHAPModel(), misses, np.array([[1.0], [1.0]]), ("sum_amount_24h",), holdout_config) == holdout_config


def test_mutator_uses_shap_of_eligible_missed_rows_not_entire_frozen_test() -> None:
    events = pd.DataFrame(
        {
            "family": ["cnp_testing", "cnp_testing", "agentic_checkout"],
            "label": [1, 1, 1],
            "decision": ["DECLINE", "APPROVE", "APPROVE"],
            "amount_usd": [10.0, 200.0, 500.0],
        }
    )
    config = CrewConfig(
        vector_id="LLM_Card_Testing",
        family="cnp_testing",
        rail="card",
        amount_bounds=(10.0, 500.0),
        velocity_per_hour=3,
        max_hop_count=2,
    )

    mutated = mutate_config(
        RowSelectiveSHAPModel(),
        events,
        np.array([[0.0, 100.0], [100.0, 0.0], [0.0, 100.0]]),
        ("sum_amount_24h", "count_tx_1h"),
        config,
    )

    assert mutated.amount_bounds == (10.0, 200.0)
    assert mutated.velocity_per_hour == 3
