"""
### ML: Daily air pollution forecast using LSTM model
"""

from __future__ import annotations

import sys
from pathlib import Path

from airflow.decorators import dag, task
from pendulum import datetime, duration

PROJECT_ROOT = Path("/opt/airflow/project")
if not PROJECT_ROOT.exists():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dag(
    dag_display_name="ML pollution forecast",
    dag_id="ml_pollution_forecast",
    start_date=datetime(2026, 1, 1, tz="Europe/Warsaw"),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "Data team",
        "retries": 2,
        "retry_delay": duration(minutes=5),
    },
    doc_md=__doc__,
    description="Daily LSTM inference for air pollution prediction",
    tags=["ml", "pollution", "forecast"],
)
def ml_pollution_forecast():
    @task
    def run_lstm_inference() -> None:
        """Load the trained LSTM model and generate 14-day pollution forecasts."""
        from scripts.ml.predict import predict

        predict()

    run_lstm_inference()


ml_pollution_forecast()
