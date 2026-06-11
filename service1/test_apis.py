import requests

OPENAQ_API_KEY = "935ee76874b2d32d234daa214af392b447c71deb70bd46a5587884c034a663f4"   # ← paste your key here too

# ── OpenAQ ────────────────────────────────────────────────────
print("=== OpenAQ ===")
r = requests.get(
    "https://api.openaq.org/v3/locations",
    params={
        "coordinates": "41.2995,69.2401",
        "radius": 25000,
        "limit": 10,
    },
    headers={"accept": "application/json", "X-API-Key": OPENAQ_API_KEY},
    timeout=15,
)
print("Status:", r.status_code)
print("Raw response:", r.text[:500])
data = r.json() if isinstance(r.json(), dict) else {}
results = data.get("results", [])
print("Locations found:", len(results))
for loc in results:
    sensors = loc.get("sensors", [])
    params = [s["parameter"]["name"] for s in sensors if "parameter" in s]
    print(f"  → ID={loc['id']}  name={loc.get('name','?')}  parameters={params}")

# ── Open-Meteo ────────────────────────────────────────────────
print("\n=== Open-Meteo ===")
r2 = requests.get(
    "https://archive-api.open-meteo.com/v1/archive",
    params={
        "latitude": 41.2995,
        "longitude": 69.2401,
        "start_date": "2024-01-01",
        "end_date": "2024-01-02",
        "hourly": "temperature_2m",
        "timezone": "UTC",
    },
    timeout=15,
)
print("Status:", r2.status_code)
times = r2.json().get("hourly", {}).get("time", [])
print("Records returned:", len(times))
if times:
    print("First:", times[0], "| Last:", times[-1])
