import os
import random
from datetime import datetime, timedelta

import psycopg

DB_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/weather_warehouse"
)


def seed():
    print("Connecting to the data warehouse...")
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dw.dim_location (city_name, latitude, longitude)
                VALUES ('Warsaw', 52.2297, 21.0122)
                ON CONFLICT (latitude, longitude) DO UPDATE SET city_name = EXCLUDED.city_name
                RETURNING location_key;
            """)
            loc_key = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO dw.dim_weather_condition (openweather_weather_id, main, description, icon)
                VALUES (800, 'Clear', 'clear sky', '01d')
                ON CONFLICT (openweather_weather_id) DO UPDATE SET main = EXCLUDED.main
                RETURNING weather_condition_key;
            """)
            cond_key = cur.fetchone()[0]

            # 3. Generate 60 days of historical data
            now = datetime.now()
            start_date = now - timedelta(days=60)

            print("Generating and inserting 60 days of mock data...")
            for i in range(60):
                current_date = start_date + timedelta(days=i)
                date_key = int(current_date.strftime("%Y%m%d"))
                time_key = int(current_date.strftime("%H%M"))

                cur.execute(
                    """
                    INSERT INTO dw.dim_date (
                        date_key, full_date, day, month, month_name, quarter, year,
                        day_of_the_week, day_name, is_weekend
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """,
                    (
                        date_key,
                        current_date.date(),
                        current_date.day,
                        current_date.month,
                        current_date.strftime("%B"),
                        (current_date.month - 1) // 3 + 1,
                        current_date.year,
                        current_date.isoweekday(),
                        current_date.strftime("%A"),
                        current_date.weekday() >= 5,
                    ),
                )

                # Insert dim_time
                if current_date.hour < 6:
                    part = "Night"
                elif current_date.hour < 12:
                    part = "Morning"
                elif current_date.hour < 18:
                    part = "Afternoon"
                else:
                    part = "Evening"

                cur.execute(
                    """
                    INSERT INTO dw.dim_time (
                        time_key, full_time, hour, minute, second, part_of_the_day
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """,
                    (
                        time_key,
                        current_date.time(),
                        current_date.hour,
                        current_date.minute,
                        current_date.second,
                        part,
                    ),
                )

                # Insert fact_air_pollution
                cur.execute(
                    """
                    INSERT INTO dw.fact_air_pollution (
                        location_key, observed_date_key, observed_time_key, observed_at,
                        aqi, co, "no", no2, o3, so2, pm2_5, pm10, nh3
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """,
                    (
                        loc_key,
                        date_key,
                        time_key,
                        current_date,
                        random.randint(1, 5),
                        random.uniform(100, 500),
                        random.uniform(0, 10),
                        random.uniform(5, 50),
                        random.uniform(20, 100),
                        random.uniform(1, 20),
                        random.uniform(5, 80),
                        random.uniform(10, 100),
                        random.uniform(0, 5),
                    ),
                )

                # Insert fact_current_weather
                cur.execute(
                    """
                    INSERT INTO dw.fact_current_weather (
                        location_key, observed_date_key, observed_time_key,
                        weather_condition_key, observed_at,
                        temp, humidity, wind_speed
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                """,
                    (
                        loc_key,
                        date_key,
                        time_key,
                        cond_key,
                        current_date,
                        random.uniform(-5, 30),
                        random.randint(30, 90),
                        random.uniform(0, 15),
                    ),
                )

            conn.commit()
    print("Success! Seeded 60 days of historical data for Warsaw.")


if __name__ == "__main__":
    seed()
