import os
import pickle
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

from scripts.ml.dataset import load_data_from_db, prepare_sliding_windows, interpolate_missing, PollutionDataset
from scripts.ml.model import PollutionLSTM

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/weather_warehouse")
PAST_DAYS = 30
FUTURE_DAYS = 14
BATCH_SIZE = 32
NUM_EPOCHS = 50
LEARNING_RATE = 0.001
HIDDEN_SIZE = 64
NUM_LAYERS = 2
TEST_SIZE = 0.2
RANDOM_STATE = 42
FEATURE_COLS = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3', 'temp', 'humidity', 'wind_speed']
TARGET_COLS = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']

def train():
    print("Loading data from DB...")
    df = load_data_from_db(DB_URL)
    if df.empty:
        print("No data available for training.")
        return

    print("Interpolating missing values...")
    df = interpolate_missing(df, FEATURE_COLS, TARGET_COLS)

    print("Preparing sliding windows...")
    X, y = prepare_sliding_windows(df, PAST_DAYS, FUTURE_DAYS, FEATURE_COLS, TARGET_COLS)

    if len(X) == 0:
        print("Not enough sequences to train.")
        return

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    print("Scaling data (fit on train set only)...")
    scaler_X = MinMaxScaler(feature_range=(0, 1))
    scaler_y = MinMaxScaler(feature_range=(0, 1))

    X_train_flat = X_train.reshape(-1, X_train.shape[-1])
    scaler_X.fit(X_train_flat)
    X_train = scaler_X.transform(X_train_flat).reshape(X_train.shape)
    X_test = scaler_X.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)

    y_train_flat = y_train.reshape(-1, y_train.shape[-1])
    scaler_y.fit(y_train_flat)
    y_train = scaler_y.transform(y_train_flat).reshape(y_train.shape)
    y_test = scaler_y.transform(y_test.reshape(-1, y_test.shape[-1])).reshape(y_test.shape)

    train_dataset = PollutionDataset(X_train, y_train)
    test_dataset = PollutionDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    model = PollutionLSTM(
        input_size=len(FEATURE_COLS),
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        output_size=len(TARGET_COLS),
        future_days=FUTURE_DAYS
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print("Starting training...")
    for epoch in range(NUM_EPOCHS):
        model.train()
        train_loss = 0.0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * batch_X.size(0)

        train_loss /= len(train_loader.dataset)

        # validation phase
        model.eval()
        test_loss = 0.0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                test_loss += loss.item() * batch_X.size(0)
        test_loss /= len(test_loader.dataset)

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{NUM_EPOCHS} - Train Loss: {train_loss:.6f} - Test Loss: {test_loss:.6f}")

    # save the model and scalers for prediction later on
    os.makedirs('models', exist_ok=True)
    torch.save(model.state_dict(), 'models/pollution_lstm.pt')
    with open('models/scaler_X.pkl', 'wb') as f:
        pickle.dump(scaler_X, f)
    with open('models/scaler_y.pkl', 'wb') as f:
        pickle.dump(scaler_y, f)

    print("Training finished. Models saved to 'models/' directory.")

if __name__ == '__main__':
    train()
