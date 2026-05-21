CREATE TABLE IF NOT EXISTS location (
    location_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_name        varchar(100),
    country_code     char(2),
    lat              numeric(8,5) NOT NULL,
    lon              numeric(8,5) NOT NULL,
    timezone         varchar(64),
    timezone_offset  integer,

    CONSTRAINT chk_location_lat
        CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_location_lon
        CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_location_country_code
        CHECK (country_code IS NULL OR length(country_code) = 2),
    CONSTRAINT uq_location_lat_lon
        UNIQUE (lat, lon)
);

CREATE TABLE IF NOT EXISTS weather_condition (
    openweather_weather_id   bigint PRIMARY KEY,
    main                     varchar(50) NOT NULL,
    description              varchar(100) NOT NULL,
    icon                     varchar(4)
);

CREATE TABLE IF NOT EXISTS current_weather (
    current_weather_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    openweather_weather_id   bigint NOT NULL REFERENCES weather_condition(openweather_weather_id),
    observed_at              timestamptz NOT NULL,
    sunrise_at               timestamptz,
    sunset_at                timestamptz,
    temp                     numeric(5,2) NOT NULL,
    feels_like               numeric(5,2),
    pressure                 integer,
    humidity                 smallint,
    dew_point                numeric(5,2),
    uvi                      numeric(4,2),
    clouds                   smallint,
    visibility               integer,
    wind_speed               numeric(5,2),
    wind_deg                 smallint,
    wind_gust                numeric(5,2),
    rain_1h                  numeric(5,2),
    snow_1h                  numeric(5,2),

    CONSTRAINT chk_current_humidity
        CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_current_clouds
        CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_current_wind_deg
        CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_current_nonnegative
        CHECK (
            (visibility IS NULL OR visibility >= 0) AND
            (wind_speed IS NULL OR wind_speed >= 0) AND
            (wind_gust IS NULL OR wind_gust >= 0) AND
            (rain_1h IS NULL OR rain_1h >= 0) AND
            (snow_1h IS NULL OR snow_1h >= 0) AND
            (uvi IS NULL OR uvi >= 0)
        ),
    CONSTRAINT uq_current_location_time
        UNIQUE (location_id, observed_at)
);

CREATE TABLE IF NOT EXISTS hourly_forecast (
    hourly_forecast_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    openweather_weather_id   bigint NOT NULL REFERENCES weather_condition(openweather_weather_id),
    forecast_for             timestamptz NOT NULL,
    retrieved_at             timestamptz NOT NULL,
    temp                     numeric(5,2) NOT NULL,
    feels_like               numeric(5,2),
    pressure                 integer,
    humidity                 smallint,
    dew_point                numeric(5,2),
    uvi                      numeric(4,2),
    clouds                   smallint,
    visibility               integer,
    pop                      numeric(4,3),
    wind_speed               numeric(5,2),
    wind_deg                 smallint,
    wind_gust                numeric(5,2),
    rain_1h                  numeric(5,2),
    snow_1h                  numeric(5,2),

    CONSTRAINT chk_hourly_humidity
        CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_hourly_clouds
        CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_hourly_wind_deg
        CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_hourly_pop
        CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    CONSTRAINT chk_hourly_nonnegative
        CHECK (
            (visibility IS NULL OR visibility >= 0) AND
            (wind_speed IS NULL OR wind_speed >= 0) AND
            (wind_gust IS NULL OR wind_gust >= 0) AND
            (rain_1h IS NULL OR rain_1h >= 0) AND
            (snow_1h IS NULL OR snow_1h >= 0) AND
            (uvi IS NULL OR uvi >= 0)
        ),
    CONSTRAINT uq_hourly_location_forecast_retrieved
        UNIQUE (location_id, forecast_for, retrieved_at)
);

CREATE TABLE IF NOT EXISTS daily_forecast (
    daily_forecast_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    openweather_weather_id   bigint NOT NULL REFERENCES weather_condition(openweather_weather_id),
    forecast_date            date NOT NULL,
    retrieved_at             timestamptz NOT NULL,
    sunrise_at               timestamptz,
    sunset_at                timestamptz,
    moonrise_at              timestamptz,
    moonset_at               timestamptz,
    moonphase                numeric(3,2),
    temp_day                 numeric(5,2),
    temp_min                 numeric(5,2),
    temp_max                 numeric(5,2),
    temp_night               numeric(5,2),
    temp_evening             numeric(5,2),
    temp_morning             numeric(5,2),
    feels_like_day           numeric(5,2),
    feels_like_night         numeric(5,2),
    pressure                 integer,
    humidity                 smallint,
    dew_point                numeric(5,2),
    wind_speed               numeric(5,2),
    wind_deg                 smallint,
    wind_gust                numeric(5,2),
    clouds                   smallint,
    pop                      numeric(4,3),
    rain                     numeric(6,2),
    snow                     numeric(6,2),
    uvi                      numeric(4,2),

    CONSTRAINT chk_daily_humidity
        CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_daily_clouds
        CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_daily_wind_deg
        CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_daily_pop
        CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    CONSTRAINT chk_daily_moonphase
        CHECK (moonphase IS NULL OR moonphase BETWEEN 0 AND 1),
    CONSTRAINT chk_daily_nonnegative
        CHECK (
            (wind_speed IS NULL OR wind_speed >= 0) AND
            (wind_gust IS NULL OR wind_gust >= 0) AND
            (rain IS NULL OR rain >= 0) AND
            (snow IS NULL OR snow >= 0) AND
            (uvi IS NULL OR uvi >= 0)
        ),
    CONSTRAINT uq_daily_location_date_retrieved
        UNIQUE (location_id, forecast_date, retrieved_at)
);

CREATE TABLE IF NOT EXISTS minutely_forecast (
    minutely_forecast_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    forecast_for             timestamptz NOT NULL,
    retrieved_at             timestamptz NOT NULL,
    precipitation            numeric(5,2) NOT NULL,

    CONSTRAINT chk_minutely_precipitation
        CHECK (precipitation >= 0),
    CONSTRAINT uq_minutely_location_forecast_retrieved
        UNIQUE (location_id, forecast_for, retrieved_at)
);

CREATE TABLE IF NOT EXISTS air_pollution (
    air_pollution_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    observed_at              timestamptz NOT NULL,
    aqi                      smallint NOT NULL,
    co                       numeric(8,2),
    no                       numeric(8,2),
    no2                      numeric(8,2),
    o3                       numeric(8,2),
    so2                      numeric(8,2),
    pm2_5                    numeric(8,2),
    pm10                     numeric(8,2),
    nh3                      numeric(8,2),

    CONSTRAINT chk_air_aqi
        CHECK (aqi BETWEEN 1 AND 5),
    CONSTRAINT chk_air_components_nonnegative
        CHECK (
            (co IS NULL OR co >= 0) AND
            (no IS NULL OR no >= 0) AND
            (no2 IS NULL OR no2 >= 0) AND
            (o3 IS NULL OR o3 >= 0) AND
            (so2 IS NULL OR so2 >= 0) AND
            (pm2_5 IS NULL OR pm2_5 >= 0) AND
            (pm10 IS NULL OR pm10 >= 0) AND
            (nh3 IS NULL OR nh3 >= 0)
        ),
    CONSTRAINT uq_air_location_time
        UNIQUE (location_id, observed_at)
);

CREATE TABLE IF NOT EXISTS weather_alert (
    weather_alert_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id              bigint NOT NULL REFERENCES location(location_id),
    sender_name              varchar(150),
    event                    varchar(150) NOT NULL,
    start_at                 timestamptz NOT NULL,
    end_at                   timestamptz NOT NULL,
    description              text,
    tags                     text,

    CONSTRAINT chk_alert_time_order
        CHECK (end_at >= start_at)
);

WITH source_locations AS (
    SELECT DISTINCT ON (location_lat, location_lon)
        location_city_name,
        location_country_code,
        location_lat,
        location_lon,
        location_timezone,
        location_timezone_offset
    FROM mapped_data_buffer
    ORDER BY location_lat, location_lon, fetched_at DESC, mapped_data_buffer_id DESC
)
INSERT INTO location (
    city_name,
    country_code,
    lat,
    lon,
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
ON CONFLICT (lat, lon) DO UPDATE SET
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
    FROM mapped_data_buffer
    UNION ALL
    SELECT
        daily_openweather_weather_id,
        daily_condition_main,
        daily_condition_description,
        daily_condition_icon,
        fetched_at,
        mapped_data_buffer_id
    FROM mapped_data_buffer
    UNION ALL
    SELECT
        hourly_openweather_weather_id,
        hourly_condition_main,
        hourly_condition_description,
        hourly_condition_icon,
        fetched_at,
        mapped_data_buffer_id
    FROM mapped_data_buffer
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
INSERT INTO weather_condition (
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

WITH source_current_weather AS (
    SELECT DISTINCT ON (loc.location_id, buf.current_observed_at)
        loc.location_id,
        buf.current_openweather_weather_id,
        buf.current_observed_at,
        buf.current_sunrise_at,
        buf.current_sunset_at,
        buf.current_temp,
        buf.current_feels_like,
        buf.current_pressure,
        buf.current_humidity,
        buf.current_dew_point,
        buf.current_uvi,
        buf.current_clouds,
        buf.current_visibility,
        buf.current_wind_speed,
        buf.current_wind_deg,
        buf.current_wind_gust,
        buf.current_rain_1h,
        buf.current_snow_1h
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    ORDER BY loc.location_id, buf.current_observed_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO current_weather (
    location_id,
    openweather_weather_id,
    observed_at,
    sunrise_at,
    sunset_at,
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
    location_id,
    current_openweather_weather_id,
    current_observed_at,
    current_sunrise_at,
    current_sunset_at,
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
FROM source_current_weather
ON CONFLICT (location_id, observed_at) DO UPDATE SET
    openweather_weather_id = EXCLUDED.openweather_weather_id,
    sunrise_at = EXCLUDED.sunrise_at,
    sunset_at = EXCLUDED.sunset_at,
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

WITH source_daily_forecast AS (
    SELECT DISTINCT ON (loc.location_id, buf.daily_forecast_date, buf.daily_retrieved_at)
        loc.location_id,
        buf.daily_openweather_weather_id,
        buf.daily_forecast_date,
        buf.daily_retrieved_at,
        buf.daily_sunrise_at,
        buf.daily_sunset_at,
        buf.daily_moonrise_at,
        buf.daily_moonset_at,
        buf.daily_moonphase,
        buf.daily_temp_day,
        buf.daily_temp_min,
        buf.daily_temp_max,
        buf.daily_temp_night,
        buf.daily_temp_evening,
        buf.daily_temp_morning,
        buf.daily_feels_like_day,
        buf.daily_feels_like_night,
        buf.daily_pressure,
        buf.daily_humidity,
        buf.daily_dew_point,
        buf.daily_wind_speed,
        buf.daily_wind_deg,
        buf.daily_wind_gust,
        buf.daily_clouds,
        buf.daily_pop,
        buf.daily_rain,
        buf.daily_snow,
        buf.daily_uvi
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    ORDER BY loc.location_id, buf.daily_forecast_date, buf.daily_retrieved_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO daily_forecast (
    location_id,
    openweather_weather_id,
    forecast_date,
    retrieved_at,
    sunrise_at,
    sunset_at,
    moonrise_at,
    moonset_at,
    moonphase,
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
    wind_speed,
    wind_deg,
    wind_gust,
    clouds,
    pop,
    rain,
    snow,
    uvi
)
SELECT
    location_id,
    daily_openweather_weather_id,
    daily_forecast_date,
    daily_retrieved_at,
    daily_sunrise_at,
    daily_sunset_at,
    daily_moonrise_at,
    daily_moonset_at,
    daily_moonphase,
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
    daily_wind_speed,
    daily_wind_deg,
    daily_wind_gust,
    daily_clouds,
    daily_pop,
    daily_rain,
    daily_snow,
    daily_uvi
FROM source_daily_forecast
ON CONFLICT (location_id, forecast_date, retrieved_at) DO UPDATE SET
    openweather_weather_id = EXCLUDED.openweather_weather_id,
    sunrise_at = EXCLUDED.sunrise_at,
    sunset_at = EXCLUDED.sunset_at,
    moonrise_at = EXCLUDED.moonrise_at,
    moonset_at = EXCLUDED.moonset_at,
    moonphase = EXCLUDED.moonphase,
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
    wind_speed = EXCLUDED.wind_speed,
    wind_deg = EXCLUDED.wind_deg,
    wind_gust = EXCLUDED.wind_gust,
    clouds = EXCLUDED.clouds,
    pop = EXCLUDED.pop,
    rain = EXCLUDED.rain,
    snow = EXCLUDED.snow,
    uvi = EXCLUDED.uvi;

WITH source_hourly_forecast AS (
    SELECT DISTINCT ON (loc.location_id, buf.hourly_forecast_for, buf.hourly_retrieved_at)
        loc.location_id,
        buf.hourly_openweather_weather_id,
        buf.hourly_forecast_for,
        buf.hourly_retrieved_at,
        buf.hourly_temp,
        buf.hourly_feels_like,
        buf.hourly_pressure,
        buf.hourly_humidity,
        buf.hourly_dew_point,
        buf.hourly_uvi,
        buf.hourly_clouds,
        buf.hourly_visibility,
        buf.hourly_pop,
        buf.hourly_wind_speed,
        buf.hourly_wind_deg,
        buf.hourly_wind_gust,
        buf.hourly_rain_1h,
        buf.hourly_snow_1h
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    ORDER BY loc.location_id, buf.hourly_forecast_for, buf.hourly_retrieved_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO hourly_forecast (
    location_id,
    openweather_weather_id,
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
    location_id,
    hourly_openweather_weather_id,
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
FROM source_hourly_forecast
ON CONFLICT (location_id, forecast_for, retrieved_at) DO UPDATE SET
    openweather_weather_id = EXCLUDED.openweather_weather_id,
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

WITH source_minutely_forecast AS (
    SELECT DISTINCT ON (loc.location_id, buf.minutely_forecast_for, buf.minutely_retrieved_at)
        loc.location_id,
        buf.minutely_forecast_for,
        buf.minutely_retrieved_at,
        buf.minutely_precipitation
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    ORDER BY loc.location_id, buf.minutely_forecast_for, buf.minutely_retrieved_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO minutely_forecast (
    location_id,
    forecast_for,
    retrieved_at,
    precipitation
)
SELECT
    location_id,
    minutely_forecast_for,
    minutely_retrieved_at,
    minutely_precipitation
FROM source_minutely_forecast
ON CONFLICT (location_id, forecast_for, retrieved_at) DO UPDATE SET
    precipitation = EXCLUDED.precipitation;

WITH source_air_pollution AS (
    SELECT DISTINCT ON (loc.location_id, buf.air_observed_at)
        loc.location_id,
        buf.air_observed_at,
        buf.air_aqi,
        buf.air_co,
        buf.air_no,
        buf.air_no2,
        buf.air_o3,
        buf.air_so2,
        buf.air_pm2_5,
        buf.air_pm10,
        buf.air_nh3
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    ORDER BY loc.location_id, buf.air_observed_at, buf.fetched_at DESC, buf.mapped_data_buffer_id DESC
)
INSERT INTO air_pollution (
    location_id,
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
    location_id,
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
FROM source_air_pollution
ON CONFLICT (location_id, observed_at) DO UPDATE SET
    aqi = EXCLUDED.aqi,
    co = EXCLUDED.co,
    no = EXCLUDED.no,
    no2 = EXCLUDED.no2,
    o3 = EXCLUDED.o3,
    so2 = EXCLUDED.so2,
    pm2_5 = EXCLUDED.pm2_5,
    pm10 = EXCLUDED.pm10,
    nh3 = EXCLUDED.nh3;

WITH source_weather_alert AS (
    SELECT DISTINCT ON (loc.location_id, buf.alert_event, buf.alert_start_at, buf.alert_end_at)
        loc.location_id,
        buf.alert_sender_name,
        buf.alert_event,
        buf.alert_start_at,
        buf.alert_end_at,
        buf.alert_description,
        buf.alert_tags
    FROM mapped_data_buffer buf
    JOIN location loc
        ON loc.lat = buf.location_lat
       AND loc.lon = buf.location_lon
    WHERE buf.alert_event IS NOT NULL
    ORDER BY
        loc.location_id,
        buf.alert_event,
        buf.alert_start_at,
        buf.alert_end_at,
        buf.fetched_at DESC,
        buf.mapped_data_buffer_id DESC
)
INSERT INTO weather_alert (
    location_id,
    sender_name,
    event,
    start_at,
    end_at,
    description,
    tags
)
SELECT
    location_id,
    alert_sender_name,
    alert_event,
    alert_start_at,
    alert_end_at,
    alert_description,
    alert_tags
FROM source_weather_alert src
WHERE NOT EXISTS (
    SELECT 1
    FROM weather_alert existing
    WHERE existing.location_id = src.location_id
      AND existing.event = src.alert_event
      AND existing.start_at = src.alert_start_at
      AND existing.end_at = src.alert_end_at
);
