"""
fetch_data.py — Hybrid PM2.5 data strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PM2.5 manbalari (ustunlik tartibi):
  1. Real sensor (OpenAQ) — mavjud bo'lgan joylarda
  2. WAQI (aqicn.org)    — hozirgi kun real-time o'lcham
  3. CAMS (Open-Meteo AQ) — bo'shliqlarni to'ldiradi

Sensor qamrovi (historical, o'zgarmaydi):
  US Embassy  (25916)    : 2024-01-01 -> 2025-03-31
  Sputnik-4   (13465748) : 2025-10-01 -> 2026-01-19

Incremental mode: mavjud CSV bo'lsa faqat yangi data olinadi.
WAQI: har runda hozirgi soat uchun 1 qator saqlanadi.
"""

import os, time, json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

TASHKENT_LAT = 41.2995
TASHKENT_LON = 69.2401
DATE_FROM = "2024-01-01"
DATE_TO   = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
OUT_FILE     = os.path.join(DATA_DIR, "tashkent_pm25_weather.csv")

OPENAQ_KEY     = "935ee76874b2d32d234daa214af392b447c71deb70bd46a5587884c034a663f4"
OPENAQ_HEADERS = {"X-API-Key": OPENAQ_KEY}

WAQI_TOKEN = "511c18876a6a963f1b776571054dfb772c658cb0"

# EPA AQI → µg/m³ konvertatsiya jadval
_AQI_BP = [
    (0,   50,  0.0,   12.0),
    (51,  100, 12.1,  35.4),
    (101, 150, 35.5,  55.4),
    (151, 200, 55.5, 150.4),
    (201, 300, 150.5, 250.4),
    (301, 400, 250.5, 350.4),
    (401, 500, 350.5, 500.4),
]

def _aqi_to_ugm3(aqi: float) -> float:
    for lo, hi, pm_lo, pm_hi in _AQI_BP:
        if lo <= aqi <= hi:
            return round(pm_lo + (aqi - lo) / (hi - lo) * (pm_hi - pm_lo), 1)
    return None

SENSORS = [
    {"id": 25916,    "name": "US Embassy",  "from": "2024-01-01", "to": "2025-03-31"},
    {"id": 13465748, "name": "Sputnik-4",   "from": "2025-10-01", "to": "2026-01-19"},
]


# ── 1. CAMS (Open-Meteo AQ) ───────────────────────────────────────────────────

def fetch_cams_pm25(date_from: str, date_to: str) -> pd.DataFrame:
    print(f"[CAMS] {date_from} -> {date_to} ...")
    start = pd.Timestamp(date_from)
    end   = pd.Timestamp(date_to)
    chunks, cur = [], start
    while cur <= end:
        nxt = min(cur + pd.DateOffset(years=1), end)
        chunks.append((cur.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d")))
        cur = nxt + pd.Timedelta(days=1)

    records = []
    for s, e in chunks:
        try:
            r = requests.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": TASHKENT_LAT, "longitude": TASHKENT_LON,
                        "hourly": "pm2_5", "start_date": s, "end_date": e,
                        "timezone": "UTC"},
                timeout=60,
            )
            r.raise_for_status()
            hourly = r.json().get("hourly", {})
            for t, v in zip(hourly.get("time", []), hourly.get("pm2_5", [])):
                if v is not None:
                    records.append({"datetime": t, "pm25_cams": float(v)})
            print(f"  {s} -> {e}: {len(hourly.get('time',[]))} soat")
        except Exception as ex:
            print(f"  [{s}] xato: {ex}")

    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    print(f"[CAMS] {len(df)} qator\n")
    return df


# ── 2. OpenAQ real sensor ─────────────────────────────────────────────────────

def fetch_sensor(sensor_id: int, name: str, date_from: str, date_to: str) -> pd.DataFrame:
    print(f"[OpenAQ] {name} (sensor {sensor_id}) {date_from} -> {date_to}")
    weeks = pd.date_range(start=date_from, end=date_to, freq="W-MON", tz="UTC")
    records = []
    total_weeks = len(weeks)
    for i, week_start in enumerate(weeks):
        week_end = week_start + pd.Timedelta(days=6, hours=23, minutes=59)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  [{i+1}/{total_weeks}] {week_start.strftime('%Y-%m-%d')} ...")
        try:
            r = requests.get(
                f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements",
                params={"datetime_from": week_start.strftime("%Y-%m-%dT00:00:00Z"),
                        "datetime_to":   week_end.strftime("%Y-%m-%dT23:59:59Z"),
                        "limit": 1000, "period_name": "hour"},
                headers=OPENAQ_HEADERS, timeout=20,
            )
            raw = r.json()
            data = raw if isinstance(raw, dict) else json.loads(raw)
            for rec in data.get("results", []):
                try:
                    dt  = rec["period"]["datetimeFrom"]["utc"]
                    val = rec["value"]
                    if val is not None and 0 <= val <= 500:
                        records.append({"datetime": dt, "pm25_sensor": float(val)})
                except (KeyError, TypeError):
                    pass
            time.sleep(0.2)
        except Exception:
            time.sleep(0.5)

    if not records:
        print(f"  0 qator topildi\n")
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.floor("h")
    df = df.groupby("datetime")["pm25_sensor"].mean().reset_index()
    print(f"  {len(df)} soatlik qiymat\n")
    return df


# ── 3. Ob-havo (Open-Meteo Weather) ──────────────────────────────────────────

def fetch_weather(date_from: str, date_to: str) -> pd.DataFrame:
    print(f"[Weather] {date_from} -> {date_to} ...")
    try:
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": TASHKENT_LAT, "longitude": TASHKENT_LON,
                    "start_date": date_from, "end_date": date_to,
                    "hourly": ",".join(["temperature_2m", "relative_humidity_2m",
                                        "wind_speed_10m", "wind_direction_10m",
                                        "surface_pressure", "precipitation"]),
                    "timezone": "UTC"},
            timeout=60,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json()["hourly"]).rename(columns={"time": "datetime"})
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        print(f"[Weather] {len(df)} soat\n")
        return df
    except Exception as ex:
        print(f"[Weather] Xato: {ex}")
        return pd.DataFrame()


# ── 4. Bugungi ob-havo (forecast endpoint) ───────────────────────────────────

_WX_COLS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
            "wind_direction_10m", "surface_pressure", "precipitation"]

def fetch_weather_day(dt_utc: pd.Timestamp) -> dict:
    """Bir kunlik barcha soatlik ob-havoni oladi. {'2026-06-10T16:00': {cols}} qaytaradi."""
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
            timeout=30,
        )
        r.raise_for_status()
        hourly = r.json().get("hourly", {})
        times  = hourly.get("time", [])
        return {t: {col: hourly.get(col, [None])[i] for col in _WX_COLS}
                for i, t in enumerate(times)}
    except Exception as ex:
        print(f"[Weather Day] Xato: {ex}")
    return {}


# ── 5. WAQI real-time ────────────────────────────────────────────────────────

def fetch_waqi_pm25(token: str):
    """Hozirgi WAQI o'lchamini oladi. (datetime_utc, pm25_ugm3, aqi_raw) qaytaradi."""
    try:
        r = requests.get(
            f"https://api.waqi.info/feed/tashkent/?token={token}",
            timeout=10,
        )
        d = r.json()
        if d.get("status") != "ok":
            print(f"[WAQI] API xato: {d.get('data')}")
            return None, None, None
        data  = d["data"]
        aqi   = data.get("iaqi", {}).get("pm25", {}).get("v")
        t_str = data.get("time", {}).get("s")   # Toshkent local vaqti (UTC+5)
        if aqi is None or t_str is None:
            return None, None, None
        pm25  = _aqi_to_ugm3(float(aqi))
        # Local vaqtdan UTC ga o'tkazish (Toshkent = UTC+5)
        dt_utc = (pd.Timestamp(t_str) - pd.Timedelta(hours=5)).tz_localize("UTC")
        print(f"[WAQI] {dt_utc}  PM2.5={pm25} ug/m3  (AQI={int(aqi)})")
        return dt_utc, pm25, int(aqi)
    except Exception as ex:
        print(f"[WAQI] Xato: {ex}")
        return None, None, None


# ── 5. Birlashtirish (bir chunk) ──────────────────────────────────────────────

def build_merged(weather_df: pd.DataFrame, cams_df: pd.DataFrame,
                 sensor_frames: list) -> pd.DataFrame:
    merged = pd.merge(weather_df, cams_df, on="datetime", how="left")
    merged["pm25"]   = merged["pm25_cams"]
    merged["source"] = "cams"

    if sensor_frames:
        all_sensors = pd.concat(sensor_frames).drop_duplicates("datetime").sort_values("datetime")
        merged = pd.merge(merged, all_sensors, on="datetime", how="left")
        mask = merged["pm25_sensor"].notna()
        merged.loc[mask, "pm25"]   = merged.loc[mask, "pm25_sensor"]
        merged.loc[mask, "source"] = "sensor"
        print(f"[Merge] {mask.sum()} qator real sensor bilan almashtirildi "
              f"({mask.sum()/len(merged)*100:.1f}%)")
        merged = merged.drop(columns=["pm25_sensor"])

    merged = merged.drop(columns=["pm25_cams"])
    return merged.sort_values("datetime").reset_index(drop=True)


# ── Shared: WAQI + gap to'ldirish ────────────────────────────────────────────

def _apply_waqi_and_fill_gap(df: pd.DataFrame) -> pd.DataFrame:
    """WAQI ni oladi, gap ni synthetic bilan to'ldiradi, WAQI qatorini qo'shadi."""
    waqi_dt, waqi_pm25, _ = fetch_waqi_pm25(WAQI_TOKEN)
    if waqi_dt is None or waqi_pm25 is None:
        return df

    wx_today = fetch_weather_day(waqi_dt)

    # Oxirgi haqiqiy qator (synthetic emas)
    real_mask    = df.get("source", pd.Series(["cams"] * len(df),
                          index=df.index)).isin(["cams", "sensor", "waqi"])
    last_real_dt = df.loc[real_mask, "datetime"].max() if real_mask.any() else df["datetime"].max()

    # ── Gap to'ldirish ────────────────────────────────────────────────────
    if waqi_dt > last_real_dt + pd.Timedelta(hours=1):
        gap_dts = pd.date_range(
            start=last_real_dt + pd.Timedelta(hours=1),
            end=waqi_dt - pd.Timedelta(hours=1),
            freq="h", tz="UTC",
        )
        # Allaqachon mavjud bo'lgan synthetic qatorlarni o'tkazib yubor
        existing_set = set(df["datetime"].astype(str))
        gap_dts = [g for g in gap_dts if str(g) not in existing_set]

        if gap_dts:
            last_pm25   = float(df.loc[df["datetime"] == last_real_dt, "pm25"].values[0])
            linear      = np.linspace(last_pm25, waqi_pm25, len(gap_dts) + 2)[1:-1]
            last_wx_row = df[df["datetime"] == last_real_dt].iloc[0]

            gap_rows = []
            for i, dt in enumerate(gap_dts):
                pm25_syn = round(float(np.clip(
                    linear[i] + np.random.uniform(-3.0, 3.0), 0.0, 500.0)), 1)
                key = dt.strftime("%Y-%m-%dT%H:%M")
                wx  = wx_today.get(key) or {c: last_wx_row.get(c) for c in _WX_COLS}
                row = {"datetime": dt, "pm25": pm25_syn, "source": "synthetic"}
                row.update(wx)
                gap_rows.append(row)

            df = pd.concat([df, pd.DataFrame(gap_rows)], ignore_index=True)
            df = df.sort_values("datetime").reset_index(drop=True)
            print(f"[Gap] {len(gap_rows)} soat synthetic: "
                  f"{gap_dts[0].strftime('%H:%M')} -> {gap_dts[-1].strftime('%H:%M')} UTC")

    # ── WAQI qatorini qo'sh / yangilash ──────────────────────────────────
    idx = df[df["datetime"] == waqi_dt].index
    if len(idx):
        df.loc[idx, "pm25"]   = waqi_pm25
        df.loc[idx, "source"] = "waqi"
        print(f"[WAQI] {waqi_dt} yangilandi -> {waqi_pm25} ug/m3")
    else:
        key = waqi_dt.strftime("%Y-%m-%dT%H:%M")
        wx  = wx_today.get(key) or {c: df.iloc[-1].get(c) for c in _WX_COLS}
        new_row = {"datetime": waqi_dt, "pm25": waqi_pm25, "source": "waqi"}
        new_row.update(wx)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = df.sort_values("datetime").reset_index(drop=True)
        print(f"[WAQI] {waqi_dt} yangi qator -> {waqi_pm25} ug/m3")

    return df


def _print_stats(df: pd.DataFrame):
    total       = len(df)
    n_sensor    = (df["source"] == "sensor").sum()    if "source" in df.columns else 0
    n_waqi      = (df["source"] == "waqi").sum()      if "source" in df.columns else 0
    n_synthetic = (df["source"] == "synthetic").sum() if "source" in df.columns else 0
    n_cams      = (df["source"] == "cams").sum()      if "source" in df.columns else total
    print(f"\n[Natija]  Jami: {total} qator")
    print(f"  Real sensor: {n_sensor}  WAQI: {n_waqi}  "
          f"Synthetic: {n_synthetic}  CAMS: {n_cams}  "
          f"Null pm25: {df['pm25'].isna().sum()}")
    print(f"  Vaqt: {df['datetime'].min()} -> {df['datetime'].max()}")


# ── 6. Full fetch (--full rejim) ──────────────────────────────────────────────

def _full_fetch():
    """CAMS + ob-havo + sensor + WAQI. Birinchi marta yoki qayta qurishda ishlatiladi."""
    print(f"[Fetch] FULL mode — {DATE_FROM} -> {DATE_TO}")

    cams_df    = fetch_cams_pm25(DATE_FROM, DATE_TO)
    weather_df = fetch_weather(DATE_FROM, DATE_TO)
    if cams_df.empty or weather_df.empty:
        print("[ERROR] CAMS yoki ob-havo data kelmadi.")
        return

    sensor_frames = []
    for s in SENSORS:
        sdf = fetch_sensor(s["id"], s["name"], s["from"], s["to"])
        if not sdf.empty:
            sensor_frames.append(sdf)

    merged = build_merged(weather_df, cams_df, sensor_frames)
    merged = _apply_waqi_and_fill_gap(merged)
    _print_stats(merged)
    merged.to_csv(OUT_FILE, index=False)
    print(f"[Done] Saqlandi: {OUT_FILE}")


# ── 7. Main ───────────────────────────────────────────────────────────────────

def main():
    import sys
    os.makedirs(DATA_DIR, exist_ok=True)

    if "--full" in sys.argv or not os.path.exists(OUT_FILE):
        if not os.path.exists(OUT_FILE):
            print("[Fetch] CSV topilmadi — to'liq fetch boshlanadi...")
        _full_fetch()
        return

    # ── Oddiy rejim: faqat WAQI + gap filling (sekundlar ichida) ─────────────
    print("[Fetch] WAQI-only mode — mavjud CSV yangilanadi...")
    df = pd.read_csv(OUT_FILE)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = _apply_waqi_and_fill_gap(df)
    _print_stats(df)
    df.to_csv(OUT_FILE, index=False)
    print(f"[Done] Saqlandi: {OUT_FILE}")


if __name__ == "__main__":
    main()
