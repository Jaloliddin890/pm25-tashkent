"""
predict.py
Generates a 24-hour PM2.5 forecast using the best available model.
Appends the forecast to outputs/predictions.json.

Usage:
  python predict.py                    <- 72h forecast, XGBoost (default)
  python predict.py --hours 24         <- 24h forecast
  python predict.py --hours 72         <- 3-day forecast
  python predict.py --model rf         <- uses Random Forest
  python predict.py --model lstm       <- uses LSTM
"""

import argparse
import json
import os
import pickle
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

AQI_LEVELS = [
    (0,   12,  "Good",                    "#00e400"),
    (12,  35,  "Moderate",                "#ffff00"),
    (35,  55,  "Unhealthy for Sensitive", "#ff7e00"),
    (55,  150, "Unhealthy",               "#ff0000"),
    (150, 250, "Very Unhealthy",          "#8f3f97"),
    (250, 999, "Hazardous",               "#7e0023"),
]

def aqi_label(pm25: float) -> dict:
    for lo, hi, label, color in AQI_LEVELS:
        if lo <= pm25 < hi:
            return {"label": label, "color": color}
    return {"label": "Hazardous", "color": "#7e0023"}

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "models")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

LSTM_SEQUENCE_LEN   = 24
LSTM_NOLAGS_SEQ_LEN = 48
LSTM_NOLAGS_COLS    = [
    "pm25",
    "temperature_2m", "relative_humidity_2m",
    "wind_speed_10m", "wind_direction_10m",
    "surface_pressure", "precipitation",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
    "wind_u", "wind_v",
]


def load_latest_features() -> tuple[np.ndarray, list, pd.DataFrame]:
    """
    Load the last N rows from processed.csv to use as input for forecasting.
    Returns (X_last, feature_cols, processed_df)
    """
    processed = pd.read_csv(
        os.path.join(DATA_DIR, "processed.csv"), parse_dates=["datetime"]
    )
    with open(os.path.join(DATA_DIR, "feature_cols.json")) as f:
        feature_cols = json.load(f)
    return processed[feature_cols].values, feature_cols, processed


def forecast_xgb_rf(model, X_last: np.ndarray, feature_cols: list,
                     processed_df: pd.DataFrame, forecast_hours: int = 72) -> list:
    """
    Auto-regressive forecast for tree-based models.
    Each step: predict t+1 -> shift lags -> predict t+2 ... etc.
    """
    last_row = dict(zip(feature_cols, X_last[-1]))
    last_datetime = processed_df["datetime"].iloc[-1]

    forecast = []
    lag_buffer = list(processed_df["pm25"].iloc[-168:])  # 7-day buffer so roll_7d updates

    for step in range(forecast_hours):
        x = np.array([last_row[c] for c in feature_cols]).reshape(1, -1)
        pred = float(model.predict(x)[0])
        pred = max(0.0, pred)   # no negative PM2.5

        ts = last_datetime + timedelta(hours=step + 1)
        forecast.append({
            "datetime": ts.isoformat(),
            "pm25_forecast": round(pred, 2),
        })

        # Update lag features for next step
        lag_buffer.append(pred)
        for lag in [1, 2, 3, 6, 12, 24, 48]:
            key = f"pm25_lag_{lag}h"
            if key in last_row and len(lag_buffer) >= lag:
                last_row[key] = lag_buffer[-lag]

        # Update rolling means
        for window in [3, 6, 24]:
            key = f"pm25_roll_{window}h"
            if key in last_row and len(lag_buffer) >= window:
                last_row[key] = float(np.mean(lag_buffer[-window:]))

        if "pm25_roll_7d" in last_row and len(lag_buffer) >= 24 * 7:
            last_row["pm25_roll_7d"] = float(np.mean(lag_buffer[-24 * 7:]))

        # Update cyclical time features
        h = ts.hour
        dow = ts.dayofweek
        m = ts.month
        last_row["hour_sin"]  = np.sin(2 * np.pi * h / 24)
        last_row["hour_cos"]  = np.cos(2 * np.pi * h / 24)
        last_row["dow_sin"]   = np.sin(2 * np.pi * dow / 7)
        last_row["dow_cos"]   = np.cos(2 * np.pi * dow / 7)
        last_row["month_sin"] = np.sin(2 * np.pi * (m - 1) / 12)
        last_row["month_cos"] = np.cos(2 * np.pi * (m - 1) / 12)

    return forecast


def forecast_lstm_nolags(processed_df: pd.DataFrame, forecast_hours: int = 72) -> list:
    try:
        from tensorflow.keras.models import load_model
    except ImportError:
        print("[Predict] TensorFlow not available. Falling back to XGBoost.")
        return None

    model_path  = os.path.join(MODELS_DIR, "lstm_nolags.keras")
    scaler_path = os.path.join(MODELS_DIR, "lstm_nolags_scaler.pkl")
    if not os.path.exists(model_path):
        print("[Predict] lstm_nolags.keras not found. Falling back to XGBoost.")
        return None

    model = load_model(model_path)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    n_cols        = len(LSTM_NOLAGS_COLS)
    last_datetime = processed_df["datetime"].iloc[-1]
    df_nl         = processed_df[LSTM_NOLAGS_COLS].tail(LSTM_NOLAGS_SEQ_LEN)
    window        = scaler.transform(df_nl.values).copy()   # (48, 15)

    # Frozen weather values (last observed)
    last_row = processed_df[LSTM_NOLAGS_COLS].iloc[-1].to_dict()

    forecast = []
    for step in range(forecast_hours):
        x_in       = window.reshape(1, LSTM_NOLAGS_SEQ_LEN, n_cols)
        pred_scaled = float(model.predict(x_in, verbose=0)[0, 0])

        dummy = np.zeros((1, n_cols))
        dummy[0, 0] = pred_scaled
        pred_pm25 = float(np.clip(scaler.inverse_transform(dummy)[0, 0], 0, 500))

        ts = last_datetime + timedelta(hours=step + 1)
        forecast.append({"datetime": ts.isoformat(), "pm25_forecast": round(pred_pm25, 2)})

        h, dow, m = ts.hour, ts.dayofweek, ts.month
        next_vals = [
            pred_pm25,
            last_row["temperature_2m"],
            last_row["relative_humidity_2m"],
            last_row["wind_speed_10m"],
            last_row["wind_direction_10m"],
            last_row["surface_pressure"],
            last_row["precipitation"],
            np.sin(2 * np.pi * h / 24),
            np.cos(2 * np.pi * h / 24),
            np.sin(2 * np.pi * dow / 7),
            np.cos(2 * np.pi * dow / 7),
            np.sin(2 * np.pi * (m - 1) / 12),
            np.cos(2 * np.pi * (m - 1) / 12),
            last_row.get("wind_u", 0.0),
            last_row.get("wind_v", 0.0),
        ]
        next_scaled = scaler.transform(np.array([next_vals]))   # (1, 15)
        window = np.vstack([window[1:], next_scaled])

    return forecast


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, default=168,
                        help="How many hours ahead to forecast (default: 168 = 7 days)")
    args = parser.parse_args()

    forecast_hours = max(1, min(args.hours, 720))
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    X_all, feature_cols, processed_df = load_latest_features()

    print(f"[Predict] Generating {forecast_hours}h forecast — RF + XGBoost + LSTM (No Lags) ...")

    # RF
    with open(os.path.join(MODELS_DIR, "random_forest.pkl"), "rb") as f:
        rf_model = pickle.load(f)
    fc_rf = forecast_xgb_rf(rf_model, X_all, feature_cols, processed_df, forecast_hours)
    print(f"  RF    : {fc_rf[0]['pm25_forecast']} ... {fc_rf[-1]['pm25_forecast']} ug/m3")

    # XGBoost
    import xgboost as xgblib
    xgb_model = xgblib.XGBRegressor()
    xgb_model.load_model(os.path.join(MODELS_DIR, "xgboost.json"))
    fc_xgb = forecast_xgb_rf(xgb_model, X_all, feature_cols, processed_df, forecast_hours)
    print(f"  XGB   : {fc_xgb[0]['pm25_forecast']} ... {fc_xgb[-1]['pm25_forecast']} ug/m3")

    # LSTM No Lags
    fc_lstm = forecast_lstm_nolags(processed_df, forecast_hours)
    if fc_lstm is None:
        fc_lstm = fc_xgb
        print("  LSTM  : skipped (fallback to XGBoost)")
    else:
        print(f"  LSTM  : {fc_lstm[0]['pm25_forecast']} ... {fc_lstm[-1]['pm25_forecast']} ug/m3")

    pred_path = os.path.join(OUTPUTS_DIR, "predictions.json")
    if os.path.exists(pred_path):
        with open(pred_path) as f:
            payload = json.load(f)
    else:
        payload = {}

    payload["forecast_rf"]           = fc_rf
    payload["forecast_xgb"]          = fc_xgb
    payload["forecast_lstm"]         = fc_lstm
    payload["forecast"]              = fc_lstm   # backward compat
    payload["forecast_hours"]        = forecast_hours
    payload["forecast_generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["forecast_model"]        = "RF + XGBoost + LSTM (No Lags)"

    # AQI sensor — latest actual reading from processed.csv
    pm25_sensor = round(float(processed_df["pm25"].iloc[-1]), 1)
    sensor_dt   = processed_df["datetime"].iloc[-1].isoformat()
    payload["aqi_sensor"] = {
        "pm25": pm25_sensor,
        "level": aqi_label(pm25_sensor),
        "datetime": sensor_dt,
    }
    print(f"  AQI sensor  -> {pm25_sensor} ug/m3 (actual {sensor_dt})")

    # AQI forecast — LSTM forecast point closest to now
    now_utc = datetime.now(timezone.utc)
    best, best_diff = None, float("inf")
    for pt in fc_lstm:
        dt = datetime.fromisoformat(pt["datetime"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = abs((dt - now_utc).total_seconds())
        if diff < best_diff:
            best_diff = diff
            best = pt
    if best:
        pm25_now = round(best["pm25_forecast"], 1)
        payload["aqi_current"] = {"pm25": pm25_now, "level": aqi_label(pm25_now)}
        print(f"  AQI forecast-> {pm25_now} ug/m3 (forecast {best['datetime']})")

    with open(pred_path, "w") as f:
        json.dump(payload, f, indent=2)

    days = forecast_hours // 24
    print(f"\n[Predict] {days}-day forecast (3 models, {forecast_hours} points each) -> {pred_path}")


if __name__ == "__main__":
    main()
