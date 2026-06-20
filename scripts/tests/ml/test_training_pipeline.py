from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.preprocessing import MinMaxScaler

from scripts.ml.dataset import PollutionDataset, prepare_sliding_windows, interpolate_missing
from scripts.ml.model import PollutionLSTM
from scripts.tests.ml.conftest import FEATURE_COLS, TARGET_COLS, PAST_DAYS, FUTURE_DAYS


class TestTrainingPipelineEndToEnd:
    def test_loss_decreases_after_training(self, sample_pollution_df) -> None:
        df = interpolate_missing(sample_pollution_df, FEATURE_COLS, TARGET_COLS)
        X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)

        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        X_flat = scaler_X.fit_transform(X.reshape(-1, X.shape[-1]))
        X_scaled = X_flat.reshape(X.shape)
        y_flat = scaler_y.fit_transform(y.reshape(-1, y.shape[-1]))
        y_scaled = y_flat.reshape(y.shape)

        dataset = PollutionDataset(X_scaled, y_scaled)
        loader = DataLoader(dataset, batch_size=8, shuffle=True)

        model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=32,
            num_layers=1,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.01)

        model.train()
        first_loss = None
        last_loss = None
        for _ in range(15):
            epoch_loss = 0.0
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                out = model(batch_X)
                loss = criterion(out, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * batch_X.size(0)
            epoch_loss /= len(loader.dataset)
            if first_loss is None:
                first_loss = epoch_loss
            last_loss = epoch_loss

        assert last_loss < first_loss

    def test_model_can_overfit_small_batch(self) -> None:
        rng = np.random.default_rng(7)
        X = rng.standard_normal((4, PAST_DAYS, len(FEATURE_COLS))).astype(np.float32)
        y = rng.standard_normal((4, FUTURE_DAYS, len(TARGET_COLS))).astype(np.float32)

        dataset = PollutionDataset(X, y)
        loader = DataLoader(dataset, batch_size=4, shuffle=False)

        model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=64,
            num_layers=1,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.005)

        model.train()
        for _ in range(100):
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                out = model(batch_X)
                loss = criterion(out, batch_y)
                loss.backward()
                optimizer.step()

        model.eval()
        with torch.no_grad():
            final_loss = criterion(model(dataset.X), dataset.y).item()
        assert final_loss < 0.5


class TestTrainingPipelineGradients:
    def test_gradients_flow_through_all_parameters(self) -> None:
        model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=32,
            num_layers=1,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        x = torch.randn(2, PAST_DAYS, len(FEATURE_COLS))
        y = torch.randn(2, FUTURE_DAYS, len(TARGET_COLS))

        out = model(x)
        loss = nn.MSELoss()(out, y)
        loss.backward()

        for name, param in model.named_parameters():
            assert param.grad is not None, f"No gradient for {name}"
            assert param.grad.abs().sum() > 0, f"Zero gradient for {name}"

    def test_weights_change_after_optimizer_step(self) -> None:
        model = PollutionLSTM(
            input_size=len(FEATURE_COLS),
            hidden_size=32,
            num_layers=1,
            output_size=len(TARGET_COLS),
            future_days=FUTURE_DAYS,
        )
        optimizer = optim.Adam(model.parameters(), lr=0.01)

        initial_weights = {name: p.clone() for name, p in model.named_parameters()}

        x = torch.randn(2, PAST_DAYS, len(FEATURE_COLS))
        y = torch.randn(2, FUTURE_DAYS, len(TARGET_COLS))
        optimizer.zero_grad()
        loss = nn.MSELoss()(model(x), y)
        loss.backward()
        optimizer.step()

        for name, param in model.named_parameters():
            assert not torch.allclose(param, initial_weights[name]), f"Weights unchanged for {name}"
