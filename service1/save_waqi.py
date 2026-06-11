"""
save_waqi.py — WAQI dan hozirgi PM2.5 ni CSV ga saqlaydi.
Gap bo'lsa (oxirgi CAMS qatori va WAQI o'rtasi) synthetic data bilan to'ldiradi.
Har soatda APScheduler tomonidan chaqiriladi.
"""

import os, requests
import numpy as np
import pandas as pd

TASHKENT_LAT = 41.2995
TASHKENT_LON = 69.2401
WAQI_TOKEN   = "511c18876a6a963f1b776571054dfb772c658cb0"
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
OUT_FILE     = os.path.join(DATA_DIR, "tashkent_pm25_weather.csv")

_AQI_BP = [
    (0,   50,  0.0,   12.0),
    (51,  100, 12.1,  35.4),
    (101, 150, 35.5,  55.4),
    (151, 200, 55.5, 150.4),
    (201, 300, 150.5, 250.4),
    (301, 400, 250.5, 350.4),
    (401, 500, 350.5, 500.4),
]
_WX_COLS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
            "wind_direction_10m", "surface_pressure", "precipitation"]

def aqi_to_ugm3(aqi):
    for lo, hi, pm_lo, pm_hi in _AQI_BP:
        if lo <= aqi <= hi:
            return round(pm_lo + (aqi - lo) / (hi - lo) * (pm_hi - pm_lo), 1)
    return None

def fetch_weather_day(dt_utc):
    """Bir kunlik barcha soatlik ob-havo. {'2026-06-10T16:00': {cols}} qaytaradi."""
    date_str = dt_utc.strftime("%Y-%m-%d")
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": TASHKENT_LAT, "longitude": TASHKENT_LON,
                "start_date": date_str, "end_date": date_str,
                "hourly": ",".join(_WX_COLS),
                "timezone": "UTC",
            },
            timeout=20,
        )
        r.raise_for_status()
        hourly = r.json().get("hourly", {})
        times  = hourly.get("time", [])
        return {t: {col: hourly.get(col, [None])[i] for col in _WX_COLS}
                for i, t in enumerate(times)}
    except Exception as ex:
        print(f"[save_waqi] ob-havo xato: {ex}")
    return {}

def save():
    if not os.path.exists(OUT_FILE):
        print("[save_waqi] CSV topilmadi — avval fetch_data.py ishlatib.")
        return

    # WAQI dan hozirgi o'lcham
    try:
        r = requests.get(
            f"https://api.waqi.info/feed/tashkent/?token={WAQI_TOKEN}",
            timeout=10,
        )
        d = r.json()
        if d.get("status") != "ok":
            print(f"[save_waqi] WAQI xato: {d.get('data')}")
            return
        data  = d["data"]
        aqi   = data.get("iaqi", {}).get("pm25", {}).get("v")
        t_str = data.get("time", {}).get("s")
        if aqi is None or t_str is None:
            print("[save_waqi] WAQI javobida pm25 yoki vaqt yo'q")
            return
        pm25   = aqi_to_ugm3(float(aqi))
        dt_utc = (pd.Timestamp(t_str) - pd.Timedelta(hours=5)).tz_localize("UTC")
    except Exception as ex:
        print(f"[save_waqi] WAQI xato: {ex}")
        return

    # CSV o'qi
    df = pd.read_csv(OUT_FILE)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)

    # Bir marta bugungi ob-havo
    wx_today = fetch_weather_day(dt_utc)

    # Oxirgi haqiqiy qator (synthetic emas)
    real_mask = df.get("source", pd.Series(["cams"] * len(df),
                       index=df.index)).isin(["cams", "sensor", "waqi"])
    last_real_dt = df.loc[real_mask, "datetime"].max() if real_mask.any() else df["datetime"].max()

    # ── Gap to'ldirish ──────────────────────────────────────────────────────
    if dt_utc > last_real_dt + pd.Timedelta(hours=1):
        gap_dts = pd.date_range(
            start=last_real_dt + pd.Timedelta(hours=1),
            end=dt_utc - pd.Timedelta(hours=1),
            freq="h", tz="UTC",
        )
        # Avval synthetic qatorlar bor-yo'qligini tekshir (qayta qo'shmasliq uchun)
        existing_dts = set(df["datetime"].astype(str))
        gap_dts = [g for g in gap_dts if str(g) not in existing_dts]

        if gap_dts:
            last_pm25 = float(df.loc[df["datetime"] == last_real_dt, "pm25"].values[0])
            linear = np.linspace(last_pm25, float(pm25), len(gap_dts) + 2)[1:-1]
            last_row = df[df["datetime"] == last_real_dt].iloc[0]

            gap_rows = []
            for i, dt in enumerate(gap_dts):
                pm25_syn = round(float(np.clip(
                    linear[i] + np.random.uniform(-3.0, 3.0), 0.0, 500.0)), 1)
                key = dt.strftime("%Y-%m-%dT%H:%M")
                wx  = wx_today.get(key) or {c: last_row.get(c) for c in _WX_COLS}
                row = {"datetime": dt, "pm25": pm25_syn, "source": "synthetic"}
                row.update(wx)
                gap_rows.append(row)

            df = pd.concat([df, pd.DataFrame(gap_rows)], ignore_index=True)
            df = df.sort_values("datetime").reset_index(drop=True)
            print(f"[save_waqi] {len(gap_rows)} soat synthetic gap to'ldirildi")

    # ── WAQI qatorini qo'sh / yangilash ────────────────────────────────────
    existing = df[df["datetime"] == dt_utc]
    if not existing.empty:
        df.loc[df["datetime"] == dt_utc, "pm25"]   = pm25
        df.loc[df["datetime"] == dt_utc, "source"] = "waqi"
        print(f"[save_waqi] {dt_utc} yangilandi -> {pm25} ug/m3 (AQI={int(aqi)})")
    else:
        key = dt_utc.strftime("%Y-%m-%dT%H:%M")
        wx  = wx_today.get(key) or {c: df.iloc[-1].get(c) for c in _WX_COLS}
        new_row = {"datetime": dt_utc, "pm25": pm25, "source": "waqi"}
        new_row.update(wx)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = df.sort_values("datetime").reset_index(drop=True)
        print(f"[save_waqi] {dt_utc} yangi qator -> {pm25} ug/m3 (AQI={int(aqi)})")

    df.to_csv(OUT_FILE, index=False)

if __name__ == "__main__":
    save()
