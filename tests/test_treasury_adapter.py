"""Contracts for the Treasury yield adapter: cleaning, validation, features."""

import numpy as np
import pandas as pd
import pytest

from dsm_project.config import load_config
from dsm_project.data import load_project_dataset
from dsm_project.data.treasury import (
    FORWARD_HORIZON,
    TRADING_DAYS,
    YIELD_COLUMNS,
    add_features,
    clean_yields,
    validate_yields,
)


def make_yields(n_days: int = 150) -> pd.DataFrame:
    """Build a small, reproducible yield table with every column present."""

    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2000-01-03", periods=n_days)
    level = 4.0 + np.cumsum(rng.normal(0.0, 0.05, n_days))
    data = {"observation_date": dates}
    for offset, column in enumerate(YIELD_COLUMNS):
        data[column] = level + 0.1 * offset
    return pd.DataFrame(data)


def test_clean_drops_holidays_partial_rows_and_early_dates() -> None:
    raw = pd.DataFrame(
        {
            "observation_date": [
                "1985-01-03",
                "1981-12-09",
                "1985-01-01",
                "1985-01-02",
                "1985-01-04",
            ],
            **{column: [5.0, None, None, 5.0, "."] for column in YIELD_COLUMNS},
        }
    )
    raw.loc[1, "DGS10"] = 13.64  # partial row: only some yields present

    cleaned = clean_yields(raw)

    assert list(cleaned["observation_date"].dt.strftime("%Y-%m-%d")) == [
        "1985-01-02",
        "1985-01-03",
    ]


def test_clean_rejects_a_missing_column() -> None:
    raw = make_yields().drop(columns=["DGS10"])

    with pytest.raises(ValueError, match="missing columns"):
        clean_yields(raw)


def test_validate_rejects_an_implausible_yield() -> None:
    yields = make_yields()
    yields.loc[10, "DGS5"] = 450.0  # a decimal-point error

    with pytest.raises(ValueError, match="plausible range"):
        validate_yields(yields)


def test_validate_rejects_duplicate_dates() -> None:
    yields = make_yields()
    yields.loc[1, "observation_date"] = yields.loc[0, "observation_date"]

    with pytest.raises(ValueError, match="unique"):
        validate_yields(yields)


def test_daily_change_is_in_basis_points() -> None:
    yields = make_yields()
    features = add_features(yields)
    day = features["observation_date"].iloc[0]
    position = yields.index[yields["observation_date"] == day][0]

    expected = (
        yields.loc[position, "DGS10"] - yields.loc[position - 1, "DGS10"]
    ) * 100
    assert features["d_DGS10"].iloc[0] == pytest.approx(expected)


def test_forward_target_uses_exactly_the_next_21_days() -> None:
    yields = make_yields()
    features = add_features(yields)
    day = features["observation_date"].iloc[0]
    position = yields.index[yields["observation_date"] == day][0]

    changes = yields["DGS10"].diff() * 100
    next_days = changes.iloc[position + 1 : position + 1 + FORWARD_HORIZON]
    expected = next_days.std() * np.sqrt(TRADING_DAYS)

    assert features["vol_fwd_21d"].iloc[0] == pytest.approx(expected)


def test_trailing_features_never_use_future_data() -> None:
    yields = make_yields()
    shocked = yields.copy()
    shocked.loc[120:, list(YIELD_COLUMNS)] += 1.0  # a 100bp jump on day 120

    before = add_features(yields).set_index("observation_date")
    after = add_features(shocked).set_index("observation_date")
    cutoff = yields.loc[120, "observation_date"]
    trailing = ["rv_5d", "rv_21d", "rv_63d", "slope_2s10s", "slope_3m10y", "DGS10"]

    earlier = before.index < cutoff
    pd.testing.assert_frame_equal(
        before.loc[earlier, trailing], after.loc[earlier, trailing]
    )


def test_fixture_loads_through_the_registry() -> None:
    dataset = load_project_dataset(load_config("configs/treasury_fixture.toml"))
    regression = dataset.tasks["regression"]

    assert len(dataset.observations) > 100
    assert set(dataset.tasks) == {"regression", "unsupervised"}
    assert regression.target_column == "vol_fwd_21d"
    assert regression.target_column not in regression.feature_columns
    assert not dataset.observations.isna().any().any()