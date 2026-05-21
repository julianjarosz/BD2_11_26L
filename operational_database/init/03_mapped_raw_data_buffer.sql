CREATE TABLE mapped_data_buffer (
    mapped_data_buffer_id                    bigserial PRIMARY KEY,
    fetched_at                                timestamptz NOT NULL DEFAULT now(),

    location_city_name                        varchar(100) NOT NULL DEFAULT 'Warsaw',
    location_country_code                     char(2) NOT NULL DEFAULT 'PL',
    location_lat                              numeric(8, 5) NOT NULL DEFAULT 52.22970,
    location_lon                              numeric(8, 5) NOT NULL DEFAULT 21.01220,
    location_timezone                         varchar(64),
    location_timezone_offset                  integer,

    current_observed_at                       timestamptz NOT NULL,
    current_sunrise_at                        timestamptz,
    current_sunset_at                         timestamptz,
    current_temp                              numeric(5, 2) NOT NULL,
    current_feels_like                        numeric(5, 2),
    current_pressure                          integer,
    current_humidity                          smallint,
    current_dew_point                         numeric(5, 2),
    current_uvi                               numeric(4, 2),
    current_clouds                            smallint,
    current_visibility                        integer,
    current_wind_speed                        numeric(5, 2),
    current_wind_deg                          smallint,
    current_wind_gust                         numeric(5, 2),
    current_rain_1h                           numeric(5, 2),
    current_snow_1h                           numeric(5, 2),
    current_openweather_weather_id            bigint NOT NULL,
    current_condition_main                    varchar(50) NOT NULL,
    current_condition_description             varchar(100) NOT NULL,
    current_condition_icon                    varchar(4),

    daily_forecast_date                       date NOT NULL,
    daily_retrieved_at                        timestamptz NOT NULL,
    daily_sunrise_at                          timestamptz,
    daily_sunset_at                           timestamptz,
    daily_moonrise_at                         timestamptz,
    daily_moonset_at                          timestamptz,
    daily_moonphase                           numeric(3, 2),
    daily_temp_day                            numeric(5, 2),
    daily_temp_min                            numeric(5, 2),
    daily_temp_max                            numeric(5, 2),
    daily_temp_night                          numeric(5, 2),
    daily_temp_evening                        numeric(5, 2),
    daily_temp_morning                        numeric(5, 2),
    daily_feels_like_day                      numeric(5, 2),
    daily_feels_like_night                    numeric(5, 2),
    daily_pressure                            integer,
    daily_humidity                            smallint,
    daily_dew_point                           numeric(5, 2),
    daily_wind_speed                          numeric(5, 2),
    daily_wind_deg                            smallint,
    daily_wind_gust                           numeric(5, 2),
    daily_clouds                              smallint,
    daily_pop                                 numeric(4, 3),
    daily_rain                                numeric(6, 2),
    daily_snow                                numeric(6, 2),
    daily_uvi                                 numeric(4, 2),
    daily_openweather_weather_id              bigint NOT NULL,
    daily_condition_main                      varchar(50) NOT NULL,
    daily_condition_description               varchar(100) NOT NULL,
    daily_condition_icon                      varchar(4),

    hourly_forecast_for                       timestamptz NOT NULL,
    hourly_retrieved_at                       timestamptz NOT NULL,
    hourly_temp                               numeric(5, 2) NOT NULL,
    hourly_feels_like                         numeric(5, 2),
    hourly_pressure                           integer,
    hourly_humidity                           smallint,
    hourly_dew_point                          numeric(5, 2),
    hourly_uvi                                numeric(4, 2),
    hourly_clouds                             smallint,
    hourly_visibility                         integer,
    hourly_pop                                numeric(4, 3),
    hourly_wind_speed                         numeric(5, 2),
    hourly_wind_deg                           smallint,
    hourly_wind_gust                          numeric(5, 2),
    hourly_rain_1h                            numeric(5, 2),
    hourly_snow_1h                            numeric(5, 2),
    hourly_openweather_weather_id             bigint NOT NULL,
    hourly_condition_main                     varchar(50) NOT NULL,
    hourly_condition_description              varchar(100) NOT NULL,
    hourly_condition_icon                     varchar(4),

    minutely_forecast_for                     timestamptz NOT NULL,
    minutely_retrieved_at                     timestamptz NOT NULL,
    minutely_precipitation                    numeric(5, 2) NOT NULL,

    air_observed_at                           timestamptz NOT NULL,
    air_aqi                                   smallint NOT NULL,
    air_co                                    numeric(8, 2),
    air_no                                    numeric(8, 2),
    air_no2                                   numeric(8, 2),
    air_o3                                    numeric(8, 2),
    air_so2                                   numeric(8, 2),
    air_pm2_5                                 numeric(8, 2),
    air_pm10                                  numeric(8, 2),
    air_nh3                                   numeric(8, 2),

    alert_sender_name                         varchar(150),
    alert_event                               varchar(150),
    alert_start_at                            timestamptz,
    alert_end_at                              timestamptz,
    alert_description                         text,
    alert_tags                                text,

    CONSTRAINT chk_mapped_data_buffer_location_lat
        CHECK (location_lat BETWEEN -90 AND 90),
    CONSTRAINT chk_mapped_data_buffer_location_lon
        CHECK (location_lon BETWEEN -180 AND 180),
    CONSTRAINT chk_mapped_data_buffer_location_country_code
        CHECK (length(location_country_code) = 2),
    CONSTRAINT chk_mapped_data_buffer_current_humidity
        CHECK (current_humidity IS NULL OR current_humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_current_clouds
        CHECK (current_clouds IS NULL OR current_clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_current_wind_deg
        CHECK (current_wind_deg IS NULL OR current_wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_mapped_data_buffer_daily_humidity
        CHECK (daily_humidity IS NULL OR daily_humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_daily_clouds
        CHECK (daily_clouds IS NULL OR daily_clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_daily_wind_deg
        CHECK (daily_wind_deg IS NULL OR daily_wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_mapped_data_buffer_daily_pop
        CHECK (daily_pop IS NULL OR daily_pop BETWEEN 0 AND 1),
    CONSTRAINT chk_mapped_data_buffer_daily_moonphase
        CHECK (daily_moonphase IS NULL OR daily_moonphase BETWEEN 0 AND 1),
    CONSTRAINT chk_mapped_data_buffer_hourly_humidity
        CHECK (hourly_humidity IS NULL OR hourly_humidity BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_hourly_clouds
        CHECK (hourly_clouds IS NULL OR hourly_clouds BETWEEN 0 AND 100),
    CONSTRAINT chk_mapped_data_buffer_hourly_wind_deg
        CHECK (hourly_wind_deg IS NULL OR hourly_wind_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_mapped_data_buffer_hourly_pop
        CHECK (hourly_pop IS NULL OR hourly_pop BETWEEN 0 AND 1),
    CONSTRAINT chk_mapped_data_buffer_minutely_precipitation
        CHECK (minutely_precipitation >= 0),
    CONSTRAINT chk_mapped_data_buffer_air_aqi
        CHECK (air_aqi BETWEEN 1 AND 5),
    CONSTRAINT chk_mapped_data_buffer_alert_complete
        CHECK (
            alert_event IS NULL
            OR (alert_start_at IS NOT NULL AND alert_end_at IS NOT NULL)
        ),
    CONSTRAINT chk_mapped_data_buffer_alert_time_order
        CHECK (
            alert_start_at IS NULL
            OR alert_end_at IS NULL
            OR alert_end_at >= alert_start_at
        )
);
