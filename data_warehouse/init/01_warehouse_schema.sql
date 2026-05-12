CREATE SCHEMA IF NOT EXISTS dw;
SET search_path TO dw;

CREATE TABLE dim_date (
    date_key integer PRIMARY KEY,
    full_date data NOT NULL UNIQUE,
    day integer NOT NULL CHECK (day BETWEEN 1 AND 31),
    month integer NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name varchar(20) NOT NULL,
    quarter integer NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year integer NOT NULL,
    day_of_the_week integer NOT NULL CHECK (day_of_the_week BETWEEN 1 AND 7),
    day_name varchar(20) NOT NULL, 
    is_weekend boolean NOT NULL
);

CREATE TABLE dim_time (
    time_key integer PRIMARY KEY,
    full_time time NOT NULL UNIQUE,
    hour integer NOT NULL CHECK (hour BETWEEN 0 AND 23),
    minute integer NOT NULL CHECK (minute BETWEEN 0 AND 59),
    second integer NOT NULL CHECK (second BETWEEN 0 AND 59),
    part_of_the_dat varchar(20) NOT NULL
);

CREATE TABLE dim_location (
    location_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id_nk bigint UNIQUE, 
    city_name varchar(100),
    country_code char(2),
    latitude numeric(10, 6),
    longitude numeric(10, 6),
    timezone varchar(64),
    timezone_offset integer,
    -- skąd te wartości?
    CONSTRAINT check_dim_location_lat CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT check_dim_location_lon CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
);

CREATE TABLE dim_weather_condition (
    weather_condition_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    condiiton_id_nk bigint UNIQUE,
    openweather_weather_id integer,
    main varchar(50),
    description varchar(100),
    icon varchar(4)
);

CREATE TABLE fact_current_weather (
    current_weather_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    current_weather_id_nk bigint UNIQUE,
    lcoatioN_key bigint NOT NULL REFERENCES dim_location(location_key),
    observed_date_key integer NOT NULL REFERENCES dim_date(date_key),
    observed_time_key integer NOT NULL REFERENCES dim_time(time_key),
    weather_condition_key integer NOT NULL REFERENCES dim_weather_condition(weather_condition_key),
    observed_at timestampz,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    visibility integer,
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2)
);

CREATE TABLE fact_hourly_forecast (
    hourly_forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    houtly_forecast_id_nk, bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dim_location(location_key),
    forecast_date_key NOT NULL REFERENCES dim_date(date_key),
    forecast_time_key NOT NULL REFERENCES dim_time(time_key),
    weather_condition_key NOT NULL REFERENCES dim_weather_condition(weather_condition_key),
    forecast_for timestampz,
    retrieved_at timestampz,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NUL OR humidity BETWEEN 0 AND 100),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEENM 0 AND 100),
    pop numeric(4, 3) CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2)
);

CREATE TABLE fact_daily_forecast (
    daily_forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    daily_forecast_id_nk bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dim_location(location_key),
    forecast_date_key integer NOT NULL REFERENCES dim_date(date_key),
    weather_condition_key bigint NOT NULL REFERENCES dim_weather_condition(weather_condition_key),
    forecast_date date,
    retrieved_at timestamptz,
    temp_day numeric(5, 2),
    temp_min numeric(5, 2),
    temp_max numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    pop numeric(4, 3) CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    rain numeric(6, 2),
    snow numeric(6, 2),
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360)
);

CREATET TABLE fact_air_pollution (
    air_pollution_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    air_pollution_id_nk bigint UNIQUE,
    location_key NOT NULL REFERENCES dim_location(location_key),
    observed_date_key NOT NULL REFERENCES dim_date(date_key),
    observed_time_key NOT NULL REFERENCES dim_time(time_key),
    observed_at timestampz,
    aqi integer CHECK (aqi IS NULL OR aqi BETWEEN 1 AND 5),
    co numeric(8, 2),
    no numeric(8, 2),
    no2 numeric(8, 2),
    o3 numeric(8, 2),
    so2 numeric(8, 2),
    pm2_5 numeric(8, 2),
    pm10 numeric(8, 2),
    nh3 numeric(8, 2)
);

CREATE TABLE fact_forecast_accuracy (
    forecast_accuracy_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_key bigint NOT NULL REFERENCES dim_location(location_key),
    observed_date_key bigint NOT NULL REFERENCES dim_date(date_key),
    observed_time_key bigint NOT NULL REFERENCES dim_time(time_key),
    forecast_temp numeric(5, 2),
    actual_temp numeric(5, 2),
    temp_error numeric(6, 2),
    abs_temp_error numeric(6, 2) CHECK (abs_temp_error IS NULL OR abs_temp_error >= 0)
);

CREATE TABLE fact_weather_alert (
    weather_alert_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    weather_alert_id_nk bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dim_location(location_key),
    start_date_key NOT NULL REFERENCES dim_date(date_key),
    start_time_key NOT NULL REFERENCES dim_time(time_key),
    end_date_key NOT NULL REFERENCES dim_date(date_key),
    end_time_key NOT NULL REFERENCES dim_time(time_key),
    sender_name varchar(150),
    event varchar(150),
    start_at timestamptz,
    end_at timestamptz,
    description text,
    tags text,
    alert_count intger NOT NULL DEFAULT 1,
    CONSTRAINT check_fact_alert_time CHECK (end_at IS NULL OR start_at IS NULL OR end_at >= start_at)
);