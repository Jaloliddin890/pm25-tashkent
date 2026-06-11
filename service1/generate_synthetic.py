"""
generate_synthetic.py
Generates realistic synthetic PM2.5 + weather data for Tashkent (2022-2024).
Use this when OpenAQ API is unavailable or returns incomplete data.
Saves to data/tashkent_pm25_weather.csv — same format as fetch_data.py output.
"""

import numpy as np
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUT_FILE = os.path.join(DATA_DIR, "tashkent_pm25_weather.csv")

# Random seed for reproducibility
RNG = np.random.default_rng(42)


def make_datetime_index() -> pd.DatetimeIndex:
    return pd.date_range(
        start="2022-01-01 00:00:00",
        end="2024-12-31 23:00:00",
        freq="h",
        tz="UTC",
    )


def seasonal_pm25(index: pd.DatetimeIndex) -> np.ndarray:
    """
    Tashkent PM2.5 pattern:
    - Winter (Dec-Feb): high pollution (heating + inversion) ~80-150 µg/m³
    - Spring (Mar-May): moderate ~30-60 µg/m³
    - Summer (Jun-Aug): low ~15-35 µg/m³ (wind disperses)
    - Autumn (Sep-Nov): rising ~40-80 µg/m³
    """
    n = len(index)
    hour  = index.hour.values
    month = index.month.values

    # Seasonal base level
    seasonal_base = np.where(month.isin([12, 1, 2])  if hasattr(month, 'isin')
                             else np.isin(month, [12, 1, 2]),  90,
                    np.where(np.isin(month, [3, 4, 5]),        45,
                    np.where(np.isin(month, [6, 7, 8]),        22,
                                                               60)))

    # Diurnal cycle: peaks at morning rush (8-10h) and evening (19-21h)
    diurnal = (
        15 * np.sin(2 * np.pi * (hour - 8) / 24) +
         8 * np.sin(4 * np.pi * (hour - 6) / 24)
    )

    # Smooth random noise (autocorrelated)
    noise = np.zeros(n)
    noise[0] = RNG.normal(0, 5)
    for i in range(1, n):
        noise[i] = 0.92 * noise[i - 1] + RNG.normal(0, 4)

    pm25 = seasonal_base + diurnal + noise
    pm25 = np.clip(pm25, 2.0, 480.0)   # physical bounds
    return pm25.astype(float)


def synthetic_weather(index: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(index)
    month = index.month.values
    hour  = index.hour.values

    # Temperature: hot summers, cold winters (Tashkent continental climate)
    temp_seasonal = (
        -2  * np.cos(2 * np.pi * (month - 1) / 12) * 18 +
        14  # mean annual temp ~14°C
    )
    temp_diurnal = 8 * np.sin(2 * np.pi * (hour - 6) / 24)
    temp_noise   = RNG.normal(0, 1.5, n)
    temperature  = temp_seasonal + temp_diurnal + temp_noise

    # Humidity: lower in summer, higher in winter
    humidity_base = 65 - 20 * np.sin(2 * np.pi * (month - 3) / 12)
    humidity = np.clip(humidity_base + RNG.normal(0, 8, n), 10, 99)

    # Wind speed (m/s) — Tashkent gets moderate winds
    wind_speed = np.abs(RNG.weibull(2.0, n) * 4 + 0.5)

    # Wind direction (degrees, uniform)
    wind_direction = RNG.uniform(0, 360, n)

    # Surface pressure (hPa) ~1000-1020
    pressure = 1013 + RNG.normal(0, 5, n)

    # Precipitation — mostly in spring/winter
    precip_prob = np.where(np.isin(month, [1, 2, 3, 4, 11, 12]), 0.08, 0.02)
    precipitation = np.where(
        RNG.random(n) < precip_prob,
        RNG.exponential(2.0, n),
        0.0,
    )

    # Boundary layer height (m) — low in winter/night, high in summer/day
    blh_base = 800 + 600 * np.sin(2 * np.pi * (month - 3) / 12)
    blh_diurnal = 400 * np.maximum(0, np.sin(2 * np.pi * (hour - 6) / 24))
    boundary_layer_height = np.clip(blh_base + blh_diurnal + RNG.normal(0, 100, n),
                                    50, 3000)

    return pd.DataFrame({
        "temperature_2m":        temperature,
        "relative_humidity_2m":  humidity,
        "wind_speed_10m":        wind_speed,
        "wind_direction_10m":    wind_direction,
        "surface_pressure":      pressure,
        "precipitation":         precipitation,
        "boundary_layer_height": boundary_layer_height,
    })


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("[Synthetic] Generating data for 2022-2024 …")

    index = make_datetime_index()
    pm25  = seasonal_pm25(index)
    weather = synthetic_weather(index)

    df = pd.DataFrame({"datetime": index, "pm25": pm25})
    df = pd.concat([df.reset_index(drop=True), weather.reset_index(drop=True)], axis=1)

    df.to_csv(OUT_FILE, index=False)
    print(f"[Synthetic] Saved {len(df)} rows -> {OUT_FILE}")
    print(f"  PM2.5  — mean: {pm25.mean():.1f}, min: {pm25.min():.1f}, max: {pm25.max():.1f}")


if __name__ == "__main__":
    main()
