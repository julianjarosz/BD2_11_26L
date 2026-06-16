import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import MinMaxScaler
import psycopg
from psycopg.rows import dict_row

class PollutionDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def load_data_from_db(db_url: str) -> pd.DataFrame:
    query = """
    WITH daily_pollution AS (
        SELECT
            location_key,
            DATE(observed_at) as obs_date,
            AVG(aqi) as aqi, AVG(co) as co, AVG(no) as "no", AVG(no2) as no2,
            AVG(o3) as o3, AVG(so2) as so2, AVG(pm2_5) as pm2_5,
            AVG(pm10) as pm10, AVG(nh3) as nh3
        FROM dw.fact_air_pollution
        GROUP BY location_key, DATE(observed_at)
    ),
    daily_weather AS (
        SELECT
            location_key,
            DATE(observed_at) as obs_date,
            AVG(temp) as temp, AVG(humidity) as humidity,
            AVG(wind_speed) as wind_speed
        FROM dw.fact_current_weather
        GROUP BY location_key, DATE(observed_at)
    )
    SELECT
        p.location_key, p.obs_date,
        p.aqi, p.co, p."no", p.no2, p.o3, p.so2, p.pm2_5, p.pm10, p.nh3,
        w.temp, w.humidity, w.wind_speed
    FROM daily_pollution p
    LEFT JOIN daily_weather w
        ON p.location_key = w.location_key AND p.obs_date = w.obs_date
    ORDER BY p.location_key, p.obs_date;
    """
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    df = pd.DataFrame(rows)
    if not df.empty:
        df['obs_date'] = pd.to_datetime(df['obs_date']) # convert date to datetime for the sliding windows
        numeric_cols = df.columns.drop(['location_key', 'obs_date'])
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    return df

def prepare_sliding_windows(df: pd.DataFrame, past_days: int, future_days: int, feature_cols: list, target_cols: list):
    """
    prepares sliding windows used for training and prediction
    (we can't train the model on every single day - hence sliding windows)
    sliding window X: (past_days x num_features)
    sliding prediction window Y: (future_days x num_targets)
    """
    X, y = [], []
    locations = df['location_key'].unique()

    for loc in locations:
        loc_df = df[df['location_key'] == loc].copy()

        features_array = loc_df[feature_cols].values
        targets_array = loc_df[target_cols].values

        for i in range(len(loc_df) - past_days - future_days + 1):
            X.append(features_array[i:i + past_days])
            y.append(targets_array[i + past_days:i + past_days + future_days])

    return np.array(X), np.array(y)

def interpolate_missing(df: pd.DataFrame, feature_cols: list, target_cols: list) -> pd.DataFrame:
    all_cols = list(set(feature_cols + target_cols))
    parts = []
    for loc in df['location_key'].unique():
        loc_df = df[df['location_key'] == loc].copy()
        loc_df = loc_df.set_index('obs_date').asfreq('D')
        loc_df['location_key'] = loc
        loc_df[all_cols] = loc_df[all_cols].interpolate(method='linear').bfill().ffill()
        parts.append(loc_df.reset_index())
    return pd.concat(parts, ignore_index=True)

def scale_data(df: pd.DataFrame, feature_cols: list, target_cols: list, scaler_X: MinMaxScaler, scaler_y: MinMaxScaler, fit: bool = True):
    df_scaled = df.copy()
    if fit:
        df_scaled[feature_cols] = scaler_X.fit_transform(df_scaled[feature_cols])
        df_scaled[target_cols] = scaler_y.fit_transform(df_scaled[target_cols])
    else:
        df_scaled[feature_cols] = scaler_X.transform(df_scaled[feature_cols])
        df_scaled[target_cols] = scaler_y.transform(df_scaled[target_cols])
    return df_scaled, scaler_X, scaler_y
