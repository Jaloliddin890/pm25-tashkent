"""
eda.py
Exploratory Data Analysis — 5 ta grafik yaratadi va saqlaydi.

Input : data/processed.csv
Output: outputs/eda/01_pm25_over_time.png
        outputs/eda/02_monthly_avg.png
        outputs/eda/03_hourly_avg.png
        outputs/eda/04_correlation_heatmap.png
        outputs/eda/05_pm25_distribution.png
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "eda")

os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(DATA_DIR, "processed.csv"), parse_dates=["datetime"])
print(f"Loaded {len(df)} rows for EDA.")

year_min = df["datetime"].dt.year.min()
year_max = df["datetime"].dt.year.max()
year_label = f"{year_min}–{year_max}" if year_min != year_max else str(year_min)

# ── 1. PM2.5 vaqt boyicha ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(df["datetime"], df["pm25"], linewidth=0.6, color="#2196F3", alpha=0.8)
ax.set_title(f"PM2.5 Levels Over Time — Tashkent ({year_label})", fontsize=14)
ax.set_xlabel("Date")
ax.set_ylabel("PM2.5 (µg/m³)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45)
ax.axhline(15,  color="green",  linestyle="--", linewidth=1, label="WHO limit (15)")
ax.axhline(35,  color="orange", linestyle="--", linewidth=1, label="Moderate (35)")
ax.axhline(55,  color="red",    linestyle="--", linewidth=1, label="Unhealthy (55)")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "01_pm25_over_time.png"), dpi=150)
plt.close()
print("  [1/5] pm25_over_time saved.")

# ── 2. Oylik o'rtacha (xronologik tartibda) ───────────────────────────────────
df["ym"] = df["datetime"].dt.to_period("M")
monthly_chron = (
    df.groupby("ym")["pm25"]
    .mean()
    .reset_index()
    .sort_values("ym")
)
monthly_chron["label"] = monthly_chron["ym"].dt.strftime("%b %Y")

colors = []
for v in monthly_chron["pm25"]:
    if v < 15:   colors.append("#4CAF50")
    elif v < 35: colors.append("#FFC107")
    elif v < 55: colors.append("#FF9800")
    else:        colors.append("#F44336")

fig, ax = plt.subplots(figsize=(max(10, len(monthly_chron) * 0.8), 5))
bars = ax.bar(monthly_chron["label"], monthly_chron["pm25"],
              color=colors, edgecolor="white", linewidth=0.5)
ax.set_title(f"Monthly Average PM2.5 — Tashkent ({year_label})", fontsize=14)
ax.set_xlabel("Month")
ax.set_ylabel("PM2.5 (µg/m³)")
ax.axhline(15, color="green",  linestyle="--", linewidth=1, label="WHO limit (15)")
ax.axhline(35, color="orange", linestyle="--", linewidth=1, label="Moderate (35)")
ax.legend(fontsize=9)
plt.xticks(rotation=45, ha="right")
for bar, val in zip(bars, monthly_chron["pm25"]):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
            f"{val:.1f}", ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "02_monthly_avg.png"), dpi=150)
plt.close()
print("  [2/5] monthly_avg saved.")

# ── 3. Soat boyicha o'rtacha ──────────────────────────────────────────────────
hourly = df.groupby(df["datetime"].dt.hour)["pm25"].mean()

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(hourly.index, hourly.values, marker="o", markersize=5,
        color="#9C27B0", linewidth=2)
ax.fill_between(hourly.index, hourly.values, alpha=0.15, color="#9C27B0")
ax.set_title(f"Average PM2.5 by Hour of Day — Tashkent ({year_label})", fontsize=14)
ax.set_xlabel("Hour (UTC)")
ax.set_ylabel("PM2.5 (µg/m³)")
ax.set_xticks(range(0, 24))
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "03_hourly_avg.png"), dpi=150)
plt.close()
print("  [3/5] hourly_avg saved.")

# ── 4. Korrelyatsiya heatmap ──────────────────────────────────────────────────
weather_cols = [c for c in [
    "pm25", "temperature_2m", "relative_humidity_2m",
    "wind_speed_10m", "surface_pressure", "precipitation",
    "pm25_lag_1h", "pm25_lag_24h", "pm25_roll_24h"
] if c in df.columns]

corr = df[weather_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(
    corr, annot=True, fmt=".2f", cmap="RdYlGn",
    center=0, linewidths=0.5, ax=ax,
    annot_kws={"size": 9}
)
ax.set_title("Correlation Heatmap — PM2.5 vs Weather Features", fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "04_correlation_heatmap.png"), dpi=150)
plt.close()
print("  [4/5] correlation_heatmap saved.")

# ── 5. PM2.5 taqsimoti histogram ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(df["pm25"], bins=60, color="#2196F3", edgecolor="white",
        linewidth=0.4, alpha=0.85)
ax.set_title(f"PM2.5 Distribution — Tashkent ({year_label})", fontsize=14)
ax.set_xlabel("PM2.5 (µg/m³)")
ax.set_ylabel("Frequency (hours)")
for val, label, color in [(15, "WHO (15)", "green"),
                           (35, "Moderate (35)", "orange"),
                           (55, "Unhealthy (55)", "red")]:
    ax.axvline(val, color=color, linestyle="--", linewidth=1.5, label=label)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "05_pm25_distribution.png"), dpi=150)
plt.close()
print("  [5/5] pm25_distribution saved.")

print(f"\nDone. Barcha grafiklar saqlandi: {OUTPUT_DIR}")
print(f"  PM2.5 stats — mean: {df['pm25'].mean():.1f}, "
      f"min: {df['pm25'].min():.1f}, max: {df['pm25'].max():.1f}")
