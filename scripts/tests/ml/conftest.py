from __future__ import annotations

# pylint: disable=redefined-outer-name

import numpy as np
import pandas as pd
import pytest
import torch

from scripts.ml.dataset import PollutionDataset, prepare_sliding_windows
from scripts.ml.model import PollutionLSTM

FEATURE_COLS = [
    "aqi",
    "co",
    "no",
    "no2",
    "o3",
    "so2",
    "pm2_5",
    "pm10",
    "nh3",
    "temp",
    "humidity",
    "wind_speed",
]
TARGET_COLS = ["aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]

PAST_DAYS = 30
FUTURE_DAYS = 14
HIDDEN_SIZE = 32
NUM_LAYERS = 1
BATCH_SIZE = 4


@pytest.fixture()
def sample_pollution_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    num_days = 90
    dates = pd.date_range("2024-01-01", periods=num_days, freq="D")

    records = []
    for loc_key in [1, 2]:
        for date in dates:
            row = {"location_key": loc_key, "obs_date": date}
            for col in FEATURE_COLS:
                row[col] = rng.uniform(0, 100)
            records.append(row)

    return pd.DataFrame(records)


@pytest.fixture()
def sample_pollution_df_with_gaps(sample_pollution_df: pd.DataFrame) -> pd.DataFrame:
    df = sample_pollution_df.copy()
    rng = np.random.default_rng(99)
    mask = rng.random(len(df)) < 0.15
    for col in FEATURE_COLS:
        df.loc[mask, col] = np.nan
    df = df.drop(df.index[10:13])
    return df.reset_index(drop=True)


@pytest.fixture()
def sample_sliding_windows(sample_pollution_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return prepare_sliding_windows(
        sample_pollution_df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS
    )


@pytest.fixture()
def sample_model() -> PollutionLSTM:
    return PollutionLSTM(
        input_size=len(FEATURE_COLS),
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        output_size=len(TARGET_COLS),
        future_days=FUTURE_DAYS,
    )


@pytest.fixture()
def sample_dataset(sample_sliding_windows: tuple[np.ndarray, np.ndarray]) -> PollutionDataset:
    X, y = sample_sliding_windows
    return PollutionDataset(X, y)


@pytest.fixture()
def sample_batch(sample_dataset: PollutionDataset) -> tuple[torch.Tensor, torch.Tensor]:
    X_batch = sample_dataset.X[:BATCH_SIZE]
    y_batch = sample_dataset.y[:BATCH_SIZE]
    return X_batch, y_batch
