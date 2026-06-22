from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import MinMaxScaler

from scripts.ml.dataset import scale_data
from scripts.tests.ml.conftest import FEATURE_COLS, TARGET_COLS


def _make_df(rng: np.random.Generator, n: int = 60) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "location_key": [1] * n,
            "obs_date": pd.date_range("2024-01-01", periods=n, freq="D"),
            **{col: rng.uniform(10, 500, n) for col in FEATURE_COLS},
        }
    )


class TestScaleDataFit:
    def test_scaled_features_in_0_1_range(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        scaled, _, _ = scale_data(
            df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=True
        )
        for col in FEATURE_COLS:
            assert scaled[col].min() >= -1e-9
            assert scaled[col].max() <= 1.0 + 1e-9

    def test_scaled_targets_in_0_1_range(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        scaled, _, _ = scale_data(
            df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=True
        )
        for col in TARGET_COLS:
            assert scaled[col].min() >= -1e-9
            assert scaled[col].max() <= 1.0 + 1e-9

    def test_returns_fitted_scalers(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        _, returned_X, returned_y = scale_data(
            df, FEATURE_COLS, TARGET_COLS, scaler_X, scaler_y, fit=True
        )
        assert hasattr(returned_X, "data_min_")
        assert hasattr(returned_y, "data_min_")


class TestScaleDataTransformOnly:
    def test_transform_uses_existing_scaler(self) -> None:
        rng = np.random.default_rng(42)
        df_train = _make_df(rng, n=60)
        df_test = _make_df(rng, n=20)

        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        _, scaler_X, scaler_y = scale_data(
            df_train, FEATURE_COLS, TARGET_COLS, scaler_X, scaler_y, fit=True
        )

        scaled_test, _, _ = scale_data(
            df_test, FEATURE_COLS, TARGET_COLS, scaler_X, scaler_y, fit=False
        )
        assert len(scaled_test) == 20

    def test_transform_without_fit_raises(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        with pytest.raises(Exception):
            scale_data(df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=False)


class TestScaleDataPreservesStructure:
    def test_non_numeric_columns_unchanged(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        scaled, _, _ = scale_data(
            df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=True
        )
        assert list(scaled["location_key"].unique()) == [1]
        assert len(scaled["obs_date"]) == len(df["obs_date"])

    def test_column_order_preserved(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng)
        scaled, _, _ = scale_data(
            df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=True
        )
        assert list(scaled.columns) == list(df.columns)

    def test_row_count_preserved(self) -> None:
        rng = np.random.default_rng(42)
        df = _make_df(rng, n=45)
        scaled, _, _ = scale_data(
            df, FEATURE_COLS, TARGET_COLS, MinMaxScaler(), MinMaxScaler(), fit=True
        )
        assert len(scaled) == 45
