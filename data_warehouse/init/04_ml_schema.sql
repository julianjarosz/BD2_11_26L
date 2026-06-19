CREATE TABLE IF NOT EXISTS dw.fact_air_pollution_forecast (
    forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    forecast_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    forecast_for timestamptz NOT NULL,
    predicted_aqi numeric(8, 2),
    predicted_co numeric(8, 2),
    predicted_no numeric(8, 2),
    predicted_no2 numeric(8, 2),
    predicted_o3 numeric(8, 2),
    predicted_so2 numeric(8, 2),
    predicted_pm2_5 numeric(8, 2),
    predicted_pm10 numeric(8, 2),
    predicted_nh3 numeric(8, 2),
    model_version varchar(50) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_fact_air_pollution_forecast UNIQUE (location_key, forecast_for, model_version)
);

CREATE INDEX IF NOT EXISTS idx_fact_air_pollution_forecast_date_location
    ON dw.fact_air_pollution_forecast (forecast_date_key, location_key);

CREATE INDEX IF NOT EXISTS idx_fact_air_pollution_forecast_model_created
    ON dw.fact_air_pollution_forecast (model_version, created_at DESC);
