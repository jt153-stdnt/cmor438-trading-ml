"""Adapter for daily FRED Treasury constant-maturity yields."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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
START_DATE = "1985-01-01"
FORWARD_HORIZON = 21


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
        return yields  # TEMPORARY: remove once the dataset is built
        # TODO: validate, compute features, build and return the dataset