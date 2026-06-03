WITH source_dates AS (
    SELECT observed_at::date AS full_date FROM stg.current_weather WHERE observed_at IS NOT NULL
    UNION
    SELECT forecast_for::date FROM stg.hourly_forecast WHERE forecast_for IS NOT NULL
    UNION
    SELECT forecast_date FROM stg.daily_forecast WHERE forecast_date IS NOT NULL
    UNION
    SELECT forecast_for::date FROM stg.minutely_forecast WHERE forecast_for IS NOT NULL
    UNION
    SELECT observed_at::date FROM stg.air_pollution WHERE observed_at IS NOT NULL
    UNION
    SELECT start_at::date FROM stg.weather_alert WHERE start_at IS NOT NULL
    UNION
    SELECT end_at::date FROM stg.weather_alert WHERE end_at IS NOT NULL
)
INSERT INTO dw.dim_date (
    date_key, full_date, day, month, month_name, quarter, year,
    day_of_the_week, day_name, is_weekend
)
SELECT
    to_char(full_date, 'YYYYMMDD')::integer,
    full_date,
    extract(day FROM full_date)::integer,
    extract(month FROM full_date)::integer,
    to_char(full_date, 'FMMonth'),
    extract(quarter FROM full_date)::integer,
    extract(year FROM full_date)::integer,
    extract(isodow FROM full_date)::integer,
    to_char(full_date, 'FMDay'),
    extract(isodow FROM full_date)::integer IN (6, 7)
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
    SELECT date_trunc('second', observed_at)::time AS full_time FROM stg.current_weather WHERE observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', forecast_for)::time FROM stg.hourly_forecast WHERE forecast_for IS NOT NULL
    UNION
    SELECT date_trunc('second', forecast_for)::time FROM stg.minutely_forecast WHERE forecast_for IS NOT NULL
    UNION
    SELECT date_trunc('second', observed_at)::time FROM stg.air_pollution WHERE observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', start_at)::time FROM stg.weather_alert WHERE start_at IS NOT NULL
    UNION
    SELECT date_trunc('second', end_at)::time FROM stg.weather_alert WHERE end_at IS NOT NULL
)
INSERT INTO dw.dim_time (
    time_key, full_time, hour, minute, second, part_of_the_day
)
SELECT
    extract(hour FROM full_time)::integer * 10000
        + extract(minute FROM full_time)::integer * 100
        + floor(extract(second FROM full_time))::integer,
    full_time,
    extract(hour FROM full_time)::integer,
    extract(minute FROM full_time)::integer,
    floor(extract(second FROM full_time))::integer,
    CASE
        WHEN extract(hour FROM full_time)::integer BETWEEN 5 AND 11 THEN 'morning'
        WHEN extract(hour FROM full_time)::integer BETWEEN 12 AND 16 THEN 'afternoon'
        WHEN extract(hour FROM full_time)::integer BETWEEN 17 AND 20 THEN 'evening'
        ELSE 'night'
    END
FROM source_times
ON CONFLICT (time_key) DO UPDATE SET
    full_time = EXCLUDED.full_time,
    hour = EXCLUDED.hour,
    minute = EXCLUDED.minute,
    second = EXCLUDED.second,
    part_of_the_day = EXCLUDED.part_of_the_day;

INSERT INTO dw.dim_location (
    city_name, country_code, latitude, longitude, timezone, timezone_offset
)
SELECT city_name, country_code, lat, lon, timezone, timezone_offset
FROM stg.location
WHERE lat IS NOT NULL
  AND lon IS NOT NULL
ON CONFLICT (latitude, longitude) DO UPDATE SET
    city_name = EXCLUDED.city_name,
    country_code = EXCLUDED.country_code,
    timezone = EXCLUDED.timezone,
    timezone_offset = EXCLUDED.timezone_offset;

INSERT INTO dw.dim_weather_condition (
    openweather_weather_id, main, description, icon
)
SELECT openweather_weather_id, main, description, icon
FROM stg.weather_condition
WHERE openweather_weather_id IS NOT NULL
ON CONFLICT (openweather_weather_id) DO UPDATE SET
    main = EXCLUDED.main,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon;

INSERT INTO dw.fact_current_weather (
    source_buffer_id, location_key, observed_date_key, observed_time_key,
    weather_condition_key, observed_at, temp, feels_like, pressure, humidity,
    dew_point, uvi, clouds, visibility, wind_speed, wind_deg, wind_gust,
    rain_1h, snow_1h
)
SELECT
    cw.current_weather_id,
    dl.location_key,
    to_char(cw.observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM cw.observed_at)::integer * 10000
        + extract(minute FROM cw.observed_at)::integer * 100
        + floor(extract(second FROM cw.observed_at))::integer,
    dwc.weather_condition_key,
    cw.observed_at,
    cw.temp,
    cw.feels_like,
    cw.pressure,
    cw.humidity,
    cw.dew_point,
    cw.uvi,
    cw.clouds,
    cw.visibility,
    cw.wind_speed,
    cw.wind_deg,
    cw.wind_gust,
    cw.rain_1h,
    cw.snow_1h
FROM stg.current_weather cw
JOIN stg.location loc ON loc.location_id = cw.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
JOIN dw.dim_weather_condition dwc ON dwc.openweather_weather_id = cw.openweather_weather_id
WHERE cw.current_weather_id IS NOT NULL
  AND cw.observed_at IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    observed_date_key = EXCLUDED.observed_date_key,
    observed_time_key = EXCLUDED.observed_time_key,
    weather_condition_key = EXCLUDED.weather_condition_key,
    observed_at = EXCLUDED.observed_at,
    temp = EXCLUDED.temp,
    feels_like = EXCLUDED.feels_like,
    pressure = EXCLUDED.pressure,
    humidity = EXCLUDED.humidity,
    dew_point = EXCLUDED.dew_point,
    uvi = EXCLUDED.uvi,
    clouds = EXCLUDED.clouds,
    visibility = EXCLUDED.visibility,
    wind_speed = EXCLUDED.wind_speed,
    wind_deg = EXCLUDED.wind_deg,
    wind_gust = EXCLUDED.wind_gust,
    rain_1h = EXCLUDED.rain_1h,
    snow_1h = EXCLUDED.snow_1h;

INSERT INTO dw.fact_hourly_forecast (
    source_buffer_id, location_key, forecast_date_key, forecast_time_key,
    weather_condition_key, forecast_for, retrieved_at, temp, feels_like,
    pressure, humidity, dew_point, uvi, clouds, visibility, pop, wind_speed,
    wind_deg, wind_gust, rain_1h, snow_1h
)
SELECT
    hf.hourly_forecast_id,
    dl.location_key,
    to_char(hf.forecast_for::date, 'YYYYMMDD')::integer,
    extract(hour FROM hf.forecast_for)::integer * 10000
        + extract(minute FROM hf.forecast_for)::integer * 100
        + floor(extract(second FROM hf.forecast_for))::integer,
    dwc.weather_condition_key,
    hf.forecast_for,
    hf.retrieved_at,
    hf.temp,
    hf.feels_like,
    hf.pressure,
    hf.humidity,
    hf.dew_point,
    hf.uvi,
    hf.clouds,
    hf.visibility,
    hf.pop,
    hf.wind_speed,
    hf.wind_deg,
    hf.wind_gust,
    hf.rain_1h,
    hf.snow_1h
FROM stg.hourly_forecast hf
JOIN stg.location loc ON loc.location_id = hf.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
JOIN dw.dim_weather_condition dwc ON dwc.openweather_weather_id = hf.openweather_weather_id
WHERE hf.hourly_forecast_id IS NOT NULL
  AND hf.forecast_for IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    forecast_date_key = EXCLUDED.forecast_date_key,
    forecast_time_key = EXCLUDED.forecast_time_key,
    weather_condition_key = EXCLUDED.weather_condition_key,
    forecast_for = EXCLUDED.forecast_for,
    retrieved_at = EXCLUDED.retrieved_at,
    temp = EXCLUDED.temp,
    feels_like = EXCLUDED.feels_like,
    pressure = EXCLUDED.pressure,
    humidity = EXCLUDED.humidity,
    dew_point = EXCLUDED.dew_point,
    uvi = EXCLUDED.uvi,
    clouds = EXCLUDED.clouds,
    visibility = EXCLUDED.visibility,
    pop = EXCLUDED.pop,
    wind_speed = EXCLUDED.wind_speed,
    wind_deg = EXCLUDED.wind_deg,
    wind_gust = EXCLUDED.wind_gust,
    rain_1h = EXCLUDED.rain_1h,
    snow_1h = EXCLUDED.snow_1h;

INSERT INTO dw.fact_daily_forecast (
    source_buffer_id, location_key, forecast_date_key, weather_condition_key,
    forecast_date, retrieved_at, temp_day, temp_min, temp_max, temp_night,
    temp_evening, temp_morning, feels_like_day, feels_like_night, pressure,
    humidity, dew_point, clouds, pop, rain, snow, wind_speed, wind_deg,
    wind_gust, uvi
)
SELECT
    df.daily_forecast_id,
    dl.location_key,
    to_char(df.forecast_date, 'YYYYMMDD')::integer,
    dwc.weather_condition_key,
    df.forecast_date,
    df.retrieved_at,
    df.temp_day,
    df.temp_min,
    df.temp_max,
    df.temp_night,
    df.temp_evening,
    df.temp_morning,
    df.feels_like_day,
    df.feels_like_night,
    df.pressure,
    df.humidity,
    df.dew_point,
    df.clouds,
    df.pop,
    df.rain,
    df.snow,
    df.wind_speed,
    df.wind_deg,
    df.wind_gust,
    df.uvi
FROM stg.daily_forecast df
JOIN stg.location loc ON loc.location_id = df.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
JOIN dw.dim_weather_condition dwc ON dwc.openweather_weather_id = df.openweather_weather_id
WHERE df.daily_forecast_id IS NOT NULL
  AND df.forecast_date IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    forecast_date_key = EXCLUDED.forecast_date_key,
    weather_condition_key = EXCLUDED.weather_condition_key,
    forecast_date = EXCLUDED.forecast_date,
    retrieved_at = EXCLUDED.retrieved_at,
    temp_day = EXCLUDED.temp_day,
    temp_min = EXCLUDED.temp_min,
    temp_max = EXCLUDED.temp_max,
    temp_night = EXCLUDED.temp_night,
    temp_evening = EXCLUDED.temp_evening,
    temp_morning = EXCLUDED.temp_morning,
    feels_like_day = EXCLUDED.feels_like_day,
    feels_like_night = EXCLUDED.feels_like_night,
    pressure = EXCLUDED.pressure,
    humidity = EXCLUDED.humidity,
    dew_point = EXCLUDED.dew_point,
    clouds = EXCLUDED.clouds,
    pop = EXCLUDED.pop,
    rain = EXCLUDED.rain,
    snow = EXCLUDED.snow,
    wind_speed = EXCLUDED.wind_speed,
    wind_deg = EXCLUDED.wind_deg,
    wind_gust = EXCLUDED.wind_gust,
    uvi = EXCLUDED.uvi;

INSERT INTO dw.fact_minutely_forecast (
    source_buffer_id, location_key, forecast_date_key, forecast_time_key,
    forecast_for, retrieved_at, precipitation
)
SELECT
    mf.minutely_forecast_id,
    dl.location_key,
    to_char(mf.forecast_for::date, 'YYYYMMDD')::integer,
    extract(hour FROM mf.forecast_for)::integer * 10000
        + extract(minute FROM mf.forecast_for)::integer * 100
        + floor(extract(second FROM mf.forecast_for))::integer,
    mf.forecast_for,
    mf.retrieved_at,
    mf.precipitation
FROM stg.minutely_forecast mf
JOIN stg.location loc ON loc.location_id = mf.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
WHERE mf.minutely_forecast_id IS NOT NULL
  AND mf.forecast_for IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    forecast_date_key = EXCLUDED.forecast_date_key,
    forecast_time_key = EXCLUDED.forecast_time_key,
    forecast_for = EXCLUDED.forecast_for,
    retrieved_at = EXCLUDED.retrieved_at,
    precipitation = EXCLUDED.precipitation;

INSERT INTO dw.fact_air_pollution (
    source_buffer_id, location_key, observed_date_key, observed_time_key,
    observed_at, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
)
SELECT
    ap.air_pollution_id,
    dl.location_key,
    to_char(ap.observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM ap.observed_at)::integer * 10000
        + extract(minute FROM ap.observed_at)::integer * 100
        + floor(extract(second FROM ap.observed_at))::integer,
    ap.observed_at,
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
JOIN stg.location loc ON loc.location_id = ap.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
WHERE ap.air_pollution_id IS NOT NULL
  AND ap.observed_at IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    observed_date_key = EXCLUDED.observed_date_key,
    observed_time_key = EXCLUDED.observed_time_key,
    observed_at = EXCLUDED.observed_at,
    aqi = EXCLUDED.aqi,
    co = EXCLUDED.co,
    no = EXCLUDED.no,
    no2 = EXCLUDED.no2,
    o3 = EXCLUDED.o3,
    so2 = EXCLUDED.so2,
    pm2_5 = EXCLUDED.pm2_5,
    pm10 = EXCLUDED.pm10,
    nh3 = EXCLUDED.nh3;

INSERT INTO dw.fact_weather_alert (
    source_buffer_id, location_key, start_date_key, start_time_key,
    end_date_key, end_time_key, sender_name, event, start_at, end_at,
    description, tags, alert_count
)
SELECT
    wa.weather_alert_id,
    dl.location_key,
    to_char(wa.start_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM wa.start_at)::integer * 10000
        + extract(minute FROM wa.start_at)::integer * 100
        + floor(extract(second FROM wa.start_at))::integer,
    to_char(wa.end_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM wa.end_at)::integer * 10000
        + extract(minute FROM wa.end_at)::integer * 100
        + floor(extract(second FROM wa.end_at))::integer,
    wa.sender_name,
    wa.event,
    wa.start_at,
    wa.end_at,
    wa.description,
    wa.tags,
    1
FROM stg.weather_alert wa
JOIN stg.location loc ON loc.location_id = wa.location_id
JOIN dw.dim_location dl ON dl.latitude = loc.lat AND dl.longitude = loc.lon
WHERE wa.weather_alert_id IS NOT NULL
  AND wa.event IS NOT NULL
  AND wa.start_at IS NOT NULL
  AND wa.end_at IS NOT NULL
ON CONFLICT (source_buffer_id) DO UPDATE SET
    location_key = EXCLUDED.location_key,
    start_date_key = EXCLUDED.start_date_key,
    start_time_key = EXCLUDED.start_time_key,
    end_date_key = EXCLUDED.end_date_key,
    end_time_key = EXCLUDED.end_time_key,
    sender_name = EXCLUDED.sender_name,
    event = EXCLUDED.event,
    start_at = EXCLUDED.start_at,
    end_at = EXCLUDED.end_at,
    description = EXCLUDED.description,
    tags = EXCLUDED.tags,
    alert_count = EXCLUDED.alert_count;

TRUNCATE TABLE dw.fact_forecast_accuracy RESTART IDENTITY;

WITH matched_forecasts AS (
    SELECT DISTINCT ON (hf.hourly_forecast_fact_key)
        hf.hourly_forecast_fact_key,
        cw.observed_at,
        cw.temp AS actual_temp,
        hf.temp AS forecast_temp,
        cw.location_key
    FROM dw.fact_hourly_forecast hf
    JOIN dw.fact_current_weather cw
        ON cw.location_key = hf.location_key
       AND date_trunc('hour', cw.observed_at) = date_trunc('hour', hf.forecast_for)
    WHERE hf.forecast_for IS NOT NULL
      AND cw.observed_at IS NOT NULL
    ORDER BY
        hf.hourly_forecast_fact_key,
        abs(extract(epoch FROM (cw.observed_at - hf.forecast_for)))
)
INSERT INTO dw.fact_forecast_accuracy (
    location_key, observed_date_key, observed_time_key, forecast_temp,
    actual_temp, temp_error, abs_temp_error
)
SELECT
    location_key,
    to_char(observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM observed_at)::integer * 10000
        + extract(minute FROM observed_at)::integer * 100
        + floor(extract(second FROM observed_at))::integer,
    forecast_temp,
    actual_temp,
    actual_temp - forecast_temp,
    abs(actual_temp - forecast_temp)
FROM matched_forecasts;

WITH loaded_watermarks AS (
    SELECT 'operational.location' AS source_name, max(location_id) AS last_loaded_id FROM stg.location
    UNION ALL
    SELECT 'operational.weather_condition', max(openweather_weather_id) FROM stg.weather_condition
    UNION ALL
    SELECT 'operational.current_weather', max(current_weather_id) FROM stg.current_weather
    UNION ALL
    SELECT 'operational.hourly_forecast', max(hourly_forecast_id) FROM stg.hourly_forecast
    UNION ALL
    SELECT 'operational.daily_forecast', max(daily_forecast_id) FROM stg.daily_forecast
    UNION ALL
    SELECT 'operational.minutely_forecast', max(minutely_forecast_id) FROM stg.minutely_forecast
    UNION ALL
    SELECT 'operational.air_pollution', max(air_pollution_id) FROM stg.air_pollution
    UNION ALL
    SELECT 'operational.weather_alert', max(weather_alert_id) FROM stg.weather_alert
)
INSERT INTO dw.etl_watermark (source_name, last_loaded_id, updated_at)
SELECT source_name, last_loaded_id, now()
FROM loaded_watermarks
WHERE last_loaded_id IS NOT NULL
ON CONFLICT (source_name) DO UPDATE SET
    last_loaded_id = GREATEST(dw.etl_watermark.last_loaded_id, EXCLUDED.last_loaded_id),
    updated_at = now();
