"""
fill_gaps.py
Mavjud CSV dagi bo'sh PM2.5 qatorlarini real OpenAQ data bilan to'ldiradi.
Mavjud PM2.5 qiymatlarga TEGMAYDI.
"""

import os
import time
import requests
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_FILE = os.path.join(DATA_DIR, "tashkent_pm25_weather.csv")

OPENAQ_API_KEY = "935ee76874b2d32d234daa214af392b447c71deb70bd46a5587884c034a663f4"
HEADERS = {"X-API-Key": OPENAQ_API_KEY}

SENSORS = [
    (25916,    "US Diplomatic Post"),
    (13465748, "Sputnik-4"),
]


def to_naive_utc(series: pd.Series) -> pd.Series:
    """Datetime series ni timezone-naive UTC ga o'tkazish."""
    if hasattr(series.dt, 'tz') and series.dt.tz is not None:
        return series.dt.tz_convert("UTC").dt.tz_localize(None)
    return series


def fetch_sensor_range(sensor_id: int, date_from: str, date_to: str) -> pd.DataFrame:
    """Berilgan sana oraligida sensor ma'lumotlarini hafta-hafta yuklaydi."""
    start = pd.Timestamp(date_from, tz="UTC")
    end   = pd.Timestamp(date_to,   tz="UTC")

    # Haftalik windows (W-MON) + boshlanish kunini qo'shish
    week_starts = [start]
    cur = start
    while True:
        next_mon = cur + pd.offsets.Week(weekday=0)
        if next_mon >= end:
            break
        week_starts.append(next_mon)
        cur = next_mon

    records = []
    for ws in week_starts:
        we = min(ws + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59), end)
        try:
            r = requests.get(
                f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements",
                params={
                    "datetime_from": ws.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "datetime_to":   we.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "limit":         1000,
                    "page":          1,
                    "period_name":   "hour",
                },
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            for rec in r.json().get("results", []):
                try:
                    dt  = rec["period"]["datetimeFrom"]["utc"]
                    val = rec["value"]
                    if val is not None and val >= 0:
                        records.append({"datetime": dt, "pm25_new": float(val)})
                except (KeyError, TypeError):
                    pass
            time.sleep(0.3)
        except Exception as e:
            print(f"    [{ws.date()}] xato: {e}")

    if not records:
        return pd.DataFrame()

    fetched = pd.DataFrame(records)
    # Naive UTC ga o'tkazish
    fetched["datetime"] = pd.to_datetime(fetched["datetime"], utc=True).dt.tz_localize(None)
    fetched["datetime"] = fetched["datetime"].dt.floor("h")
    fetched = fetched.groupby("datetime")["pm25_new"].mean().reset_index()
    return fetched


def main():
    print(f"[FillGaps] CSV yuklanmoqda ...")
    df = pd.read_csv(CSV_FILE, parse_dates=["datetime"])

    # Barcha datetime ni naive UTC ga o'tkazish
    df["datetime"] = to_naive_utc(df["datetime"])
    df["datetime"] = df["datetime"].dt.floor("h")
    df = df.sort_values("datetime").reset_index(drop=True)

    total_before = df["pm25"].isna().sum()
    print(f"[FillGaps] Boshliq qatorlar: {total_before}")

    # Katta boshliqlarni aniqlash
    df["has"] = df["pm25"].notna()
    df["grp"] = (df["has"] != df["has"].shift()).cumsum()
    gaps = (
        df[~df["has"]]
        .groupby("grp")["datetime"]
        .agg(["min", "max", "count"])
        .rename(columns={"min": "s", "max": "e", "count": "n"})
    )
    big_gaps = gaps[gaps["n"] > 24].sort_values("s")
    df = df.drop(columns=["has", "grp"])

    print(f"[FillGaps] {len(big_gaps)} ta katta boshliq topildi.\n")

    filled_total = 0

    for _, row in big_gaps.iterrows():
        date_from = row["s"].strftime("%Y-%m-%d")
        date_to   = row["e"].strftime("%Y-%m-%d")
        print(f"Bo'shliq: {date_from} -> {date_to} ({row['n']} soat)")

        all_fetched = pd.DataFrame()

        for sensor_id, name in SENSORS:
            print(f"  Sensor {sensor_id} ({name}) ...")
            fetched = fetch_sensor_range(sensor_id, date_from, date_to)
            if not fetched.empty:
                print(f"  {len(fetched)} qator topildi.")
                all_fetched = pd.concat([all_fetched, fetched]).drop_duplicates("datetime")
            else:
                print(f"  Data yo'q.")

        if all_fetched.empty:
            print(f"  Real data yo'q — qoladi.\n")
            continue

        # Merge: faqat NaN bo'lgan qatorlarga yangi qiymat
        before = df["pm25"].isna().sum()
        df = df.merge(all_fetched, on="datetime", how="left")
        mask = df["pm25"].isna() & df["pm25_new"].notna()
        df.loc[mask, "pm25"] = df.loc[mask, "pm25_new"]
        df = df.drop(columns=["pm25_new"])
        after = df["pm25"].isna().sum()
        filled = before - after
        filled_total += filled
        print(f"  {filled} qator to'ldirildi.\n")

    total_after = df["pm25"].isna().sum()
    print(f"[FillGaps] Natija:")
    print(f"  Avval bo'sh : {total_before}")
    print(f"  To'ldirildi : {filled_total}")
    print(f"  Hali bo'sh  : {total_after}")

    df.to_csv(CSV_FILE, index=False)
    print(f"[FillGaps] Saqlandi: {CSV_FILE}")

    if total_after > 0:
        print(f"\n[FillGaps] {total_after} qator hali bo'sh.")
        print("  Keyingi qadam: python generate_synthetic.py  (faqat bo'shliqlar uchun)")


if __name__ == "__main__":
    main()
