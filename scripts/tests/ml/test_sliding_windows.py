from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.ml.dataset import prepare_sliding_windows
from scripts.tests.ml.conftest import FEATURE_COLS, TARGET_COLS, PAST_DAYS, FUTURE_DAYS


class TestSlidingWindowsShape:
    def test_x_has_correct_dimensions(self, sample_sliding_windows: tuple[np.ndarray, np.ndarray]) -> None:
        X, _ = sample_sliding_windows
        assert X.ndim == 3
        assert X.shape[1] == PAST_DAYS
        assert X.shape[2] == len(FEATURE_COLS)

    def test_y_has_correct_dimensions(self, sample_sliding_windows: tuple[np.ndarray, np.ndarray]) -> None:
        _, y = sample_sliding_windows
        assert y.ndim == 3
        assert y.shape[1] == FUTURE_DAYS
        assert y.shape[2] == len(TARGET_COLS)

    def test_x_and_y_have_same_number_of_samples(
        self, sample_sliding_windows: tuple[np.ndarray, np.ndarray]
    ) -> None:
        X, y = sample_sliding_windows
        assert X.shape[0] == y.shape[0]


class TestSlidingWindowsCount:
    def test_expected_window_count_single_location(self) -> None:
        rng = np.random.default_rng(0)
        num_days = 60
        df = pd.DataFrame({
            "location_key": [1] * num_days,
            "obs_date": pd.date_range("2024-01-01", periods=num_days, freq="D"),
            **{col: rng.uniform(0, 100, num_days) for col in FEATURE_COLS},
        })
        X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)
        expected = num_days - PAST_DAYS - FUTURE_DAYS + 1
        assert X.shape[0] == expected

    def test_two_locations_double_the_windows(self) -> None:
        rng = np.random.default_rng(0)
        num_days = 60
        frames = []
        for loc in [1, 2]:
            frames.append(pd.DataFrame({
                "location_key": [loc] * num_days,
                "obs_date": pd.date_range("2024-01-01", periods=num_days, freq="D"),
                **{col: rng.uniform(0, 100, num_days) for col in FEATURE_COLS},
            }))
        df = pd.concat(frames, ignore_index=True)
        X, _ = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)
        expected_per_loc = num_days - PAST_DAYS - FUTURE_DAYS + 1
        assert X.shape[0] == 2 * expected_per_loc


class TestSlidingWindowsEdgeCases:
    def test_too_few_days_returns_empty(self) -> None:
        rng = np.random.default_rng(0)
        num_days = PAST_DAYS + FUTURE_DAYS - 2
        df = pd.DataFrame({
            "location_key": [1] * num_days,
            "obs_date": pd.date_range("2024-01-01", periods=num_days, freq="D"),
            **{col: rng.uniform(0, 100, num_days) for col in FEATURE_COLS},
        })
        X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)
        assert X.shape[0] == 0
        assert y.shape[0] == 0

    def test_exact_minimum_days_returns_one_window(self) -> None:
        rng = np.random.default_rng(0)
        num_days = PAST_DAYS + FUTURE_DAYS
        df = pd.DataFrame({
            "location_key": [1] * num_days,
            "obs_date": pd.date_range("2024-01-01", periods=num_days, freq="D"),
            **{col: rng.uniform(0, 100, num_days) for col in FEATURE_COLS},
        })
        X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)
        assert X.shape[0] == 1
        assert y.shape[0] == 1

    def test_windows_contain_correct_values(self) -> None:
        num_days = PAST_DAYS + FUTURE_DAYS
        values = np.arange(num_days, dtype=float)
        df = pd.DataFrame({
            "location_key": [1] * num_days,
            "obs_date": pd.date_range("2024-01-01", periods=num_days, freq="D"),
            **{col: values for col in FEATURE_COLS},
        })
        X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)
        np.testing.assert_array_equal(X[0, :, 0], np.arange(PAST_DAYS, dtype=float))
        np.testing.assert_array_equal(y[0, :, 0], np.arange(PAST_DAYS, PAST_DAYS + FUTURE_DAYS, dtype=float))