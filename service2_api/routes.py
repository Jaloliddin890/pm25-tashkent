"""
service2_api/routes.py
All REST endpoints for the PM2.5 Tashkent dashboard.
"""

import json
import os
import subprocess
import sys
import threading

from fastapi import APIRouter, Query, HTTPException
from . import state

router = APIRouter()

SERVICE1_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service1"))
PRED_JSON    = os.path.join(SERVICE1_DIR, "outputs", "predictions.json")

def _run_pipeline(hours: int = 72):
    steps = [
        ("fetch_data.py",  [],                       "Fetching latest WAQI data..."),
        ("preprocess.py",  [],                       "Preprocessing & feature engineering..."),
        ("evaluate.py",    [],                       "Updating historical predictions..."),
        ("predict.py",     ["--hours", str(hours)],  f"Generating {hours}h forecast..."),
    ]
    state.refresh_state["status"]  = "running"
    state.refresh_state["message"] = "Starting pipeline..."

    for script, args, message in steps:
        state.refresh_state["step"]    = script
        state.refresh_state["message"] = message

        result = subprocess.run(
            [sys.executable, os.path.join(SERVICE1_DIR, script)] + args,
            capture_output=True, text=True, cwd=SERVICE1_DIR,
        )
        if result.returncode != 0:
            state.refresh_state["status"]  = "error"
            state.refresh_state["message"] = f"Error in {script}: {result.stderr[-300:]}"
            return

    # Reload predictions into memory
    if os.path.exists(PRED_JSON):
        with open(PRED_JSON) as f:
            data = json.load(f)
        state.store.update(data)

    days = state.refresh_state.get("hours", hours) // 24
    state.refresh_state["status"]  = "done"
    state.refresh_state["step"]    = ""
    state.refresh_state["message"] = f"{days}-day forecast updated successfully!"


@router.get("/health")
def health():
    return {
        "status": "ok",
        "generated_at": state.store.get("generated_at"),
        "forecast_generated_at": state.store.get("forecast_generated_at"),
        "forecast_hours": state.store.get("forecast_hours", 72),
        "forecast_model": state.store.get("forecast_model"),
    }


@router.get("/metrics")
def metrics():
    """RMSE, MAE, R² for all 3 models."""
    return state.store.get("metrics", [])


@router.get("/predictions")
def predictions(days: int = Query(default=7, ge=1, le=30)):
    """Last N days of actual vs predicted values (all 3 models)."""
    hours = days * 24
    rows = state.store.get("predictions", [])
    return rows[-hours:] if len(rows) > hours else rows


@router.get("/forecast")
def forecast(hours: int = Query(default=168, ge=1, le=720)):
    """
    Next N hours of PM2.5 forecast for all 3 models.
    Returns { rf: [...], xgb: [...], lstm: [...] }
    """
    def trim(key):
        rows = state.store.get(key, [])
        return rows[:hours] if rows else []

    rf   = trim("forecast_rf")
    xgb  = trim("forecast_xgb")
    lstm = trim("forecast_lstm")

    if not lstm and not rf and not xgb:
        raise HTTPException(status_code=404, detail="No forecast available yet.")

    return {"rf": rf, "xgb": xgb, "lstm": lstm}


@router.get("/feature-importance")
def feature_importance():
    """Top 15 features ranked by importance score."""
    return state.store.get("feature_importance", [])


@router.get("/aqi")
def aqi():
    """Current AQI — both latest sensor reading and LSTM forecast."""
    forecast = state.store.get("aqi_current", {"pm25": None, "level": {"label": "Unknown", "color": "#aaa"}})
    sensor   = state.store.get("aqi_sensor",  None)
    return {"forecast": forecast, "sensor": sensor}


@router.get("/monthly")
def monthly():
    """Monthly average PM2.5 for bar chart."""
    return state.store.get("monthly_avg", [])


@router.post("/refresh-forecast")
def refresh_forecast(hours: int = Query(default=72, ge=24, le=720)):
    """Start the full pipeline in a background thread. hours: 24, 72, 168, or 720."""
    if state.refresh_state.get("status") == "running":
        raise HTTPException(status_code=409, detail="Pipeline already running.")
    days = hours // 24
    state.refresh_state["status"]  = "running"
    state.refresh_state["message"] = f"Starting {days}-day forecast pipeline..."
    state.refresh_state["step"]    = ""
    state.refresh_state["hours"]   = hours
    threading.Thread(target=_run_pipeline, args=(hours,), daemon=True).start()
    return {"status": "started", "hours": hours}


@router.get("/refresh-status")
def refresh_status():
    """Current pipeline status — frontend polls this every 2 seconds."""
    return state.refresh_state
