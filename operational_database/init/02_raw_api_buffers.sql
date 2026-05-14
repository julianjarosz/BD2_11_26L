CREATE TABLE raw_current_weather (
    raw_current_weather_id  bigserial PRIMARY KEY,
    fetched_at              timestamptz NOT NULL DEFAULT now(),

    observed_at             timestamptz NOT NULL,
    sunrise_at              timestamptz,
    sunset_at               timestamptz,
    temp                    numeric(5, 2) NOT NULL,
    feels_like              numeric(5, 2),
    pressure                integer,
    humidity                smallint,
    dew_point               numeric(5, 2),
    uvi                     numeric(4, 2),
    clouds                  smallint,
    visibility              integer,
    wind_speed              numeric(5, 2),
    wind_deg                smallint,
    wind_gust               numeric(5, 2),
    rain_1h                 numeric(5, 2),
    snow_1h                 numeric(5, 2),

    openweather_weather_id  integer NOT NULL,
    main                    varchar(50) NOT NULL,
    description             varchar(100) NOT NULL,
    icon                    varchar(4),

    city_name               varchar(100),
    country_code            char(2),
    lat                     numeric(8, 5) NOT NULL,
    lon                     numeric(8, 5) NOT NULL,
    timezone                varchar(64),
    timezone_offset         integer,

    CONSTRAINT chk_raw_current_humidity CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_current_clouds CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_current_wind_deg CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_raw_current_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_current_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_current_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE raw_hourly_forecast (
    raw_hourly_forecast_id  bigserial PRIMARY KEY,
    fetched_at              timestamptz NOT NULL DEFAULT now(),

    forecast_for            timestamptz NOT NULL,
    retrieved_at            timestamptz NOT NULL,
    temp                    numeric(5, 2) NOT NULL,
    feels_like              numeric(5, 2),
    pressure                integer,
    humidity                smallint,
    dew_point               numeric(5, 2),
    uvi                     numeric(4, 2),
    clouds                  smallint,
    visibility              integer,
    pop                     numeric(4, 3),
    wind_speed              numeric(5, 2),
    wind_deg                smallint,
    wind_gust               numeric(5, 2),
    rain_1h                 numeric(5, 2),
    snow_1h                 numeric(5, 2),

    openweather_weather_id  integer NOT NULL,
    main                    varchar(50) NOT NULL,
    description             varchar(100) NOT NULL,
    icon                    varchar(4),

    city_name               varchar(100),
    country_code            char(2),
    lat                     numeric(8, 5) NOT NULL,
    lon                     numeric(8, 5) NOT NULL,
    timezone                varchar(64),
    timezone_offset         integer,

    CONSTRAINT chk_raw_hourly_humidity CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_hourly_clouds CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_hourly_wind_deg CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_raw_hourly_pop CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    CONSTRAINT chk_raw_hourly_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_hourly_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_hourly_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE raw_daily_forecast (
    raw_daily_forecast_id   bigserial PRIMARY KEY,
    fetched_at              timestamptz NOT NULL DEFAULT now(),

    forecast_date           date NOT NULL,
    retrieved_at            timestamptz NOT NULL,
    sunrise_at              timestamptz,
    sunset_at               timestamptz,
    moonrise_at             timestamptz,
    moonset_at              timestamptz,
    moonphase               numeric(3, 2),
    temp_day                numeric(5, 2),
    temp_min                numeric(5, 2),
    temp_max                numeric(5, 2),
    temp_night              numeric(5, 2),
    temp_evening            numeric(5, 2),
    temp_morning            numeric(5, 2),
    feels_like_day          numeric(5, 2),
    feels_like_night        numeric(5, 2),
    pressure                integer,
    humidity                smallint,
    dew_point               numeric(5, 2),
    wind_speed              numeric(5, 2),
    wind_deg                smallint,
    wind_gust               numeric(5, 2),
    clouds                  smallint,
    pop                     numeric(4, 3),
    rain                    numeric(6, 2),
    snow                    numeric(6, 2),
    uvi                     numeric(4, 2),

    openweather_weather_id  integer NOT NULL,
    main                    varchar(50) NOT NULL,
    description             varchar(100) NOT NULL,
    icon                    varchar(4),

    city_name               varchar(100),
    country_code            char(2),
    lat                     numeric(8, 5) NOT NULL,
    lon                     numeric(8, 5) NOT NULL,
    timezone                varchar(64),
    timezone_offset         integer,

    CONSTRAINT chk_raw_daily_humidity CHECK (humidity IS NULL OR humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_daily_clouds CHECK (clouds IS NULL OR clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_raw_daily_wind_deg CHECK (wind_deg IS NULL OR wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_raw_daily_pop CHECK (pop IS NULL OR pop BETWEEN 0 AND 1),
    CONSTRAINT chk_raw_daily_moonphase CHECK (moonphase IS NULL OR moonphase BETWEEN 0 AND 1),
    CONSTRAINT chk_raw_daily_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_daily_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_daily_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE raw_minutely_forecast (
    raw_minutely_forecast_id  bigserial PRIMARY KEY,
    fetched_at                timestamptz NOT NULL DEFAULT now(),

    forecast_for              timestamptz NOT NULL,
    retrieved_at              timestamptz NOT NULL,
    precipitation             numeric(5, 2) NOT NULL,

    city_name                 varchar(100),
    country_code              char(2),
    lat                       numeric(8, 5) NOT NULL,
    lon                       numeric(8, 5) NOT NULL,
    timezone                  varchar(64),
    timezone_offset           integer,

    CONSTRAINT chk_raw_minutely_precipitation CHECK (precipitation >= 0),
    CONSTRAINT chk_raw_minutely_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_minutely_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_minutely_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE raw_air_pollution (
    raw_air_pollution_id  bigserial PRIMARY KEY,
    fetched_at            timestamptz NOT NULL DEFAULT now(),

    observed_at           timestamptz NOT NULL,
    aqi                   smallint NOT NULL,
    co                    numeric(8, 2),
    no                    numeric(8, 2),
    no2                   numeric(8, 2),
    o3                    numeric(8, 2),
    so2                   numeric(8, 2),
    pm2_5                 numeric(8, 2),
    pm10                  numeric(8, 2),
    nh3                   numeric(8, 2),

    city_name             varchar(100),
    country_code          char(2),
    lat                   numeric(8, 5) NOT NULL,
    lon                   numeric(8, 5) NOT NULL,
    timezone              varchar(64),
    timezone_offset       integer,

    CONSTRAINT chk_raw_air_aqi CHECK (aqi BETWEEN 1 AND 5),
    CONSTRAINT chk_raw_air_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_air_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_air_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);

CREATE TABLE raw_weather_alert (
    raw_weather_alert_id  bigserial PRIMARY KEY,
    fetched_at            timestamptz NOT NULL DEFAULT now(),

    sender_name           varchar(150),
    event                 varchar(150) NOT NULL,
    start_at              timestamptz NOT NULL,
    end_at                timestamptz NOT NULL,
    description_1         text,
    tags                  text,

    city_name             varchar(100),
    country_code          char(2),
    lat                   numeric(8, 5) NOT NULL,
    lon                   numeric(8, 5) NOT NULL,
    timezone              varchar(64),
    timezone_offset       integer,

    CONSTRAINT chk_raw_alert_time_order CHECK (end_at >= start_at),
    CONSTRAINT chk_raw_alert_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT chk_raw_alert_lon CHECK (lon BETWEEN -180 AND 180),
    CONSTRAINT chk_raw_alert_country_code CHECK (country_code IS NULL OR length(country_code) = 2)
);
