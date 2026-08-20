import pandas as pd
import pytest

from crucible.simulator.background import generate_background


def test_background_is_deterministic_and_matches_grocery_distribution() -> None:
    first = generate_background(seed=17, n_days=4, num_users=250)
    second = generate_background(seed=17, n_days=4, num_users=250)

    pd.testing.assert_frame_equal(first, second)
    grocery = first.loc[first["mcc"] == 5411, "amount_usd"]

    assert set(first["rail"]) == {"card", "upi"}
    assert abs(grocery.mean() - 45.0) <= 5.0


def test_background_reuses_stable_per_user_card_and_upi_entities() -> None:
    frame = generate_background(seed=23, n_days=10, num_users=50)

    card = frame.loc[frame["rail"].eq("card")]
    upi = frame.loc[frame["rail"].eq("upi")]

    assert card["pan_token"].nunique() <= 50
    assert upi["payer_vpa"].nunique() <= 50
    repeated_cards = card["pan_token"].value_counts()
    assert repeated_cards.gt(1).any()
    per_user_window = card.sort_values("timestamp").groupby("pan_token")["amount_usd"]
    assert per_user_window.count().gt(1).any()


def test_upi_business_hour_volume_matches_context_eighty_percent() -> None:
    frame = generate_background(seed=31, n_days=10, num_users=400)

    upi = frame.loc[frame["rail"].eq("upi")]
    timestamps = pd.to_datetime(upi["timestamp"], utc=True)
    ist_hour = (timestamps + pd.Timedelta(hours=5, minutes=30)).dt.hour

    assert ist_hour.between(9, 20).mean() == pytest.approx(0.80, abs=0.05)
