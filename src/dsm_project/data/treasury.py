"""Adapter for daily FRED Treasury constant-maturity yields."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from dsm_project.config import ProjectConfig
from dsm_project.contracts import (
    DatasetProvenance,
    ProjectDataset,
    TaskDefinition,
    TaskKind,
)

# Treasury maturities, shortest to longest
YIELD_COLUMNS = (
    "DGS3MO",
    "DGS6MO",
    "DGS1",
    "DGS2",
    "DGS3",
    "DGS5",
    "DGS7",
    "DGS10",
)
REGRESSION_FEATURES = (
    "rv_5d",
    "rv_21d",
    "rv_63d",
    "slope_2s10s",
    "slope_3m10y",
    "DGS10",
)
CHANGE_COLUMNS = tuple(f"d_{column}" for column in YIELD_COLUMNS)

START_DATE = "1985-01-01"
FORWARD_HORIZON = 21
TRADING_DAYS = 252  # for annualizing volatilities

def clean_yields(raw: pd.DataFrame) -> pd.DataFrame:
    """Return complete, date-sorted yield rows from START_DATE onward.

    Drops market holidays (all yields blank) and partial rows rather than
    filling them in.
    """

    required = ("observation_date", *YIELD_COLUMNS)
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Treasury data is missing columns: {missing}")

    frame = raw.loc[:, list(required)].copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    for column in YIELD_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=list(YIELD_COLUMNS))
    frame = frame[frame["observation_date"] >= START_DATE]
    return frame.sort_values("observation_date").reset_index(drop=True)

def validate_yields(yields: pd.DataFrame) -> None:
    """Reject cleaned yields that cannot be correct."""

    if yields.empty:
        raise ValueError("No Treasury yield rows remain after cleaning")
    if not yields["observation_date"].is_unique:
        raise ValueError("Treasury dates must be unique")
    if not yields["observation_date"].is_monotonic_increasing:
        raise ValueError("Treasury dates must be sorted ascending")

    values = yields.loc[:, list(YIELD_COLUMNS)]
    if ((values < -1.0) | (values > 25.0)).any().any():
        raise ValueError("Treasury yields outside the plausible range [-1%, 25%]")


def add_features(yields: pd.DataFrame) -> pd.DataFrame:
    """Add bp changes, trailing vol, curve slopes, and the forward vol target.

    Every feature on day t uses data up to and including t. Only the target
    vol_fwd_21d looks ahead (days t+1 ... t+21).
    """

    frame = yields.copy()
    annualize = np.sqrt(TRADING_DAYS)

    for column in YIELD_COLUMNS:
        frame[f"d_{column}"] = frame[column].diff() * 100

    change_10y = frame["d_DGS10"]
    for window in (5, 21, 63):
        frame[f"rv_{window}d"] = change_10y.rolling(window).std() * annualize

    frame["slope_2s10s"] = (frame["DGS10"] - frame["DGS2"]) * 100
    frame["slope_3m10y"] = (frame["DGS10"] - frame["DGS3MO"]) * 100

    future_std = change_10y.rolling(FORWARD_HORIZON).std().shift(-FORWARD_HORIZON)
    frame["vol_fwd_21d"] = future_std * annualize

    return frame.dropna().reset_index(drop=True)

class TreasuryYieldAdapter:
    """Load, clean, and validate daily FRED Treasury yields into a ProjectDataset."""

    def load(self, config: ProjectConfig) -> ProjectDataset:
        """Read the configured file and return a validated dataset."""

        path_setting = config.dataset.get("path")
        if not path_setting:
            raise ValueError("dataset.path is required in the config")
        data_path = config.root / Path(str(path_setting))
        if not data_path.is_file():
            raise FileNotFoundError(
                f"Treasury yield data not found at {data_path}. "
                "Download it from FRED; see docs/DATASET_CARD.md."
            )
        raw = pd.read_csv(data_path)
        yields = clean_yields(raw)
        validate_yields(yields)
        features = add_features(yields)
        tasks = {
            "regression": TaskDefinition(
                name=str(config.tasks["regression"]["name"]),
                kind=TaskKind.REGRESSION,
                feature_columns=REGRESSION_FEATURES,
                target_column=str(config.tasks["regression"]["target"]),
                metric=str(config.tasks["regression"]["metric"]),
            ),
            "unsupervised": TaskDefinition(
                name=str(config.tasks["unsupervised"]["name"]),
                kind=TaskKind.UNSUPERVISED,
                feature_columns=CHANGE_COLUMNS,
                target_column=None,
                metric=str(config.tasks["unsupervised"]["metric"]),
            ),
        }
        dataset = ProjectDataset(
            observations=features,
            identifier="observation_date",
            tasks=tasks,
            provenance=DatasetProvenance(
                name=str(config.dataset["name"]),
                source=str(config.dataset["source"]),
                license=str(config.dataset["license"]),
                observation_unit=str(config.dataset["observation_unit"]),
            ),
        )
        dataset.validate()
        return dataset