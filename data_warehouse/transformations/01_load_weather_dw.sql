WITH source_dates AS (
    SELECT observed_at::date AS full_date
    FROM stg.current_weather
    WHERE observed_at IS NOT NULL
    UNION
    SELECT forecast_for::date
    FROM stg.hourly_forecast
    WHERE forecast_for IS NOT NULL
    UNION
    SELECT forecast_date
    FROM stg.daily_forecast
    WHERE forecast_date IS NOT NULL
    UNION
    SELECT observed_at::date
    FROM stg.air_pollution
    WHERE observed_at IS NOT NULL
    UNION
    SELECT start_at::date
    FROM stg.weather_alert
    WHERE start_at IS NOT NULL
    UNION
    SELECT end_at::date
    FROM stg.weather_alert
    WHERE end_at IS NOT NULL
)
INSERT INTO dw.dim_date (
    date_key,
    full_date,
    day,
    month,
    month_name,
    quarter,
    year,
    day_of_the_week,
    day_name,
    is_weekend
)
SELECT
    to_char(full_date, 'YYYYMMDD')::integer AS date_key,
    full_date,
    extract(day FROM full_date)::integer AS day,
    extract(month FROM full_date)::integer AS month,
    to_char(full_date, 'FMMonth') AS month_name,
    extract(quarter FROM full_date)::integer AS quarter,
    extract(year FROM full_date)::integer AS year,
    extract(isodow FROM full_date)::integer AS day_of_the_week,
    to_char(full_date, 'FMDay') AS day_name,
    extract(isodow FROM full_date)::integer IN (6, 7) AS is_weekend
FROM source_dates
ON CONFLICT (date_key) DO UPDATE SET
    full_date = EXCLUDED.full_date,
    day = EXCLUDED.day,
    month = EXCLUDED.month,
    month_name = EXCLUDED.month_name,
    quarter = EXCLUDED.quarter,
    year = EXCLUDED.year,
    day_of_the_week = EXCLUDED.day_of_the_week,
    day_name = EXCLUDED.day_name,
    is_weekend = EXCLUDED.is_weekend;

WITH source_times AS (
    SELECT date_trunc('second', observed_at)::time AS full_time
    FROM stg.current_weather
    WHERE observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', forecast_for)::time
    FROM stg.hourly_forecast
    WHERE forecast_for IS NOT NULL
    UNION
    SELECT date_trunc('second', observed_at)::time
    FROM stg.air_pollution
    WHERE observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', start_at)::time
    FROM stg.weather_alert
    WHERE start_at IS NOT NULL
    UNION
    SELECT date_trunc('second', end_at)::time
    FROM stg.weather_alert
    WHERE end_at IS NOT NULL
)
INSERT INTO dw.dim_time (
    time_key,
    full_time,
    hour,
    minute,
    second,
    part_of_the_day
)
SELECT
    extract(hour FROM full_time)::integer * 10000
        + extract(minute FROM full_time)::integer * 100
        + floor(extract(second FROM full_time))::integer AS time_key,
    full_time,
    extract(hour FROM full_time)::integer AS hour,
    extract(minute FROM full_time)::integer AS minute,
    floor(extract(second FROM full_time))::integer AS second,
    CASE
        WHEN extract(hour FROM full_time)::integer BETWEEN 5 AND 11 THEN 'morning'
        WHEN extract(hour FROM full_time)::integer BETWEEN 12 AND 16 THEN 'afternoon'
        WHEN extract(hour FROM full_time)::integer BETWEEN 17 AND 20 THEN 'evening'
        ELSE 'night'
    END AS part_of_the_day
FROM source_times
ON CONFLICT (time_key) DO UPDATE SET
    full_time = EXCLUDED.full_time,
    hour = EXCLUDED.hour,
    minute = EXCLUDED.minute,
    second = EXCLUDED.second,
    part_of_the_day = EXCLUDED.part_of_the_day;

INSERT INTO dw.dim_location (
    location_id_nk,
    city_name,
    country_code,
    latitude,
    longitude,
    timezone,
    timezone_offset
)
SELECT
    location_id AS location_id_nk,
    city_name,
    country_code,
    lat AS latitude,
    lon AS longitude,
    timezone,
    timezone_offset
FROM stg.location
ON CONFLICT (location_id_nk) DO UPDATE SET
    city_name = EXCLUDED.city_name,
    country_code = EXCLUDED.country_code,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    timezone = EXCLUDED.timezone,
    timezone_offset = EXCLUDED.timezone_offset;

INSERT INTO dw.dim_weather_condition (
    condition_id_nk,
    openweather_weather_id,
    main,
    description,
    icon
)
SELECT
    condition_id AS condition_id_nk,
    openweather_weather_id,
    main,
    description,
    icon
FROM stg.weather_condition
ON CONFLICT (condition_id_nk) DO UPDATE SET
    openweather_weather_id = EXCLUDED.openweather_weather_id,
    main = EXCLUDED.main,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon;

TRUNCATE TABLE
    dw.fact_forecast_accuracy,
    dw.fact_weather_alert,
    dw.fact_air_pollution,
    dw.fact_daily_forecast,
    dw.fact_hourly_forecast,
    dw.fact_current_weather
RESTART IDENTITY;

INSERT INTO dw.fact_current_weather (
    location_key,
    observed_date_key,
    observed_time_key,
    weather_condition_key,
    temp,
    feels_like,
    pressure,
    humidity,
    clouds,
    visibility,
    wind_speed,
    wind_deg,
    rain_1h,
    snow_1h
)
SELECT
    dl.location_key,
    to_char(cw.observed_at::date, 'YYYYMMDD')::integer AS observed_date_key,
    extract(hour FROM cw.observed_at)::integer * 10000
        + extract(minute FROM cw.observed_at)::integer * 100
        + floor(extract(second FROM cw.observed_at))::integer AS observed_time_key,
    dwc.weather_condition_key,
    cw.temp,
    cw.feels_like,
    cw.pressure,
    cw.humidity,
    cw.clouds,
    cw.visibility,
    cw.wind_speed,
    cw.wind_deg,
    cw.rain_1h,
    cw.snow_1h
FROM stg.current_weather cw
JOIN dw.dim_location dl
    ON dl.location_id_nk = cw.location_id
JOIN dw.dim_weather_condition dwc
    ON dwc.condition_id_nk = cw.condition_id
WHERE cw.observed_at IS NOT NULL;

INSERT INTO dw.fact_hourly_forecast (
    location_key,
    forecast_date_key,
    forecast_time_key,
    weather_condition_key,
    temp,
    feels_like,
    pressure,
    humidity,
    clouds,
    pop,
    wind_speed,
    wind_deg,
    rain_1h,
    snow_1h
)
SELECT
    dl.location_key,
    to_char(hf.forecast_for::date, 'YYYYMMDD')::integer AS forecast_date_key,
    extract(hour FROM hf.forecast_for)::integer * 10000
        + extract(minute FROM hf.forecast_for)::integer * 100
        + floor(extract(second FROM hf.forecast_for))::integer AS forecast_time_key,
    dwc.weather_condition_key,
    hf.temp,
    hf.feels_like,
    hf.pressure,
    hf.humidity,
    hf.clouds,
    hf.pop,
    hf.wind_speed,
    hf.wind_deg,
    hf.rain_1h,
    hf.snow_1h
FROM stg.hourly_forecast hf
JOIN dw.dim_location dl
    ON dl.location_id_nk = hf.location_id
JOIN dw.dim_weather_condition dwc
    ON dwc.condition_id_nk = hf.condition_id
WHERE hf.forecast_for IS NOT NULL;

INSERT INTO dw.fact_daily_forecast (
    location_key,
    forecast_date_key,
    weather_condition_key,
    temp_day,
    temp_min,
    temp_max,
    pressure,
    humidity,
    clouds,
    pop,
    rain,
    snow,
    wind_speed,
    wind_deg
)
SELECT
    dl.location_key,
    to_char(df.forecast_date, 'YYYYMMDD')::integer AS forecast_date_key,
    dwc.weather_condition_key,
    df.temp_day,
    df.temp_min,
    df.temp_max,
    df.pressure,
    df.humidity,
    df.clouds,
    df.pop,
    df.rain,
    df.snow,
    df.wind_speed,
    df.wind_deg
FROM stg.daily_forecast df
JOIN dw.dim_location dl
    ON dl.location_id_nk = df.location_id
JOIN dw.dim_weather_condition dwc
    ON dwc.condition_id_nk = df.condition_id
WHERE df.forecast_date IS NOT NULL;

INSERT INTO dw.fact_air_pollution (
    location_key,
    observed_date_key,
    observed_time_key,
    aqi,
    co,
    no,
    no2,
    o3,
    so2,
    pm2_5,
    pm10,
    nh3
)
SELECT
    dl.location_key,
    to_char(ap.observed_at::date, 'YYYYMMDD')::integer AS observed_date_key,
    extract(hour FROM ap.observed_at)::integer * 10000
        + extract(minute FROM ap.observed_at)::integer * 100
        + floor(extract(second FROM ap.observed_at))::integer AS observed_time_key,
    ap.aqi,
    ap.co,
    ap.no,
    ap.no2,
    ap.o3,
    ap.so2,
    ap.pm2_5,
    ap.pm10,
    ap.nh3
FROM stg.air_pollution ap
JOIN dw.dim_location dl
    ON dl.location_id_nk = ap.location_id
WHERE ap.observed_at IS NOT NULL;

INSERT INTO dw.fact_weather_alert (
    location_key,
    start_date_key,
    start_time_key,
    end_date_key,
    end_time_key,
    alert_count
)
SELECT
    dl.location_key,
    to_char(wa.start_at::date, 'YYYYMMDD')::integer AS start_date_key,
    extract(hour FROM wa.start_at)::integer * 10000
        + extract(minute FROM wa.start_at)::integer * 100
        + floor(extract(second FROM wa.start_at))::integer AS start_time_key,
    to_char(wa.end_at::date, 'YYYYMMDD')::integer AS end_date_key,
    extract(hour FROM wa.end_at)::integer * 10000
        + extract(minute FROM wa.end_at)::integer * 100
        + floor(extract(second FROM wa.end_at))::integer AS end_time_key,
    1 AS alert_count
FROM stg.weather_alert wa
JOIN dw.dim_location dl
    ON dl.location_id_nk = wa.location_id
WHERE wa.start_at IS NOT NULL
  AND wa.end_at IS NOT NULL
  AND wa.end_at >= wa.start_at;

WITH matched_forecasts AS (
    SELECT DISTINCT ON (hf.hourly_forecast_id)
        hf.hourly_forecast_id,
        cw.observed_at,
        cw.temp AS actual_temp,
        hf.temp AS forecast_temp,
        dl.location_key
    FROM stg.hourly_forecast hf
    JOIN stg.current_weather cw
        ON cw.location_id = hf.location_id
       AND date_trunc('hour', cw.observed_at) = date_trunc('hour', hf.forecast_for)
    JOIN dw.dim_location dl
        ON dl.location_id_nk = hf.location_id
    WHERE hf.forecast_for IS NOT NULL
      AND cw.observed_at IS NOT NULL
    ORDER BY
        hf.hourly_forecast_id,
        abs(extract(epoch FROM (cw.observed_at - hf.forecast_for)))
)
INSERT INTO dw.fact_forecast_accuracy (
    location_key,
    observed_date_key,
    observed_time_key,
    forecast_temp,
    actual_temp,
    temp_error,
    abs_temp_error
)
SELECT
    location_key,
    to_char(observed_at::date, 'YYYYMMDD')::integer AS observed_date_key,
    extract(hour FROM observed_at)::integer * 10000
        + extract(minute FROM observed_at)::integer * 100
        + floor(extract(second FROM observed_at))::integer AS observed_time_key,
    forecast_temp,
    actual_temp,
    actual_temp - forecast_temp AS temp_error,
    abs(actual_temp - forecast_temp) AS abs_temp_error
FROM matched_forecasts;
