from __future__ import annotations

import numpy as np
import torch
import pytest

from scripts.ml.dataset import PollutionDataset
from scripts.tests.ml.conftest import FEATURE_COLS, TARGET_COLS, PAST_DAYS, FUTURE_DAYS


class TestPollutionDatasetLength:
    def test_length_matches_input_array(self) -> None:
        X = np.random.randn(50, PAST_DAYS, len(FEATURE_COLS))
        y = np.random.randn(50, FUTURE_DAYS, len(TARGET_COLS))
        ds = PollutionDataset(X, y)
        assert len(ds) == 50

    def test_length_single_sample(self) -> None:
        X = np.random.randn(1, PAST_DAYS, len(FEATURE_COLS))
        y = np.random.randn(1, FUTURE_DAYS, len(TARGET_COLS))
        ds = PollutionDataset(X, y)
        assert len(ds) == 1


class TestPollutionDatasetGetItem:
    def test_returns_tuple_of_two_tensors(self, sample_dataset: PollutionDataset) -> None:
        item = sample_dataset[0]
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert isinstance(item[0], torch.Tensor)
        assert isinstance(item[1], torch.Tensor)

    def test_feature_tensor_shape(self, sample_dataset: PollutionDataset) -> None:
        X, _ = sample_dataset[0]
        assert X.shape == (PAST_DAYS, len(FEATURE_COLS))

    def test_target_tensor_shape(self, sample_dataset: PollutionDataset) -> None:
        _, y = sample_dataset[0]
        assert y.shape == (FUTURE_DAYS, len(TARGET_COLS))

    def test_tensors_are_float32(self, sample_dataset: PollutionDataset) -> None:
        X, y = sample_dataset[0]
        assert X.dtype == torch.float32
        assert y.dtype == torch.float32

    def test_different_indices_return_different_data(self, sample_dataset: PollutionDataset) -> None:
        X0, _ = sample_dataset[0]
        X1, _ = sample_dataset[1]
        assert not torch.allclose(X0, X1)

    def test_index_out_of_range_raises(self, sample_dataset: PollutionDataset) -> None:
        with pytest.raises(IndexError):
            sample_dataset[len(sample_dataset)]