CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key integer PRIMARY KEY,
    full_date date NOT NULL UNIQUE,
    day integer NOT NULL CHECK (day BETWEEN 1 AND 31),
    month integer NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name varchar(20) NOT NULL,
    quarter integer NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    year integer NOT NULL,
    day_of_the_week integer NOT NULL CHECK (day_of_the_week BETWEEN 1 AND 7),
    day_name varchar(20) NOT NULL,
    is_weekend boolean NOT NULL
);

CREATE TABLE IF NOT EXISTS dw.dim_time (
    time_key integer PRIMARY KEY,
    full_time time NOT NULL UNIQUE,
    hour integer NOT NULL CHECK (hour BETWEEN 0 AND 23),
    minute integer NOT NULL CHECK (minute BETWEEN 0 AND 59),
    second integer NOT NULL CHECK (second BETWEEN 0 AND 59),
    part_of_the_day varchar(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS dw.dim_location (
    location_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_name varchar(100),
    country_code char(2),
    latitude numeric(10, 6) NOT NULL,
    longitude numeric(10, 6) NOT NULL,
    timezone varchar(64),
    timezone_offset integer,
    CONSTRAINT uq_dim_location_lat_lon UNIQUE (latitude, longitude),
    CONSTRAINT chk_dim_location_lat CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_dim_location_lon CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT chk_dim_location_country_code
        CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE IF NOT EXISTS dw.dim_weather_condition (
    weather_condition_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    openweather_weather_id bigint NOT NULL UNIQUE,
    main varchar(50),
    description varchar(100),
    icon varchar(4)
);

CREATE TABLE IF NOT EXISTS dw.fact_current_weather (
    current_weather_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    observed_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    observed_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    weather_condition_key bigint NOT NULL REFERENCES dw.dim_weather_condition(weather_condition_key),
    observed_at timestamptz NOT NULL,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    dew_point numeric(5, 2),
    uvi numeric(4, 2),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    visibility integer,
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    wind_gust numeric(5, 2),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2),
    CONSTRAINT uq_fact_current_location_time UNIQUE (location_key, observed_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_hourly_forecast (
    hourly_forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    forecast_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    forecast_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    weather_condition_key bigint NOT NULL REFERENCES dw.dim_weather_condition(weather_condition_key),
    forecast_for timestamptz NOT NULL,
    retrieved_at timestamptz,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    dew_point numeric(5, 2),
    uvi numeric(4, 2),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    visibility integer,
    pop numeric(4, 3) CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    wind_gust numeric(5, 2),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2),
    CONSTRAINT uq_fact_hourly_location_forecast_retrieved
        UNIQUE (location_key, forecast_for, retrieved_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_daily_forecast (
    daily_forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    forecast_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    weather_condition_key bigint NOT NULL REFERENCES dw.dim_weather_condition(weather_condition_key),
    forecast_date date NOT NULL,
    retrieved_at timestamptz,
    temp_day numeric(5, 2),
    temp_min numeric(5, 2),
    temp_max numeric(5, 2),
    temp_night numeric(5, 2),
    temp_evening numeric(5, 2),
    temp_morning numeric(5, 2),
    feels_like_day numeric(5, 2),
    feels_like_night numeric(5, 2),
    pressure integer,
    humidity integer CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    dew_point numeric(5, 2),
    clouds integer CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    pop numeric(4, 3) CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    rain numeric(6, 2),
    snow numeric(6, 2),
    wind_speed numeric(5, 2),
    wind_deg integer CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    wind_gust numeric(5, 2),
    uvi numeric(4, 2),
    CONSTRAINT uq_fact_daily_location_date_retrieved
        UNIQUE (location_key, forecast_date, retrieved_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_minutely_forecast (
    minutely_forecast_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    forecast_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    forecast_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    forecast_for timestamptz NOT NULL,
    retrieved_at timestamptz,
    precipitation numeric(5, 2),
    CONSTRAINT chk_fact_minutely_precipitation
        CHECK (precipitation IS NULL OR precipitation >= 0),
    CONSTRAINT uq_fact_minutely_location_forecast_retrieved
        UNIQUE (location_key, forecast_for, retrieved_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_air_pollution (
    air_pollution_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    observed_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    observed_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    observed_at timestamptz NOT NULL,
    aqi integer CHECK (aqi IS NULL OR aqi BETWEEN 1 AND 5),
    co numeric(8, 2),
    no numeric(8, 2),
    no2 numeric(8, 2),
    o3 numeric(8, 2),
    so2 numeric(8, 2),
    pm2_5 numeric(8, 2),
    pm10 numeric(8, 2),
    nh3 numeric(8, 2),
    CONSTRAINT uq_fact_air_location_time UNIQUE (location_key, observed_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_weather_alert (
    weather_alert_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_buffer_id bigint UNIQUE,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    start_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    start_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    end_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    end_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    sender_name varchar(150),
    event varchar(150) NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    description text,
    tags text,
    alert_count integer NOT NULL DEFAULT 1,
    CONSTRAINT chk_fact_alert_time CHECK (end_at >= start_at),
    CONSTRAINT uq_fact_alert_event
        UNIQUE (location_key, sender_name, event, start_at, end_at)
);

CREATE TABLE IF NOT EXISTS dw.fact_forecast_accuracy (
    forecast_accuracy_fact_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_key bigint NOT NULL REFERENCES dw.dim_location(location_key),
    observed_date_key integer NOT NULL REFERENCES dw.dim_date(date_key),
    observed_time_key integer NOT NULL REFERENCES dw.dim_time(time_key),
    forecast_temp numeric(5, 2),
    actual_temp numeric(5, 2),
    temp_error numeric(6, 2),
    abs_temp_error numeric(6, 2) CHECK (abs_temp_error IS NULL OR abs_temp_error >= 0)
);
