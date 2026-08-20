from crucible.simulator.background import generate_background
from crucible.simulator.topology import apply_power_law_topology


def test_topology_assigns_pareto_weighted_card_merchants_and_upi_payees() -> None:
    frame = apply_power_law_topology(generate_background(seed=3, n_days=2, num_users=100), seed=8)

    card_merchants = frame.loc[frame["rail"] == "card", "merchant_id"]
    upi_payees = frame.loc[frame["rail"] == "upi", "payee_vpa"]
    degrees = card_merchants.value_counts()

    assert card_merchants.notna().all()
    assert upi_payees.str.startswith("payee_").all()
    assert degrees.max() > degrees.median()
