import os
import pickle
import torch
import psycopg
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta
from psycopg.rows import dict_row

from scripts.ml.model import PollutionLSTM

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / 'models'

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/weather_warehouse")
PAST_DAYS = 30
FUTURE_DAYS = 14
HIDDEN_SIZE = 64
NUM_LAYERS = 2

FEATURE_COLS = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3', 'temp', 'humidity', 'wind_speed']
TARGET_COLS = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']


def load_recent_data(db_url: str, days: int) -> pd.DataFrame:
    query = """
    WITH daily_pollution AS (
        SELECT
            location_key,
            DATE(observed_at) as obs_date,
            AVG(aqi) as aqi, AVG(co) as co, AVG(no) as "no", AVG(no2) as no2,
            AVG(o3) as o3, AVG(so2) as so2, AVG(pm2_5) as pm2_5,
            AVG(pm10) as pm10, AVG(nh3) as nh3
        FROM dw.fact_air_pollution
        WHERE observed_at >= CURRENT_DATE - make_interval(days => %(days)s)
        GROUP BY location_key, DATE(observed_at)
    ),
    daily_weather AS (
        SELECT
            location_key,
            DATE(observed_at) as obs_date,
            AVG(temp) as temp, AVG(humidity) as humidity,
            AVG(wind_speed) as wind_speed
        FROM dw.fact_current_weather
        WHERE observed_at >= CURRENT_DATE - make_interval(days => %(days)s)
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
            cur.execute(query, {"days": days})
            rows = cur.fetchall()

    df = pd.DataFrame(rows)
    if not df.empty:
        df['obs_date'] = pd.to_datetime(df['obs_date'])
        numeric_cols = df.columns.drop(['location_key', 'obs_date'])
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    return df


def ensure_forecast_dates(conn, forecast_dates):
    with conn.cursor() as cur:
        for d in forecast_dates:
            date_key = int(d.strftime("%Y%m%d"))
            cur.execute("""
                INSERT INTO dw.dim_date
                    (date_key, full_date, day, month, month_name, quarter, year,
                     day_of_the_week, day_name, is_weekend)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (
                date_key, d.date() if hasattr(d, 'date') else d,
                d.day, d.month, d.strftime("%B"),
                (d.month - 1) // 3 + 1, d.year,
                d.isoweekday(), d.strftime("%A"),
                d.weekday() >= 5,
            ))
        conn.commit()


def predict():
    print("Loading models and scalers...")
    try:
        with open(MODEL_DIR / 'scaler_X.pkl', 'rb') as f:
            scaler_X = pickle.load(f)
        with open(MODEL_DIR / 'scaler_y.pkl', 'rb') as f:
            scaler_y = pickle.load(f)
    except FileNotFoundError:
        print("Models or scalers not found. Train the model first.")
        return

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = PollutionLSTM(
        input_size=len(FEATURE_COLS),
        hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS,
        output_size=len(TARGET_COLS),
        future_days=FUTURE_DAYS
    ).to(device)

    try:
        model.load_state_dict(torch.load(MODEL_DIR / 'pollution_lstm.pt', map_location=device))
    except FileNotFoundError:
        print("Model weights not found. Train the model first.")
        return

    model.eval()

    print("Loading recent data for inference...")
    df = load_recent_data(DB_URL, days=PAST_DAYS + 5)
    if df.empty:
        print("No data available.")
        return

    locations = df['location_key'].unique()
    predictions_to_insert = []
    all_forecast_dates = set()

    with torch.no_grad():
        for loc in locations:
            loc_df = df[df['location_key'] == loc].copy()
            loc_df = loc_df.set_index('obs_date').asfreq('D')
            loc_df[FEATURE_COLS] = loc_df[FEATURE_COLS].interpolate(method='linear').bfill().ffill()

            recent_df = loc_df.tail(PAST_DAYS)
            if len(recent_df) < PAST_DAYS:
                print(f"Not enough data for location {loc}. Skipping.")
                continue

            last_date = recent_df.index[-1]

            recent_df[FEATURE_COLS] = recent_df[FEATURE_COLS].fillna(0)
            scaled_features = scaler_X.transform(recent_df[FEATURE_COLS])
            X_tensor = torch.tensor(scaled_features, dtype=torch.float32).unsqueeze(0).to(device)

            output = model(X_tensor)
            output_np = output.squeeze(0).cpu().numpy()

            predictions = scaler_y.inverse_transform(output_np)

            for i in range(FUTURE_DAYS):
                forecast_date = last_date + timedelta(days=i+1)
                all_forecast_dates.add(forecast_date)

                predictions_to_insert.append({
                    'location_key': loc,
                    'forecast_date_key': int(forecast_date.strftime("%Y%m%d")),
                    'forecast_for': forecast_date,
                    'predicted_aqi': float(predictions[i][0]),
                    'predicted_co': float(predictions[i][1]),
                    'predicted_no': float(predictions[i][2]),
                    'predicted_no2': float(predictions[i][3]),
                    'predicted_o3': float(predictions[i][4]),
                    'predicted_so2': float(predictions[i][5]),
                    'predicted_pm2_5': float(predictions[i][6]),
                    'predicted_pm10': float(predictions[i][7]),
                    'predicted_nh3': float(predictions[i][8]),
                    'model_version': 'v1.0.0_lstm'
                })

    if not predictions_to_insert:
        print("No predictions to insert.")
        return

    print(f"Inserting {len(predictions_to_insert)} predictions into the database...")

    insert_query = """
    INSERT INTO dw.fact_air_pollution_forecast (
        location_key, forecast_date_key, forecast_for,
        predicted_aqi, predicted_co, predicted_no, predicted_no2, predicted_o3,
        predicted_so2, predicted_pm2_5, predicted_pm10, predicted_nh3, model_version
    ) VALUES (
        %(location_key)s, %(forecast_date_key)s, %(forecast_for)s,
        %(predicted_aqi)s, %(predicted_co)s, %(predicted_no)s, %(predicted_no2)s, %(predicted_o3)s,
        %(predicted_so2)s, %(predicted_pm2_5)s, %(predicted_pm10)s, %(predicted_nh3)s, %(model_version)s
    ) ON CONFLICT (location_key, forecast_for, model_version) DO UPDATE SET
        predicted_aqi = EXCLUDED.predicted_aqi,
        predicted_co = EXCLUDED.predicted_co,
        predicted_no = EXCLUDED.predicted_no,
        predicted_no2 = EXCLUDED.predicted_no2,
        predicted_o3 = EXCLUDED.predicted_o3,
        predicted_so2 = EXCLUDED.predicted_so2,
        predicted_pm2_5 = EXCLUDED.predicted_pm2_5,
        predicted_pm10 = EXCLUDED.predicted_pm10,
        predicted_nh3 = EXCLUDED.predicted_nh3,
        created_at = now();
    """

    with psycopg.connect(DB_URL) as conn:
        ensure_forecast_dates(conn, all_forecast_dates)
        with conn.cursor() as cur:
            cur.executemany(insert_query, predictions_to_insert)
            conn.commit()

    print("Inference completed successfully.")

if __name__ == '__main__':
    predict()
