CREATE SCHEMA IF NOT EXISTS stg;

CREATE TABLE IF NOT EXISTS stg.location (
    location_id bigint,
    city_name varchar(100),
    country_code char(2),
    lat numeric(8, 5),
    lon numeric(8, 5),
    timezone varchar(64),
    timezone_offset integer
);

CREATE TABLE IF NOT EXISTS stg.weather_condition (
    openweather_weather_id bigint,
    main varchar(50),
    description varchar(100),
    icon varchar(4)
);

CREATE TABLE IF NOT EXISTS stg.current_weather (
    current_weather_id bigint,
    location_id bigint,
    openweather_weather_id bigint,
    observed_at timestamptz,
    sunrise_at timestamptz,
    sunset_at timestamptz,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity smallint,
    dew_point numeric(5, 2),
    uvi numeric(4, 2),
    clouds smallint,
    visibility integer,
    wind_speed numeric(5, 2),
    wind_deg smallint,
    wind_gust numeric(5, 2),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2)
);

CREATE TABLE IF NOT EXISTS stg.hourly_forecast (
    hourly_forecast_id bigint,
    location_id bigint,
    openweather_weather_id bigint,
    forecast_for timestamptz,
    retrieved_at timestamptz,
    temp numeric(5, 2),
    feels_like numeric(5, 2),
    pressure integer,
    humidity smallint,
    dew_point numeric(5, 2),
    uvi numeric(4, 2),
    clouds smallint,
    visibility integer,
    pop numeric(4, 3),
    wind_speed numeric(5, 2),
    wind_deg smallint,
    wind_gust numeric(5, 2),
    rain_1h numeric(5, 2),
    snow_1h numeric(5, 2)
);

CREATE TABLE IF NOT EXISTS stg.daily_forecast (
    daily_forecast_id bigint,
    location_id bigint,
    openweather_weather_id bigint,
    forecast_date date,
    retrieved_at timestamptz,
    sunrise_at timestamptz,
    sunset_at timestamptz,
    moonrise_at timestamptz,
    moonset_at timestamptz,
    moonphase numeric(3, 2),
    temp_day numeric(5, 2),
    temp_min numeric(5, 2),
    temp_max numeric(5, 2),
    temp_night numeric(5, 2),
    temp_evening numeric(5, 2),
    temp_morning numeric(5, 2),
    feels_like_day numeric(5, 2),
    feels_like_night numeric(5, 2),
    pressure integer,
    humidity smallint,
    dew_point numeric(5, 2),
    wind_speed numeric(5, 2),
    wind_deg smallint,
    wind_gust numeric(5, 2),
    clouds smallint,
    pop numeric(4, 3),
    rain numeric(6, 2),
    snow numeric(6, 2),
    uvi numeric(4, 2)
);

CREATE TABLE IF NOT EXISTS stg.minutely_forecast (
    minutely_forecast_id bigint,
    location_id bigint,
    forecast_for timestamptz,
    retrieved_at timestamptz,
    precipitation numeric(5, 2)
);

CREATE TABLE IF NOT EXISTS stg.air_pollution (
    air_pollution_id bigint,
    location_id bigint,
    observed_at timestamptz,
    aqi smallint,
    co numeric(8, 2),
    no numeric(8, 2),
    no2 numeric(8, 2),
    o3 numeric(8, 2),
    so2 numeric(8, 2),
    pm2_5 numeric(8, 2),
    pm10 numeric(8, 2),
    nh3 numeric(8, 2)
);

CREATE TABLE IF NOT EXISTS stg.weather_alert (
    weather_alert_id bigint,
    location_id bigint,
    sender_name varchar(150),
    event varchar(150),
    start_at timestamptz,
    end_at timestamptz,
    description text,
    tags text
);
