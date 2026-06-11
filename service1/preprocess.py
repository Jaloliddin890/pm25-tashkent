"""
preprocess.py
Cleans raw data, engineers features, and splits into train/test sets.

Input : data/tashkent_pm25_weather.csv
Output: data/processed.csv
        data/train.csv
        data/test.csv
        data/feature_cols.json
"""

import json
import os
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_FILE       = os.path.join(DATA_DIR, "tashkent_pm25_weather.csv")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed.csv")
TRAIN_FILE     = os.path.join(DATA_DIR, "train.csv")
TEST_FILE      = os.path.join(DATA_DIR, "test.csv")
FEAT_FILE      = os.path.join(DATA_DIR, "feature_cols.json")

TEST_RATIO = 0.2   # last 20% of data used as test set


# ── Load ──────────────────────────────────────────────────────────────────────

def load_raw() -> pd.DataFrame:
    print(f"[Preprocess] Loading {RAW_FILE} …")
    df = pd.read_csv(RAW_FILE, parse_dates=["datetime"])
    if df["datetime"].dt.tz is None:
        df["datetime"] = df["datetime"].dt.tz_localize("UTC")
    df = df.sort_values("datetime").reset_index(drop=True)

    # Synthetic qatorlarni training dan chiqar (dashboard uchun saqlanadi, model uchun emas)
    if "source" in df.columns:
        n_syn = (df["source"] == "synthetic").sum()
        if n_syn:
            df = df[df["source"] != "synthetic"].reset_index(drop=True)
            print(f"  Filtered {n_syn} synthetic rows (dashboard-only).")

    print(f"  Loaded {len(df)} rows, {df.shape[1]} columns.")
    return df


# ── Clean ─────────────────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:
    print("[Preprocess] Cleaning …")

    # Remove duplicate timestamps
    df = df.drop_duplicates(subset="datetime")

    # source ustunini alohida saqlash (matn, mean qilish mumkin emas)
    source_col = None
    if "source" in df.columns:
        source_col = df.set_index("datetime")["source"]
        df = df.drop(columns=["source"])

    # Resample to hourly UTC (fills any gaps with NaN)
    df = df.set_index("datetime")
    df = df.resample("h").mean()
    df.index.name = "datetime"

    # source ni qayta qo'shish
    if source_col is not None:
        source_col = source_col[~source_col.index.duplicated(keep="first")]
        source_col = source_col.reindex(df.index, fill_value="cams")
        df["source"] = source_col.values

    # boundary_layer_height ko'p hollarda NaN — olib tashlaymiz
    if "boundary_layer_height" in df.columns:
        df = df.drop(columns=["boundary_layer_height"])

    # Remove physical outliers
    # 250 µg/m³ — Toshkentda real holatda soatlik max chegarasi
    df.loc[df["pm25"] < 0,   "pm25"] = np.nan
    df.loc[df["pm25"] > 250, "pm25"] = np.nan

    # Forward-fill gaps up to 3 consecutive hours, then drop remaining NaN rows
    df = df.ffill(limit=3)
    before = len(df)
    df = df.dropna(subset=["pm25"])
    print(f"  Dropped {before - len(df)} rows with unfillable NaN in pm25.")

    df = df.reset_index()
    return df


# ── Feature Engineering ───────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    print("[Preprocess] Engineering features …")

    # Lag features (hours before)
    for lag in [1, 2, 3, 6, 12, 24, 48]:
        df[f"pm25_lag_{lag}h"] = df["pm25"].shift(lag)

    # Rolling mean features
    for window in [3, 6, 24]:
        df[f"pm25_roll_{window}h"] = (
            df["pm25"].shift(1).rolling(window).mean()
        )
    df["pm25_roll_7d"] = df["pm25"].shift(1).rolling(24 * 7).mean()

    # Cyclical time encodings
    df["hour_sin"] = np.sin(2 * np.pi * df["datetime"].dt.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["datetime"].dt.hour / 24)
    df["dow_sin"]  = np.sin(2 * np.pi * df["datetime"].dt.dayofweek / 7)
    df["dow_cos"]  = np.cos(2 * np.pi * df["datetime"].dt.dayofweek / 7)
    df["month_sin"] = np.sin(2 * np.pi * (df["datetime"].dt.month - 1) / 12)
    df["month_cos"] = np.cos(2 * np.pi * (df["datetime"].dt.month - 1) / 12)

    # Wind u/v components (direction -> Cartesian)
    if "wind_direction_10m" in df.columns and "wind_speed_10m" in df.columns:
        wind_rad = np.deg2rad(df["wind_direction_10m"])
        df["wind_u"] = -df["wind_speed_10m"] * np.sin(wind_rad)
        df["wind_v"] = -df["wind_speed_10m"] * np.cos(wind_rad)

    # Drop rows with NaN introduced by lags/rolling
    df = df.dropna().reset_index(drop=True)
    print(f"  {len(df)} rows after feature engineering.")
    return df


# ── Split ─────────────────────────────────────────────────────────────────────

def split_train_test(df: pd.DataFrame):
    split_idx = int(len(df) * (1 - TEST_RATIO))
    train = df.iloc[:split_idx].copy()
    test  = df.iloc[split_idx:].copy()
    print(f"  Train: {len(train)} rows | Test: {len(test)} rows")
    return train, test


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    df = load_raw()
    df = clean(df)
    df = engineer_features(df)

    # Save processed
    df.to_csv(PROCESSED_FILE, index=False)
    print(f"[Preprocess] Saved processed data -> {PROCESSED_FILE}")

    # Save train/test
    train, test = split_train_test(df)
    train.to_csv(TRAIN_FILE, index=False)
    test.to_csv(TEST_FILE, index=False)
    print(f"[Preprocess] Saved train -> {TRAIN_FILE}")
    print(f"[Preprocess] Saved test  -> {TEST_FILE}")

    # Save feature column list (everything except datetime and target)
    feature_cols = [c for c in df.columns if c not in ("datetime", "pm25", "source")]
    with open(FEAT_FILE, "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"[Preprocess] Saved {len(feature_cols)} feature names -> {FEAT_FILE}")
    print("[Preprocess] Done.")


if __name__ == "__main__":
    main()
