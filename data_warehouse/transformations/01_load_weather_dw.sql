WITH source_dates AS (
    SELECT current_observed_at::date AS full_date
    FROM stg.mapped_data_buffer
    WHERE current_observed_at IS NOT NULL
    UNION
    SELECT hourly_forecast_for::date
    FROM stg.mapped_data_buffer
    WHERE hourly_forecast_for IS NOT NULL
    UNION
    SELECT daily_forecast_date
    FROM stg.mapped_data_buffer
    WHERE daily_forecast_date IS NOT NULL
    UNION
    SELECT minutely_forecast_for::date
    FROM stg.mapped_data_buffer
    WHERE minutely_forecast_for IS NOT NULL
    UNION
    SELECT air_observed_at::date
    FROM stg.mapped_data_buffer
    WHERE air_observed_at IS NOT NULL
    UNION
    SELECT alert_start_at::date
    FROM stg.mapped_data_buffer
    WHERE alert_start_at IS NOT NULL
    UNION
    SELECT alert_end_at::date
    FROM stg.mapped_data_buffer
    WHERE alert_end_at IS NOT NULL
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
    SELECT date_trunc('second', current_observed_at)::time AS full_time
    FROM stg.mapped_data_buffer
    WHERE current_observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', hourly_forecast_for)::time
    FROM stg.mapped_data_buffer
    WHERE hourly_forecast_for IS NOT NULL
    UNION
    SELECT date_trunc('second', minutely_forecast_for)::time
    FROM stg.mapped_data_buffer
    WHERE minutely_forecast_for IS NOT NULL
    UNION
    SELECT date_trunc('second', air_observed_at)::time
    FROM stg.mapped_data_buffer
    WHERE air_observed_at IS NOT NULL
    UNION
    SELECT date_trunc('second', alert_start_at)::time
    FROM stg.mapped_data_buffer
    WHERE alert_start_at IS NOT NULL
    UNION
    SELECT date_trunc('second', alert_end_at)::time
    FROM stg.mapped_data_buffer
    WHERE alert_end_at IS NOT NULL
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

WITH source_locations AS (
    SELECT DISTINCT ON (location_lat, location_lon)
        location_city_name,
        location_country_code,
        location_lat,
        location_lon,
        location_timezone,
        location_timezone_offset
    FROM stg.mapped_data_buffer
    WHERE location_lat IS NOT NULL
      AND location_lon IS NOT NULL
    ORDER BY location_lat, location_lon, fetched_at DESC, mapped_data_buffer_id DESC
)
INSERT INTO dw.dim_location (
    city_name,
    country_code,
    latitude,
    longitude,
    timezone,
    timezone_offset
)
SELECT
    location_city_name,
    location_country_code,
    location_lat,
    location_lon,
    location_timezone,
    location_timezone_offset
FROM source_locations
ON CONFLICT (latitude, longitude) DO UPDATE SET
    city_name = EXCLUDED.city_name,
    country_code = EXCLUDED.country_code,
    timezone = EXCLUDED.timezone,
    timezone_offset = EXCLUDED.timezone_offset;

WITH source_conditions AS (
    SELECT
        current_openweather_weather_id AS openweather_weather_id,
        current_condition_main AS main,
        current_condition_description AS description,
        current_condition_icon AS icon,
        fetched_at,
        mapped_data_buffer_id
    FROM stg.mapped_data_buffer
    WHERE current_openweather_weather_id IS NOT NULL
    UNION ALL
    SELECT
        daily_openweather_weather_id,
        daily_condition_main,
        daily_condition_description,
        daily_condition_icon,
        fetched_at,
        mapped_data_buffer_id
    FROM stg.mapped_data_buffer
    WHERE daily_openweather_weather_id IS NOT NULL
    UNION ALL
    SELECT
        hourly_openweather_weather_id,
        hourly_condition_main,
        hourly_condition_description,
        hourly_condition_icon,
        fetched_at,
        mapped_data_buffer_id
    FROM stg.mapped_data_buffer
    WHERE hourly_openweather_weather_id IS NOT NULL
),
deduped_conditions AS (
    SELECT DISTINCT ON (openweather_weather_id)
        openweather_weather_id,
        main,
        description,
        icon
    FROM source_conditions
    ORDER BY openweather_weather_id, fetched_at DESC, mapped_data_buffer_id DESC
)
INSERT INTO dw.dim_weather_condition (
    openweather_weather_id,
    main,
    description,
    icon
)
SELECT
    openweather_weather_id,
    main,
    description,
    icon
FROM deduped_conditions
ON CONFLICT (openweather_weather_id) DO UPDATE SET
    main = EXCLUDED.main,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon;

TRUNCATE TABLE
    dw.fact_forecast_accuracy,
    dw.fact_weather_alert,
    dw.fact_air_pollution,
    dw.fact_minutely_forecast,
    dw.fact_daily_forecast,
    dw.fact_hourly_forecast,
    dw.fact_current_weather
RESTART IDENTITY;

WITH source_current AS (
    SELECT DISTINCT ON (loc.location_key, buf.current_observed_at)
        buf.*,
        loc.location_key,
        cond.weather_condition_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    JOIN dw.dim_weather_condition cond
        ON cond.openweather_weather_id = buf.current_openweather_weather_id
    WHERE buf.current_observed_at IS NOT NULL
      AND buf.current_openweather_weather_id IS NOT NULL
    ORDER BY loc.location_key, buf.current_observed_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_current_weather (
    source_buffer_id,
    location_key,
    observed_date_key,
    observed_time_key,
    weather_condition_key,
    observed_at,
    temp,
    feels_like,
    pressure,
    humidity,
    dew_point,
    uvi,
    clouds,
    visibility,
    wind_speed,
    wind_deg,
    wind_gust,
    rain_1h,
    snow_1h
)
SELECT
    mapped_data_buffer_id,
    location_key,
    to_char(current_observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM current_observed_at)::integer * 10000
        + extract(minute FROM current_observed_at)::integer * 100
        + floor(extract(second FROM current_observed_at))::integer,
    weather_condition_key,
    current_observed_at,
    current_temp,
    current_feels_like,
    current_pressure,
    current_humidity,
    current_dew_point,
    current_uvi,
    current_clouds,
    current_visibility,
    current_wind_speed,
    current_wind_deg,
    current_wind_gust,
    current_rain_1h,
    current_snow_1h
FROM source_current;

WITH source_hourly AS (
    SELECT DISTINCT ON (loc.location_key, buf.hourly_forecast_for, buf.hourly_retrieved_at)
        buf.*,
        loc.location_key,
        cond.weather_condition_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    JOIN dw.dim_weather_condition cond
        ON cond.openweather_weather_id = buf.hourly_openweather_weather_id
    WHERE buf.hourly_forecast_for IS NOT NULL
      AND buf.hourly_openweather_weather_id IS NOT NULL
    ORDER BY
        loc.location_key,
        buf.hourly_forecast_for,
        buf.hourly_retrieved_at,
        buf.fetched_at DESC,
        buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_hourly_forecast (
    source_buffer_id,
    location_key,
    forecast_date_key,
    forecast_time_key,
    weather_condition_key,
    forecast_for,
    retrieved_at,
    temp,
    feels_like,
    pressure,
    humidity,
    dew_point,
    uvi,
    clouds,
    visibility,
    pop,
    wind_speed,
    wind_deg,
    wind_gust,
    rain_1h,
    snow_1h
)
SELECT
    mapped_data_buffer_id,
    location_key,
    to_char(hourly_forecast_for::date, 'YYYYMMDD')::integer,
    extract(hour FROM hourly_forecast_for)::integer * 10000
        + extract(minute FROM hourly_forecast_for)::integer * 100
        + floor(extract(second FROM hourly_forecast_for))::integer,
    weather_condition_key,
    hourly_forecast_for,
    hourly_retrieved_at,
    hourly_temp,
    hourly_feels_like,
    hourly_pressure,
    hourly_humidity,
    hourly_dew_point,
    hourly_uvi,
    hourly_clouds,
    hourly_visibility,
    hourly_pop,
    hourly_wind_speed,
    hourly_wind_deg,
    hourly_wind_gust,
    hourly_rain_1h,
    hourly_snow_1h
FROM source_hourly;

WITH source_daily AS (
    SELECT DISTINCT ON (loc.location_key, buf.daily_forecast_date, buf.daily_retrieved_at)
        buf.*,
        loc.location_key,
        cond.weather_condition_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    JOIN dw.dim_weather_condition cond
        ON cond.openweather_weather_id = buf.daily_openweather_weather_id
    WHERE buf.daily_forecast_date IS NOT NULL
      AND buf.daily_openweather_weather_id IS NOT NULL
    ORDER BY
        loc.location_key,
        buf.daily_forecast_date,
        buf.daily_retrieved_at,
        buf.fetched_at DESC,
        buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_daily_forecast (
    source_buffer_id,
    location_key,
    forecast_date_key,
    weather_condition_key,
    forecast_date,
    retrieved_at,
    temp_day,
    temp_min,
    temp_max,
    temp_night,
    temp_evening,
    temp_morning,
    feels_like_day,
    feels_like_night,
    pressure,
    humidity,
    dew_point,
    clouds,
    pop,
    rain,
    snow,
    wind_speed,
    wind_deg,
    wind_gust,
    uvi
)
SELECT
    mapped_data_buffer_id,
    location_key,
    to_char(daily_forecast_date, 'YYYYMMDD')::integer,
    weather_condition_key,
    daily_forecast_date,
    daily_retrieved_at,
    daily_temp_day,
    daily_temp_min,
    daily_temp_max,
    daily_temp_night,
    daily_temp_evening,
    daily_temp_morning,
    daily_feels_like_day,
    daily_feels_like_night,
    daily_pressure,
    daily_humidity,
    daily_dew_point,
    daily_clouds,
    daily_pop,
    daily_rain,
    daily_snow,
    daily_wind_speed,
    daily_wind_deg,
    daily_wind_gust,
    daily_uvi
FROM source_daily;

WITH source_minutely AS (
    SELECT DISTINCT ON (loc.location_key, buf.minutely_forecast_for, buf.minutely_retrieved_at)
        buf.*,
        loc.location_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    WHERE buf.minutely_forecast_for IS NOT NULL
    ORDER BY
        loc.location_key,
        buf.minutely_forecast_for,
        buf.minutely_retrieved_at,
        buf.fetched_at DESC,
        buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_minutely_forecast (
    source_buffer_id,
    location_key,
    forecast_date_key,
    forecast_time_key,
    forecast_for,
    retrieved_at,
    precipitation
)
SELECT
    mapped_data_buffer_id,
    location_key,
    to_char(minutely_forecast_for::date, 'YYYYMMDD')::integer,
    extract(hour FROM minutely_forecast_for)::integer * 10000
        + extract(minute FROM minutely_forecast_for)::integer * 100
        + floor(extract(second FROM minutely_forecast_for))::integer,
    minutely_forecast_for,
    minutely_retrieved_at,
    minutely_precipitation
FROM source_minutely;

WITH source_air AS (
    SELECT DISTINCT ON (loc.location_key, buf.air_observed_at)
        buf.*,
        loc.location_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    WHERE buf.air_observed_at IS NOT NULL
    ORDER BY loc.location_key, buf.air_observed_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_air_pollution (
    source_buffer_id,
    location_key,
    observed_date_key,
    observed_time_key,
    observed_at,
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
    mapped_data_buffer_id,
    location_key,
    to_char(air_observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM air_observed_at)::integer * 10000
        + extract(minute FROM air_observed_at)::integer * 100
        + floor(extract(second FROM air_observed_at))::integer,
    air_observed_at,
    air_aqi,
    air_co,
    air_no,
    air_no2,
    air_o3,
    air_so2,
    air_pm2_5,
    air_pm10,
    air_nh3
FROM source_air;

WITH source_alert AS (
    SELECT DISTINCT ON (
        loc.location_key,
        buf.alert_sender_name,
        buf.alert_event,
        buf.alert_start_at,
        buf.alert_end_at
    )
        buf.*,
        loc.location_key
    FROM stg.mapped_data_buffer buf
    JOIN dw.dim_location loc
        ON loc.latitude = buf.location_lat
       AND loc.longitude = buf.location_lon
    WHERE buf.alert_event IS NOT NULL
      AND buf.alert_start_at IS NOT NULL
      AND buf.alert_end_at IS NOT NULL
      AND buf.alert_end_at >= buf.alert_start_at
    ORDER BY
        loc.location_key,
        buf.alert_sender_name,
        buf.alert_event,
        buf.alert_start_at,
        buf.alert_end_at,
        buf.fetched_at DESC,
        buf.mapped_data_buffer_id DESC
)
INSERT INTO dw.fact_weather_alert (
    source_buffer_id,
    location_key,
    start_date_key,
    start_time_key,
    end_date_key,
    end_time_key,
    sender_name,
    event,
    start_at,
    end_at,
    description,
    tags,
    alert_count
)
SELECT
    mapped_data_buffer_id,
    location_key,
    to_char(alert_start_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM alert_start_at)::integer * 10000
        + extract(minute FROM alert_start_at)::integer * 100
        + floor(extract(second FROM alert_start_at))::integer,
    to_char(alert_end_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM alert_end_at)::integer * 10000
        + extract(minute FROM alert_end_at)::integer * 100
        + floor(extract(second FROM alert_end_at))::integer,
    alert_sender_name,
    alert_event,
    alert_start_at,
    alert_end_at,
    alert_description,
    alert_tags,
    1
FROM source_alert;

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
    to_char(observed_at::date, 'YYYYMMDD')::integer,
    extract(hour FROM observed_at)::integer * 10000
        + extract(minute FROM observed_at)::integer * 100
        + floor(extract(second FROM observed_at))::integer,
    forecast_temp,
    actual_temp,
    actual_temp - forecast_temp,
    abs(actual_temp - forecast_temp)
FROM matched_forecasts;
