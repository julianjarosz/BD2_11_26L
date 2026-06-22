from __future__ import annotations

import torch

from scripts.ml.model import PollutionLSTM
from scripts.tests.ml.conftest import (
    FEATURE_COLS,
    TARGET_COLS,
    PAST_DAYS,
    FUTURE_DAYS,
    BATCH_SIZE,
)


class TestPollutionLSTMOutputShape:
    def test_single_sample_output_shape(self, sample_model: PollutionLSTM) -> None:
        x = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        out = sample_model(x)
        assert out.shape == (1, FUTURE_DAYS, len(TARGET_COLS))

    def test_batch_output_shape(self, sample_model: PollutionLSTM) -> None:
        x = torch.randn(BATCH_SIZE, PAST_DAYS, len(FEATURE_COLS))
        out = sample_model(x)
        assert out.shape == (BATCH_SIZE, FUTURE_DAYS, len(TARGET_COLS))

    def test_output_dtype_is_float32(self, sample_model: PollutionLSTM) -> None:
        x = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        out = sample_model(x)
        assert out.dtype == torch.float32


class TestPollutionLSTMForwardPass:
    def test_output_is_finite(self, sample_model: PollutionLSTM) -> None:
        x = torch.randn(BATCH_SIZE, PAST_DAYS, len(FEATURE_COLS))
        out = sample_model(x)
        assert torch.isfinite(out).all()

    def test_different_inputs_produce_different_outputs(self, sample_model: PollutionLSTM) -> None:
        x1 = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        x2 = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        out1 = sample_model(x1)
        out2 = sample_model(x2)
        assert not torch.allclose(out1, out2)

    def test_eval_mode_is_deterministic(self, sample_model: PollutionLSTM) -> None:
        sample_model.eval()
        x = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        with torch.no_grad():
            out1 = sample_model(x)
            out2 = sample_model(x)
        assert torch.allclose(out1, out2)


class TestPollutionLSTMInitialization:
    def test_default_hidden_size(self) -> None:
        model = PollutionLSTM(
            input_size=12, hidden_size=64, num_layers=2, output_size=9, future_days=14
        )
        assert model.hidden_size == 64

    def test_custom_parameters(self) -> None:
        model = PollutionLSTM(
            input_size=5, hidden_size=128, num_layers=3, output_size=3, future_days=7
        )
        assert model.num_layers == 3
        assert model.future_days == 7
        assert model.output_size == 3

    def test_model_has_trainable_parameters(self, sample_model: PollutionLSTM) -> None:
        param_count = sum(p.numel() for p in sample_model.parameters() if p.requires_grad)
        assert param_count > 0
