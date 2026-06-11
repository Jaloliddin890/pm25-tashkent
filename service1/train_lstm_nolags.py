"""
train_lstm_nolags.py
Lag va rolling featurelarsiz LSTM — faqat ob-havo + vaqt + pm25 ketma-ketligi.
LSTM o'zi temporal pattern o'rganadi.

Input : data/train.csv, data/test.csv
Output: models/lstm_nolags.keras
        models/lstm_nolags_scaler.pkl
        outputs/lstm_nolags_analysis/
"""

import os, time, json, pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "models")
OUT_DIR     = os.path.join(os.path.dirname(__file__), "outputs", "lstm_nolags_analysis")

TRAIN_FILE  = os.path.join(DATA_DIR, "train.csv")
TEST_FILE   = os.path.join(DATA_DIR, "test.csv")

SEQUENCE_LEN = 48   # 48 soat — lag yo'q, LSTM ko'proq context kerak

# Faqat ob-havo + vaqt + wind — lag/rolling YO'Q
WEATHER_COLS = [
    "temperature_2m", "relative_humidity_2m",
    "wind_speed_10m", "wind_direction_10m",
    "surface_pressure", "precipitation",
]
TIME_COLS = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos"]
WIND_COLS = ["wind_u", "wind_v"]

FEATURE_COLS = WEATHER_COLS + TIME_COLS + WIND_COLS  # 14 ta
# pm25 ham sequence ga kiradi — target emas, input sifatida
SEQUENCE_COLS = ["pm25"] + FEATURE_COLS   # 15 ta


def load_data():
    train = pd.read_csv(TRAIN_FILE, parse_dates=["datetime"])
    test  = pd.read_csv(TEST_FILE,  parse_dates=["datetime"])

    # Faqat kerakli ustunlar mavjudligini tekshirish
    missing = [c for c in SEQUENCE_COLS if c not in train.columns]
    if missing:
        print(f"[ERROR] Ustunlar topilmadi: {missing}")
        return None, None

    # Faqat SEQUENCE_COLS + target ni olamiz
    all_cols = ["datetime", "pm25"] + FEATURE_COLS
    train = train[[c for c in all_cols if c in train.columns]].dropna().reset_index(drop=True)
    test  = test[[c  for c in all_cols if c in test.columns]].dropna().reset_index(drop=True)

    print(f"[Data] Train: {len(train)} | Test: {len(test)}")
    print(f"[Data] Features: {len(SEQUENCE_COLS)} (pm25 + {len(FEATURE_COLS)} weather/time)")
    return train, test


def make_sequences(df, scaler=None, fit_scaler=False):
    """MinMaxScaler bilan normalize qilib, (X, y) sequence lar yaratadi."""
    vals = df[SEQUENCE_COLS].values   # (n, 15)

    if fit_scaler:
        scaler = MinMaxScaler()
        vals_scaled = scaler.fit_transform(vals)
    else:
        vals_scaled = scaler.transform(vals)

    X, y, dts = [], [], []
    for i in range(SEQUENCE_LEN, len(vals_scaled)):
        X.append(vals_scaled[i - SEQUENCE_LEN:i, :])   # (48, 15)
        y.append(vals_scaled[i, 0])                     # pm25 (birinchi ustun)
        dts.append(df["datetime"].iloc[i])

    return np.array(X), np.array(y), np.array(dts), scaler


def build_model(n_features):
    try:
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.regularizers import l2
    except ImportError:
        print("[ERROR] TensorFlow topilmadi.")
        return None

    model = Sequential([
        LSTM(64, return_sequences=True,
             input_shape=(SEQUENCE_LEN, n_features),
             kernel_regularizer=l2(1e-4)),
        Dropout(0.3),
        LSTM(32, kernel_regularizer=l2(1e-4)),
        Dropout(0.3),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    return model


def train(model, X_train, y_train):
    try:
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    except ImportError:
        return model, []

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=20, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=7, min_lr=1e-6, verbose=0),
    ]
    history = model.fit(
        X_train, y_train,
        epochs=150, batch_size=32,
        validation_split=0.1,
        callbacks=callbacks,
        verbose=1,
    )
    return model, history.history["loss"], history.history.get("val_loss", [])


def inverse_pm25(scaler, y_scaled):
    """Faqat pm25 (birinchi ustun) ni teskari scale qiladi."""
    dummy = np.zeros((len(y_scaled), len(SEQUENCE_COLS)))
    dummy[:, 0] = y_scaled.ravel()
    return scaler.inverse_transform(dummy)[:, 0]


def save_analysis(y_test, y_pred, dts, train_loss, val_loss):
    os.makedirs(OUT_DIR, exist_ok=True)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)
    metrics = {"rmse": round(rmse, 4), "mae": round(mae, 4), "r2": round(r2, 4)}

    with open(os.path.join(OUT_DIR, "lstm_nolags_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[Metrics] RMSE={rmse:.2f}  MAE={mae:.2f}  R2={r2:.4f}")

    # 1. Actual vs Predicted (oxirgi 720 soat)
    n = min(720, len(y_test))
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(y_test[-n:], label="Actual", color="#38bdf8", linewidth=1)
    ax.plot(y_pred[-n:], label="Predicted", color="#fb923c", linewidth=1, alpha=0.85)
    ax.set_title(f"LSTM (No Lags) — Actual vs Predicted  |  RMSE={rmse:.2f}, R²={r2:.4f}")
    ax.set_xlabel("Soat"); ax.set_ylabel("PM2.5 (ug/m3)")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "01_actual_vs_predicted.png"), dpi=120)
    plt.close()

    # 2. Scatter
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y_test, y_pred, alpha=0.3, s=5, color="#38bdf8")
    lim = max(y_test.max(), y_pred.max()) * 1.05
    ax.plot([0, lim], [0, lim], "r--", linewidth=1)
    ax.set_title(f"Scatter  R²={r2:.4f}")
    ax.set_xlabel("Actual PM2.5"); ax.set_ylabel("Predicted PM2.5")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "02_scatter.png"), dpi=120)
    plt.close()

    # 3. Residuals
    residuals = y_test - y_pred
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(residuals, bins=60, color="#a78bfa", edgecolor="white", linewidth=0.3)
    ax.axvline(0, color="red", linestyle="--")
    ax.set_title(f"Residuals  mean={residuals.mean():.2f}, std={residuals.std():.2f}")
    ax.set_xlabel("Residual"); ax.set_ylabel("Count")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "03_residuals.png"), dpi=120)
    plt.close()

    # 4. Monthly RMSE
    dts_pd = pd.to_datetime(dts)
    if dts_pd.tz is not None:
        dts_pd = dts_pd.tz_localize(None)
    months  = dts_pd.to_period("M")
    df_res  = pd.DataFrame({"ym": months, "err": (y_test - y_pred) ** 2})
    monthly = df_res.groupby("ym")["err"].mean().apply(np.sqrt).reset_index()
    monthly["ym_str"] = monthly["ym"].astype(str)
    monthly = monthly.sort_values("ym")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(monthly["ym_str"], monthly["err"], color="#fb923c")
    ax.set_title("Monthly RMSE — LSTM No Lags")
    ax.set_xlabel("Oy"); ax.set_ylabel("RMSE")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "04_monthly_rmse.png"), dpi=120)
    plt.close()

    # 5. Training curve
    if train_loss:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(train_loss, label="train_loss", color="#38bdf8")
        if val_loss:
            ax.plot(val_loss, label="val_loss", color="#fb923c")
        ax.set_title("Training Curve — LSTM No Lags")
        ax.set_xlabel("Epoch"); ax.set_ylabel("MSE Loss")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, "05_training_curve.png"), dpi=120)
        plt.close()

    print(f"[Analysis] Saqlandi: {OUT_DIR}")
    return metrics


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1. Data yuklash
    train_df, test_df = load_data()
    if train_df is None:
        return

    # 2. Sequence yaratish
    print(f"\n[Sequences] Uzunlik: {SEQUENCE_LEN}h | Features: {len(SEQUENCE_COLS)}")
    X_train, y_train, _, scaler = make_sequences(train_df, fit_scaler=True)
    X_test,  y_test_s, dts, _  = make_sequences(test_df, scaler=scaler)

    print(f"  X_train: {X_train.shape}  y_train: {y_train.shape}")
    print(f"  X_test:  {X_test.shape}   y_test:  {y_test_s.shape}")

    # 3. Model qurish
    model = build_model(n_features=len(SEQUENCE_COLS))
    if model is None:
        return
    model.summary()

    # 4. Train
    print("\n[Train] Boshlanmoqda...")
    t0 = time.time()
    model, train_loss, val_loss = train(model, X_train, y_train)
    elapsed = time.time() - t0
    print(f"[Train] {elapsed:.1f}s  |  Epochs: {len(train_loss)}")

    # 5. Predict + inverse scale
    y_pred_s = model.predict(X_test, verbose=0).ravel()
    y_test   = inverse_pm25(scaler, y_test_s)
    y_pred   = inverse_pm25(scaler, y_pred_s)
    y_pred   = np.clip(y_pred, 0, 500)

    # 6. Saqlash
    model_path  = os.path.join(MODELS_DIR, "lstm_nolags.keras")
    scaler_path = os.path.join(MODELS_DIR, "lstm_nolags_scaler.pkl")
    model.save(model_path)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"[Save] Model: {model_path}")
    print(f"[Save] Scaler: {scaler_path}")

    # 7. Grafik va metrikalar
    metrics = save_analysis(y_test, y_pred, dts, train_loss, val_loss)

    print(f"\n{'='*50}")
    print(f"LSTM No Lags natijasi:")
    print(f"  RMSE : {metrics['rmse']}")
    print(f"  MAE  : {metrics['mae']}")
    print(f"  R2   : {metrics['r2']}")
    print(f"  Vaqt : {elapsed:.1f}s")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
