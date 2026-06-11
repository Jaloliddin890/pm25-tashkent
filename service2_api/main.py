"""
service2_api/main.py
FastAPI backend — loads predictions.json and serves it via REST endpoints.
APScheduler refreshes data every hour automatically.

Run:
  cd service2_api
  uvicorn main:app --reload --port 8000

Install extra dependency:
  pip install apscheduler
"""

import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from . import state

PREDICTIONS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "service1", "outputs", "predictions.json"
))
SERVICE1_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "service1"
))


def _load_store() -> dict:
    """Read predictions.json from disk into memory."""
    if os.path.exists(PREDICTIONS_PATH):
        with open(PREDICTIONS_PATH) as f:
            data = json.load(f)
        print(f"[API] Loaded predictions.json "
              f"({len(data.get('predictions', []))} rows, "
              f"{data.get('forecast_hours', '?')}h forecast)")
        return data
    print(f"[API] WARNING: predictions.json not found at {PREDICTIONS_PATH}")
    print("[API] Run service1/main.py first to generate it.")
    return {
        "generated_at": None,
        "metrics": [],
        "predictions": [],
        "feature_importance": [],
        "aqi_current": {"pm25": 0, "level": {"label": "Unknown", "color": "#aaa"}},
        "monthly_avg": [],
        "forecast": [],
        "forecast_hours": 72,
    }


def _run_script(script_name: str, extra_args: list[str] = None) -> bool:
    """Run a service1 Python script. Returns True on success."""
    cmd = [sys.executable, os.path.join(SERVICE1_DIR, script_name)]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=SERVICE1_DIR)
    if result.returncode != 0:
        print(f"[Scheduler] ERROR running {script_name}:\n{result.stderr[:500]}")
        return False
    return True


async def save_waqi_job():
    """Har soatda WAQI dan hozirgi PM2.5 ni CSV ga saqlaydi."""
    print(f"[Scheduler] WAQI save at {datetime.now(timezone.utc).isoformat()}")
    _run_script("save_waqi.py")


async def refresh_data():
    """
    Har 3 soatda: fetch → preprocess → forecast → store yangilash.
    Agar biror qadam muvaffaqiyatsiz bo'lsa store o'zgarmaydi.
    """
    print(f"[Scheduler] Refresh started at {datetime.now(timezone.utc).isoformat()}")

    steps = [
        ("fetch_data.py",  []),
        ("preprocess.py",  []),
        ("predict.py",     ["--hours", "720"]),
    ]
    for script, args in steps:
        if not _run_script(script, args):
            print(f"[Scheduler] Refresh aborted at {script}. Store unchanged.")
            return

    state.store = _load_store()
    print(f"[Scheduler] Refresh complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.store = _load_store()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(save_waqi_job, "interval", hours=1, id="waqi_save")
    scheduler.add_job(refresh_data,  "interval", hours=3, id="refresh")
    scheduler.start()
    print("[API] APScheduler started — WAQI every 1h, full refresh every 3h.")

    yield

    scheduler.shutdown()
    print("[API] APScheduler stopped.")


app = FastAPI(
    title="PM2.5 Tashkent Forecast API",
    description="REST API serving ML model predictions for the React dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
