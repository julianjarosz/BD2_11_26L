-- Migrate older operational volumes that used condition_id surrogate keys in
-- weather fact tables. The current model stores OpenWeather condition ids
-- directly as openweather_weather_id so operational SELECT * matches stg.*.

ALTER TABLE weather_condition
    ALTER COLUMN openweather_weather_id TYPE bigint;

ALTER TABLE current_weather
    ADD COLUMN IF NOT EXISTS openweather_weather_id bigint;

ALTER TABLE hourly_forecast
    ADD COLUMN IF NOT EXISTS openweather_weather_id bigint;

ALTER TABLE daily_forecast
    ADD COLUMN IF NOT EXISTS openweather_weather_id bigint;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'current_weather'
          AND column_name = 'condition_id'
    ) THEN
        UPDATE current_weather cw
        SET openweather_weather_id = wc.openweather_weather_id
        FROM weather_condition wc
        WHERE cw.openweather_weather_id IS NULL
          AND cw.condition_id = wc.condition_id;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'hourly_forecast'
          AND column_name = 'condition_id'
    ) THEN
        UPDATE hourly_forecast hf
        SET openweather_weather_id = wc.openweather_weather_id
        FROM weather_condition wc
        WHERE hf.openweather_weather_id IS NULL
          AND hf.condition_id = wc.condition_id;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'daily_forecast'
          AND column_name = 'condition_id'
    ) THEN
        UPDATE daily_forecast df
        SET openweather_weather_id = wc.openweather_weather_id
        FROM weather_condition wc
        WHERE df.openweather_weather_id IS NULL
          AND df.condition_id = wc.condition_id;
    END IF;
END $$;

ALTER TABLE current_weather
    DROP CONSTRAINT IF EXISTS current_weather_condition_id_fkey;

ALTER TABLE hourly_forecast
    DROP CONSTRAINT IF EXISTS hourly_forecast_condition_id_fkey;

ALTER TABLE daily_forecast
    DROP CONSTRAINT IF EXISTS daily_forecast_condition_id_fkey;

ALTER TABLE current_weather
    DROP COLUMN IF EXISTS condition_id;

ALTER TABLE hourly_forecast
    DROP COLUMN IF EXISTS condition_id;

ALTER TABLE daily_forecast
    DROP COLUMN IF EXISTS condition_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_attribute a
          ON a.attrelid = c.conrelid
         AND a.attnum = ANY(c.conkey)
        WHERE c.conrelid = 'weather_condition'::regclass
          AND c.contype = 'p'
          AND a.attname = 'condition_id'
    ) THEN
        ALTER TABLE weather_condition DROP CONSTRAINT weather_condition_pkey;
    END IF;
END $$;

ALTER TABLE weather_condition
    ALTER COLUMN openweather_weather_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'weather_condition'::regclass
          AND contype = 'p'
    ) THEN
        ALTER TABLE weather_condition
            ADD CONSTRAINT weather_condition_pkey PRIMARY KEY (openweather_weather_id);
    END IF;
END $$;

ALTER TABLE weather_condition
    DROP COLUMN IF EXISTS condition_id;

ALTER TABLE current_weather
    ALTER COLUMN openweather_weather_id SET NOT NULL;

ALTER TABLE hourly_forecast
    ALTER COLUMN openweather_weather_id SET NOT NULL;

ALTER TABLE daily_forecast
    ALTER COLUMN openweather_weather_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'current_weather'::regclass
          AND conname = 'current_weather_openweather_weather_id_fkey'
    ) THEN
        ALTER TABLE current_weather
            ADD CONSTRAINT current_weather_openweather_weather_id_fkey
            FOREIGN KEY (openweather_weather_id)
            REFERENCES weather_condition(openweather_weather_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'hourly_forecast'::regclass
          AND conname = 'hourly_forecast_openweather_weather_id_fkey'
    ) THEN
        ALTER TABLE hourly_forecast
            ADD CONSTRAINT hourly_forecast_openweather_weather_id_fkey
            FOREIGN KEY (openweather_weather_id)
            REFERENCES weather_condition(openweather_weather_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'daily_forecast'::regclass
          AND conname = 'daily_forecast_openweather_weather_id_fkey'
    ) THEN
        ALTER TABLE daily_forecast
            ADD CONSTRAINT daily_forecast_openweather_weather_id_fkey
            FOREIGN KEY (openweather_weather_id)
            REFERENCES weather_condition(openweather_weather_id);
    END IF;
END $$;
