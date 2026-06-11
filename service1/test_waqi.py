import requests, json, time
import pandas as pd

KEY = "935ee76874b2d32d234daa214af392b447c71deb70bd46a5587884c034a663f4"
HEADERS = {"X-API-Key": KEY}

def check_sensor(sensor_id, name, date_from, date_to):
    print(f"\n=== {name} (sensor {sensor_id}) ===")
    # Oylik tekshiruv
    months = pd.date_range(date_from, date_to, freq="MS")
    for m in months:
        end = (m + pd.DateOffset(months=1) - pd.Timedelta(seconds=1))
        r = requests.get(
            f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements",
            params={"datetime_from": m.strftime("%Y-%m-%dT00:00:00Z"),
                    "datetime_to":   end.strftime("%Y-%m-%dT23:59:59Z"),
                    "limit": 1000, "period_name": "hour"},
            headers=HEADERS, timeout=30
        )
        raw = r.json()
        data = json.loads(raw) if isinstance(raw, str) else raw
        results = data.get("results", [])
        values = [r["value"] for r in results if r.get("value") is not None]
        max_hours = (end - m).total_seconds() / 3600
        pct = len(values)/max_hours*100
        avg = sum(values)/len(values) if values else 0
        bar = "#" * int(pct/10) + "." * (10 - int(pct/10))
        print(f"  {m.strftime('%Y-%m')}  [{bar}] {pct:5.1f}%  avg={avg:5.1f}  n={len(values)}")
        time.sleep(0.25)

# US Embassy — 2023 dan 2025 gacha
check_sensor(25916, "US Diplomatic Post", "2023-01-01", "2025-03-31")

# Sputnik-4 — bor bo'lgan barcha vaqt
check_sensor(13465748, "Sputnik-4", "2025-06-01", "2026-01-31")
