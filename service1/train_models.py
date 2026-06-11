"""
train_models.py
Trains Random Forest, XGBoost, and LSTM on the preprocessed data.

Input : data/train.csv, data/test.csv, data/feature_cols.json
Output: models/random_forest.pkl
        models/xgboost.json
        models/lstm.keras
        outputs/rf_analysis/       — 5 PNG + metrics.json
        outputs/xgb_es_analysis/   — 6 PNG + metrics.json + feature_importance.json
        outputs/lstm_ipynb_analysis/ — 4 PNG + metrics.json
"""

import json
import os
import pickle
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # GUI oynasiz saqlash
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "models")
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

LSTM_SEQUENCE_LEN = 24   # 24-hour input window


# ── Load Data ─────────────────────────────────────────────────────────────────

def load_data():
    train = pd.read_csv(os.path.join(DATA_DIR, "train.csv"), parse_dates=["datetime"])
    test  = pd.read_csv(os.path.join(DATA_DIR, "test.csv"),  parse_dates=["datetime"])
    with open(os.path.join(DATA_DIR, "feature_cols.json")) as f:
        feature_cols = json.load(f)

    X_train = train[feature_cols].values
    y_train = train["pm25"].values
    X_test  = test[feature_cols].values
    y_test  = test["pm25"].values

    print(f"[Train] X_train: {X_train.shape}, X_test: {X_test.shape}")
    return X_train, y_train, X_test, y_test, feature_cols


# ── Random Forest ─────────────────────────────────────────────────────────────

def train_random_forest(X_train, y_train):
    print("\n[RF] Training Random Forest …")
    t0 = time.time()
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_leaf=2,
        max_features="sqrt",
        n_jobs=-1,
        random_state=42,
    )
    rf.fit(X_train, y_train)
    elapsed = time.time() - t0
    print(f"[RF] Done in {elapsed:.1f}s")

    out_path = os.path.join(MODELS_DIR, "random_forest.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(rf, f)
    print(f"[RF] Saved -> {out_path}")
    return rf, elapsed


# ── XGBoost ───────────────────────────────────────────────────────────────────

def train_xgboost(X_train, y_train):
    print("\n[XGB] Training XGBoost …")
    t0 = time.time()
    model = xgb.XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_train, y_train)],
              verbose=False)
    elapsed = time.time() - t0
    print(f"[XGB] Done in {elapsed:.1f}s")

    out_path = os.path.join(MODELS_DIR, "xgboost.json")
    model.save_model(out_path)
    print(f"[XGB] Saved -> {out_path}")
    return model, elapsed


# ── LSTM ──────────────────────────────────────────────────────────────────────

def make_sequences(X: np.ndarray, y: np.ndarray, seq_len: int):
    """Reshape flat features into (samples, seq_len, n_features) for LSTM."""
    Xs, ys = [], []
    for i in range(seq_len, len(X)):
        Xs.append(X[i - seq_len:i])
        ys.append(y[i])
    return np.array(Xs), np.array(ys)


def train_lstm(X_train, y_train, X_test, y_test):
    print("\n[LSTM] Training LSTM …")

    # Scale features
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    # Save scaler alongside model
    scaler_path = os.path.join(MODELS_DIR, "lstm_scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    # Build sequences
    X_tr_seq, y_tr_seq = make_sequences(X_train_sc, y_train, LSTM_SEQUENCE_LEN)
    X_te_seq, y_te_seq = make_sequences(X_test_sc,  y_test,  LSTM_SEQUENCE_LEN)
    print(f"[LSTM] Sequence shapes — train: {X_tr_seq.shape}, test: {X_te_seq.shape}")

    # Import TensorFlow here so the script still partially works if TF is absent
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    except ImportError:
        print("[LSTM] TensorFlow not installed. Skipping LSTM training.")
        print("       Run: pip install tensorflow   (or pip install tensorflow-cpu)")
        return None, 0, None, None

    n_features = X_tr_seq.shape[2]
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(LSTM_SEQUENCE_LEN, n_features)),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.summary()

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=15,
        restore_best_weights=True,
    )
    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=5,
        min_lr=1e-6,
    )

    t0 = time.time()
    history = model.fit(
        X_tr_seq, y_tr_seq,
        validation_split=0.1,   # train dan 10% validation — test set ga tegmaydi
        epochs=100,
        batch_size=32,
        callbacks=[early_stop, reduce_lr],
        verbose=1,
    )
    elapsed = time.time() - t0
    print(f"[LSTM] Done in {elapsed:.1f}s")

    out_path = os.path.join(MODELS_DIR, "lstm.keras")
    model.save(out_path)
    print(f"[LSTM] Saved -> {out_path}")

    loss_history = {
        "Train Loss": history.history["loss"],
        "Val Loss":   history.history["val_loss"],
    }
    return model, elapsed, scaler, loss_history


# ── Analysis plots ────────────────────────────────────────────────────────────

def _save_analysis(out_dir: str, model_name: str,
                   y_test, y_pred, datetimes,
                   feature_cols=None, importances=None,
                   loss_history=None):
    """Har model uchun standart 4-6 ta PNG va metrics.json saqlaydi."""
    os.makedirs(out_dir, exist_ok=True)

    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mae  = float(mean_absolute_error(y_test, y_pred))
    r2   = float(r2_score(y_test, y_pred))
    print(f"  {model_name:<15} RMSE={rmse:.2f}  MAE={mae:.2f}  R²={r2:.4f}")

    # metrics.json
    with open(os.path.join(out_dir, f"{model_name.lower().replace(' ','_')}_metrics.json"), "w") as f:
        json.dump({"model": model_name, "rmse": rmse, "mae": mae, "r2": r2}, f, indent=2)

    residuals = np.array(y_pred) - np.array(y_test)
    dts = pd.to_datetime(datetimes)

    # ── 1. Actual vs Predicted (son 30 kun) ──────────────────────────────────
    n_show = min(720, len(y_test))
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(dts[-n_show:], y_test[-n_show:],
            label="Actual", color="#2196F3", linewidth=1.2, alpha=0.9)
    ax.plot(dts[-n_show:], y_pred[-n_show:],
            label="Predicted", color="#FF5722", linewidth=1.0, alpha=0.8, linestyle="--")
    ax.set_title(f"{model_name} — Actual vs Predicted (last 30 days)", fontsize=13)
    ax.set_xlabel("Date"); ax.set_ylabel("PM2.5 (µg/m³)")
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "01_actual_vs_predicted.png"), dpi=150)
    plt.close()

    # ── 2. Scatter plot ───────────────────────────────────────────────────────
    lim = max(y_test.max(), np.array(y_pred).max()) * 1.05
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y_test, y_pred, alpha=0.3, s=8, color="#2196F3")
    ax.plot([0, lim], [0, lim], "r--", linewidth=1.5, label="Perfect fit")
    ax.set_title(f"{model_name} — Scatter (R²={r2:.3f})", fontsize=13)
    ax.set_xlabel("Actual PM2.5"); ax.set_ylabel("Predicted PM2.5")
    ax.legend(); ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "02_scatter.png"), dpi=150)
    plt.close()

    # ── 3. Residuals histogram ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(residuals, bins=60, color="#9C27B0", edgecolor="white", linewidth=0.4, alpha=0.85)
    ax.axvline(0, color="red", linewidth=1.5, linestyle="--")
    ax.set_title(f"{model_name} — Residuals (MAE={mae:.2f})", fontsize=13)
    ax.set_xlabel("Residual (Predicted − Actual)"); ax.set_ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "03_residuals.png"), dpi=150)
    plt.close()

    # ── 4. Monthly RMSE ───────────────────────────────────────────────────────
    df_err = pd.DataFrame({"dt": dts.tz_localize(None) if dts.tz is not None else dts, "sq_err": residuals**2})
    df_err["ym"] = df_err["dt"].dt.to_period("M")
    monthly_rmse = df_err.groupby("ym")["sq_err"].mean().apply(np.sqrt).reset_index()
    monthly_rmse["label"] = monthly_rmse["ym"].astype(str)

    fig, ax = plt.subplots(figsize=(max(8, len(monthly_rmse)), 4))
    ax.bar(monthly_rmse["label"], monthly_rmse["sq_err"],
           color="#FF9800", edgecolor="white", linewidth=0.5)
    ax.set_title(f"{model_name} — Monthly RMSE", fontsize=13)
    ax.set_xlabel("Month"); ax.set_ylabel("RMSE (µg/m³)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "04_monthly_rmse.png"), dpi=150)
    plt.close()

    # ── 5. Feature Importance (RF / XGBoost) ─────────────────────────────────
    if feature_cols is not None and importances is not None:
        pairs = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)[:15]
        feats, vals = zip(*pairs)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(list(reversed(feats)), list(reversed(vals)), color="#4CAF50")
        ax.set_title(f"{model_name} — Top 15 Feature Importances", fontsize=13)
        ax.set_xlabel("Importance")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "05_feature_importance.png"), dpi=150)
        plt.close()

        fi_data = [{"feature": f, "importance": float(v)} for f, v in pairs]
        with open(os.path.join(out_dir, "xgb_feature_importance.json"), "w") as f:
            json.dump(fi_data, f, indent=2)

    # ── 6. Training curve (XGBoost eval / LSTM history) ──────────────────────
    if loss_history is not None:
        fig, ax = plt.subplots(figsize=(9, 4))
        for label, values in loss_history.items():
            ax.plot(values, label=label, linewidth=1.5)
        ax.set_title(f"{model_name} — Training Curve", fontsize=13)
        ax.set_xlabel("Epoch / Round"); ax.set_ylabel("Loss (MSE)")
        ax.legend(); ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "06_training_curve.png"), dpi=150)
        plt.close()

    print(f"  [{model_name}] Rasmlar saqlandi -> {out_dir}")


# ── Feature Importance ────────────────────────────────────────────────────────

def save_feature_importance(xgb_model, feature_cols: list):
    importances = xgb_model.feature_importances_
    pairs = sorted(
        zip(feature_cols, importances),
        key=lambda x: x[1],
        reverse=True,
    )[:15]
    result = [{"feature": f, "importance": float(v)} for f, v in pairs]

    out_path = os.path.join(OUTPUTS_DIR, "feature_importance.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[FI] Top 15 feature importances saved -> {out_path}")
    for item in result[:5]:
        print(f"     {item['feature']:<30} {item['importance']:.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(MODELS_DIR,  exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    X_train, y_train, X_test, y_test, feature_cols = load_data()
    test_df   = pd.read_csv(os.path.join(DATA_DIR, "test.csv"), parse_dates=["datetime"])
    datetimes = test_df["datetime"].astype(str).tolist()

    # ── Random Forest ─────────────────────────────────────────────────────────
    rf_model, rf_time = train_random_forest(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    _save_analysis(
        out_dir      = os.path.join(OUTPUTS_DIR, "rf_analysis_new"),
        model_name   = "Random Forest",
        y_test       = y_test,
        y_pred       = rf_preds,
        datetimes    = datetimes,
        feature_cols = feature_cols,
        importances  = rf_model.feature_importances_,
    )

    # ── XGBoost ───────────────────────────────────────────────────────────────
    xgb_model, xgb_time = train_xgboost(X_train, y_train)
    xgb_preds = xgb_model.predict(X_test)
    _save_analysis(
        out_dir      = os.path.join(OUTPUTS_DIR, "xgb_analysis_new"),
        model_name   = "XGBoost",
        y_test       = y_test,
        y_pred       = xgb_preds,
        datetimes    = datetimes,
        feature_cols = feature_cols,
        importances  = xgb_model.feature_importances_,
    )
    save_feature_importance(xgb_model, feature_cols)

    # ── LSTM ──────────────────────────────────────────────────────────────────
    lstm_model, lstm_time, scaler, lstm_history = train_lstm(X_train, y_train, X_test, y_test)
    if lstm_model is not None:
        X_test_sc = scaler.transform(X_test)
        X_te_seq, y_te_seq = make_sequences(X_test_sc, y_test, LSTM_SEQUENCE_LEN)
        lstm_preds = lstm_model.predict(X_te_seq, verbose=0).flatten()
        _save_analysis(
            out_dir      = os.path.join(OUTPUTS_DIR, "lstm_analysis_new"),
            model_name   = "LSTM",
            y_test       = y_te_seq,
            y_pred       = lstm_preds,
            datetimes    = datetimes[LSTM_SEQUENCE_LEN:],
            loss_history = lstm_history,
        )

    print("\n[Train] All models trained successfully.")
    print(f"  Random Forest : {rf_time:.1f}s")
    print(f"  XGBoost       : {xgb_time:.1f}s")
    if lstm_model is not None:
        print(f"  LSTM          : {lstm_time:.1f}s")


if __name__ == "__main__":
    main()
