"""
evaluate.py
Loads all 3 trained models, runs predictions on test set,
computes RMSE / MAE / R², and builds predictions.json for the dashboard.

Input : data/test.csv, data/feature_cols.json
        models/random_forest.pkl, models/xgboost_es.json, models/lstm.keras
Output: outputs/predictions.json
        outputs/predictions.csv
"""

import json
import os
import pickle
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

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
DASHBOARD_ROWS    = 720   # 30 days × 24 hours


# ── AQI helpers ───────────────────────────────────────────────────────────────

AQI_LEVELS = [
    (0,   12,  "Good",                        "#00e400"),
    (12,  35,  "Moderate",                    "#ffff00"),
    (35,  55,  "Unhealthy for Sensitive",     "#ff7e00"),
    (55,  150, "Unhealthy",                   "#ff0000"),
    (150, 250, "Very Unhealthy",              "#8f3f97"),
    (250, 999, "Hazardous",                   "#7e0023"),
]

def aqi_label(pm25: float) -> dict:
    for lo, hi, label, color in AQI_LEVELS:
        if lo <= pm25 < hi:
            return {"label": label, "color": color}
    return {"label": "Hazardous", "color": "#7e0023"}


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_pred, model_name: str) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae  = float(mean_absolute_error(y_true, y_pred))
    r2   = float(r2_score(y_true, y_pred))
    print(f"  {model_name:<15} RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.4f}")
    return {"model": model_name, "rmse": rmse, "mae": mae, "r2": r2}


# ── Load Models ───────────────────────────────────────────────────────────────

def load_rf():
    path = os.path.join(MODELS_DIR, "random_forest.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def load_xgb():
    import xgboost as xgb
    model = xgb.XGBRegressor()
    model.load_model(os.path.join(MODELS_DIR, "xgboost.json"))
    return model

def load_lstm():
    try:
        from tensorflow.keras.models import load_model
    except ImportError:
        return None, None
    model_path  = os.path.join(MODELS_DIR, "lstm_nolags.keras")
    scaler_path = os.path.join(MODELS_DIR, "lstm_nolags_scaler.pkl")
    if not os.path.exists(model_path):
        return None, None
    model = load_model(model_path)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)
    return model, scaler


# ── LSTM Sequences ────────────────────────────────────────────────────────────

def make_sequences(X: np.ndarray, seq_len: int):
    Xs = []
    for i in range(seq_len, len(X)):
        Xs.append(X[i - seq_len:i])
    return np.array(Xs)


def inverse_pm25_nolags(scaler, y_scaled: np.ndarray) -> np.ndarray:
    dummy = np.zeros((len(y_scaled), len(LSTM_NOLAGS_COLS)))
    dummy[:, 0] = y_scaled.ravel()
    return scaler.inverse_transform(dummy)[:, 0]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # Load test data
    test = pd.read_csv(os.path.join(DATA_DIR, "test.csv"), parse_dates=["datetime"])
    with open(os.path.join(DATA_DIR, "feature_cols.json")) as f:
        feature_cols = json.load(f)

    X_test = test[feature_cols].values
    y_test = test["pm25"].values
    datetimes = test["datetime"].astype(str).tolist()

    print("[Evaluate] Running predictions …\n")

    # ── Random Forest ─────────────────────────────────────────────────────────
    rf = load_rf()
    if rf is not None:
        rf_preds = rf.predict(X_test)
        rf_metrics = compute_metrics(y_test, rf_preds, "Random Forest")
    else:
        print("  Random Forest  skipped (model not found)")
        rf_preds = np.full(len(y_test), np.nan)
        rf_metrics = {"model": "Random Forest", "rmse": None, "mae": None, "r2": None}

    # ── XGBoost ───────────────────────────────────────────────────────────────
    xgb_model = load_xgb()
    xgb_preds = xgb_model.predict(X_test)
    xgb_metrics = compute_metrics(y_test, xgb_preds, "XGBoost")

    # ── LSTM (No Lags) ────────────────────────────────────────────────────────
    lstm_model, lstm_scaler = load_lstm()
    lstm_preds_full = np.full(len(y_test), np.nan)

    if lstm_model is not None:
        X_nl        = test[LSTM_NOLAGS_COLS].values
        X_nl_scaled = lstm_scaler.transform(X_nl)
        X_nl_seq    = make_sequences(X_nl_scaled, LSTM_NOLAGS_SEQ_LEN)
        y_nl_scaled = lstm_model.predict(X_nl_seq, verbose=0).flatten()
        y_nl_pred   = inverse_pm25_nolags(lstm_scaler, y_nl_scaled)
        lstm_preds_full[LSTM_NOLAGS_SEQ_LEN:] = np.clip(y_nl_pred, 0, 500)
        valid = ~np.isnan(lstm_preds_full)
        lstm_metrics = compute_metrics(y_test[valid], lstm_preds_full[valid], "LSTM")
    else:
        print("  LSTM          skipped (model not found)")
        lstm_metrics = {"model": "LSTM", "rmse": None, "mae": None, "r2": None}

    # ── Build predictions.json ────────────────────────────────────────────────

    # Last DASHBOARD_ROWS rows for dashboard display
    n   = len(y_test)
    idx = max(0, n - DASHBOARD_ROWS)

    def safe_float(v):
        return None if (v is None or np.isnan(v)) else round(float(v), 2)

    dashboard_rows = []
    for i in range(idx, n):
        dashboard_rows.append({
            "datetime": datetimes[i],
            "actual":   safe_float(y_test[i]),
            "rf":       safe_float(rf_preds[i]),
            "xgb":      safe_float(xgb_preds[i]),
            "lstm":     safe_float(lstm_preds_full[i]),
        })

    # Current AQI — LSTM prediction for current hour (floor to :00)
    # e.g. 11:51 → use 11:00 (06:00 UTC); 12:01 → use 12:00 (07:00 UTC)
    from datetime import timezone as _tz
    now_utc = datetime.now(_tz.utc).replace(minute=0, second=0, microsecond=0)

    test_dt = pd.to_datetime(test["datetime"])
    if test_dt.dt.tz is None:
        test_dt = test_dt.dt.tz_localize("UTC")
    else:
        test_dt = test_dt.dt.tz_convert("UTC")

    match = np.where((test_dt == now_utc).values)[0]
    current_pm25 = None
    if len(match) > 0:
        val = lstm_preds_full[match[0]]
        if not np.isnan(val):
            current_pm25 = float(val)

    if current_pm25 is None:
        valid_idx = np.where(~np.isnan(lstm_preds_full))[0]
        current_pm25 = float(lstm_preds_full[valid_idx[-1]]) if len(valid_idx) > 0 else float(y_test[-1])

    # Monthly averages — sorted chronologically by first occurrence
    test["ym"] = test["datetime"].dt.tz_localize(None).dt.to_period("M")
    monthly = (
        test.groupby("ym")["pm25"]
        .mean()
        .reset_index()
        .sort_values("ym")
    )
    monthly_avg = [
        {"month": row["ym"].strftime("%b %Y"), "pm25": round(row["pm25"], 1)}
        for _, row in monthly.iterrows()
    ]

    # Feature importance (from XGBoost ES training)
    fi_path = os.path.join(OUTPUTS_DIR, "xgb_es_analysis", "xgb_feature_importance.json")
    if os.path.exists(fi_path):
        with open(fi_path) as f:
            feature_importance = json.load(f)
    else:
        feature_importance = []

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": [rf_metrics, xgb_metrics, lstm_metrics],
        "predictions": dashboard_rows,
        "feature_importance": feature_importance,
        "aqi_current": {
            "pm25": round(current_pm25, 1),
            "level": aqi_label(current_pm25),
        },
        "monthly_avg": monthly_avg,
        "forecast": [],   # filled by predict.py
    }

    pred_json_path = os.path.join(OUTPUTS_DIR, "predictions.json")
    with open(pred_json_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[Evaluate] Saved predictions.json -> {pred_json_path}")

    # Save CSV
    results_df = pd.DataFrame({
        "datetime": datetimes,
        "actual":   y_test,
        "rf":       rf_preds,
        "xgb":      xgb_preds,
        "lstm":     lstm_preds_full,
    })
    csv_path = os.path.join(OUTPUTS_DIR, "predictions.csv")
    results_df.to_csv(csv_path, index=False)
    print(f"[Evaluate] Saved predictions.csv  -> {csv_path}")
    print("[Evaluate] Done.")


if __name__ == "__main__":
    main()
