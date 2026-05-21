-- Hurtownia: znormalizowany model docelowy.
-- Cala baza dedykowana modelowi - obiekty trzymamy w schemacie public.

CREATE TABLE location (
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

CREATE TABLE weather_condition (
    openweather_weather_id   bigint PRIMARY KEY,
    main                     varchar(50) NOT NULL,
    description              varchar(100) NOT NULL,
    icon                     varchar(4)
);

CREATE TABLE current_weather (
    current_weather_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

    openweather_weather_id   bigint NOT NULL
        REFERENCES weather_condition(openweather_weather_id),

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

CREATE TABLE hourly_forecast (
    hourly_forecast_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

    openweather_weather_id   bigint NOT NULL
        REFERENCES weather_condition(openweather_weather_id),

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

CREATE TABLE daily_forecast (
    daily_forecast_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

    openweather_weather_id   bigint NOT NULL
        REFERENCES weather_condition(openweather_weather_id),

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

CREATE TABLE minutely_forecast (
    minutely_forecast_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

    forecast_for             timestamptz NOT NULL,
    retrieved_at             timestamptz NOT NULL,
    precipitation            numeric(5,2) NOT NULL,

    CONSTRAINT chk_minutely_precipitation
        CHECK (precipitation >= 0),

    CONSTRAINT uq_minutely_location_forecast_retrieved
        UNIQUE (location_id, forecast_for, retrieved_at)
);

CREATE TABLE air_pollution (
    air_pollution_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

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

CREATE TABLE weather_alert (
    weather_alert_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    location_id              bigint NOT NULL
        REFERENCES location(location_id),

    sender_name              varchar(150),
    event                    varchar(150) NOT NULL,
    start_at                 timestamptz NOT NULL,
    end_at                   timestamptz NOT NULL,
    description              text,
    tags                     text,

    CONSTRAINT chk_alert_time_order
        CHECK (end_at >= start_at)
);