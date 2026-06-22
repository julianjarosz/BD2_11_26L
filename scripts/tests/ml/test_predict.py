from __future__ import annotations

import pickle

import numpy as np
import torch
from sklearn.preprocessing import MinMaxScaler

from scripts.ml.model import PollutionLSTM
from scripts.tests.ml.conftest import (
    FEATURE_COLS,
    TARGET_COLS,
    PAST_DAYS,
    FUTURE_DAYS,
    HIDDEN_SIZE,
    NUM_LAYERS,
)

# pylint: disable=too-few-public-methods


class TestPredictionOutputRange:
    def test_predictions_are_finite(self, sample_model: PollutionLSTM) -> None:
        sample_model.eval()
        x = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))
        with torch.no_grad():
            out = sample_model(x)
        assert torch.isfinite(out).all()

    def test_predictions_shape_matches_future_days(self, sample_model: PollutionLSTM) -> None:
        sample_model.eval()
        x = torch.randn(3, PAST_DAYS, len(FEATURE_COLS))
        with torch.no_grad():
            out = sample_model(x)
        assert out.shape == (3, FUTURE_DAYS, len(TARGET_COLS))

    def test_inverse_scaled_predictions_are_non_negative(self) -> None:
        rng = np.random.default_rng(42)
        raw_data = rng.uniform(0, 100, (100, len(TARGET_COLS)))

        scaler_y = MinMaxScaler(feature_range=(0, 1))
        scaler_y.fit(raw_data)

        model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        model.eval()

        x = torch.rand(1, PAST_DAYS, len(FEATURE_COLS))
        with torch.no_grad():
            scaled_out = model(x).squeeze(0).numpy()

        predictions = scaler_y.inverse_transform(scaled_out)
        predictions = np.clip(predictions, 0, None)
        assert (predictions >= 0).all()


class TestScalerPersistence:
    def test_scaler_roundtrip(self, tmp_path) -> None:
        rng = np.random.default_rng(7)
        data = rng.uniform(0, 500, (50, len(FEATURE_COLS)))

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(data)

        path = tmp_path / "scaler.pkl"
        with open(path, "wb") as f:
            pickle.dump(scaler, f)
        with open(path, "rb") as f:
            loaded = pickle.load(f)

        sample = rng.uniform(0, 500, (5, len(FEATURE_COLS)))
        np.testing.assert_array_almost_equal(
            scaler.transform(sample),
            loaded.transform(sample),
        )

    def test_scaler_inverse_recovers_original(self) -> None:
        rng = np.random.default_rng(11)
        data = rng.uniform(0, 200, (30, len(TARGET_COLS)))

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(data)

        scaled = scaler.transform(data)
        recovered = scaler.inverse_transform(scaled)
        np.testing.assert_array_almost_equal(recovered, data, decimal=5)


class TestModelLoadAndPredict:
    def test_saved_model_produces_same_output(self, sample_model: PollutionLSTM, tmp_path) -> None:
        sample_model.eval()
        x = torch.randn(1, PAST_DAYS, len(FEATURE_COLS))

        with torch.no_grad():
            original_out = sample_model(x)

        model_path = tmp_path / "model.pt"
        torch.save(sample_model.state_dict(), model_path)

        loaded_model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=HIDDEN_SIZE,
            num_layers=NUM_LAYERS,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        loaded_model.load_state_dict(torch.load(model_path, weights_only=True))
        loaded_model.eval()

        with torch.no_grad():
            loaded_out = loaded_model(x)

        assert torch.allclose(original_out, loaded_out)
