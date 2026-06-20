from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.ml.dataset import interpolate_missing
from scripts.tests.ml.conftest import FEATURE_COLS, TARGET_COLS


class TestInterpolateMissingFillsGaps:
    def test_no_nans_after_interpolation(self, sample_pollution_df_with_gaps: pd.DataFrame) -> None:
        result = interpolate_missing(sample_pollution_df_with_gaps, FEATURE_COLS, TARGET_COLS)
        for col in FEATURE_COLS:
            assert not result[col].isna().any(), f"NaN remaining in column {col}"

    def test_preserves_non_null_values(self, sample_pollution_df: pd.DataFrame) -> None:
        original_values = sample_pollution_df[FEATURE_COLS].values.copy()
        result = interpolate_missing(sample_pollution_df, FEATURE_COLS, TARGET_COLS)
        np.testing.assert_array_almost_equal(
            result[FEATURE_COLS].values[:len(original_values)],
            original_values,
        )

    def test_location_key_preserved(self, sample_pollution_df_with_gaps: pd.DataFrame) -> None:
        result = interpolate_missing(sample_pollution_df_with_gaps, FEATURE_COLS, TARGET_COLS)
        assert set(result["location_key"].unique()) == set(
            sample_pollution_df_with_gaps["location_key"].unique()
        )


class TestInterpolateMissingDateContinuity:
    def test_fills_missing_dates(self) -> None:
        dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-05", "2024-01-06"])
        df = pd.DataFrame({
            "location_key": [1] * 4,
            "obs_date": dates,
            **{col: [10.0, 20.0, 50.0, 60.0] for col in FEATURE_COLS},
        })
        result = interpolate_missing(df, FEATURE_COLS, TARGET_COLS)
        loc_result = result[result["location_key"] == 1]
        assert len(loc_result) == 6

    def test_interpolated_values_are_between_neighbors(self) -> None:
        dates = pd.to_datetime(["2024-01-01", "2024-01-03"])
        df = pd.DataFrame({
            "location_key": [1] * 2,
            "obs_date": dates,
            **{col: [10.0, 30.0] for col in FEATURE_COLS},
        })
        result = interpolate_missing(df, FEATURE_COLS, TARGET_COLS)
        loc_result = result[result["location_key"] == 1].sort_values("obs_date")
        middle_val = loc_result.iloc[1][FEATURE_COLS[0]]
        assert 10.0 < middle_val < 30.0


class TestInterpolateMissingPerLocation:
    def test_locations_interpolated_independently(self) -> None:
        df = pd.DataFrame({
            "location_key": [1, 1, 1, 2, 2, 2],
            "obs_date": pd.to_datetime([
                "2024-01-01", "2024-01-02", "2024-01-03",
                "2024-01-01", "2024-01-02", "2024-01-03",
            ]),
            **{col: [10.0, np.nan, 30.0, 100.0, np.nan, 300.0] for col in FEATURE_COLS},
        })
        result = interpolate_missing(df, FEATURE_COLS, TARGET_COLS)

        loc1 = result[result["location_key"] == 1].sort_values("obs_date")
        loc2 = result[result["location_key"] == 2].sort_values("obs_date")

        assert abs(loc1.iloc[1][FEATURE_COLS[0]] - 20.0) < 1e-6
        assert abs(loc2.iloc[1][FEATURE_COLS[0]] - 200.0) < 1e-6

    def test_output_has_all_locations(self, sample_pollution_df_with_gaps: pd.DataFrame) -> None:
        result = interpolate_missing(sample_pollution_df_with_gaps, FEATURE_COLS, TARGET_COLS)
        assert len(result["location_key"].unique()) == len(
            sample_pollution_df_with_gaps["location_key"].unique()
        )
