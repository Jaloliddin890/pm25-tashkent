# User Manual
## PM2.5 Air Quality Forecasting Dashboard — Tashkent

**Author:** Jaloloddin Temirov
**Course:** Pearson BTEC Level 6 — Unit 2 Independent Project
**Date:** June 2026

---

## What is this application?

This is a web-based dashboard that monitors and forecasts PM2.5 air pollution in Tashkent, Uzbekistan. It pulls real sensor readings from the city, runs them through three machine learning models, and presents everything in an interactive interface — historical trends, a 7-day forecast, and a health advisory that tells you whether it is safe to go outside.

The application was built as part of a diploma project. It is not a toy — it uses real data from the US Embassy sensor and the Chilanzar monitoring station, combined with satellite-based atmospheric data from the European CAMS reanalysis system.

---

## Before you start

You will need the following installed on your machine:

- **Python 3.12** — the LSTM model will not run on other versions. Python 3.9 or higher works for the other two models, but 3.12 is strongly recommended.
- **Node.js 18 or later** — for the React dashboard.
- A stable internet connection — the app fetches live data from the WAQI air quality API.

If you are on Windows, Git Bash or PowerShell both work fine. Avoid the default Command Prompt for Python commands — it sometimes has encoding issues with certain characters.

---

## Setting up the backend

Open a terminal and go into the backend folder:

```
cd Source_Code/backend
```

Install the required Python packages:

```
pip install -r requirements.txt
```

This will install FastAPI, scikit-learn, XGBoost, pandas, and everything else the pipeline needs. TensorFlow is handled separately — see the note below.

> **Note on TensorFlow:** The LSTM model requires TensorFlow 2.21, which only works reliably on Python 3.12. A pre-configured virtual environment called `lstm_env` is included in the project. You do not need to set it up manually — just point to it when starting the server (see the next section).

---

## Setting up the frontend

In a separate terminal:

```
cd Source_Code/frontend
npm install
```

That is all. The `npm install` step may take a minute or two the first time.

---

## Starting the application

You need two terminals running simultaneously — one for the API server, one for the dashboard.

**Terminal 1 — API server:**

If you want full functionality including LSTM predictions:
```
C:\path\to\lstm_env\Scripts\python.exe -m uvicorn service2_api.main:app --port 8000
```

If you only need Random Forest and XGBoost (simpler setup):
```
uvicorn service2_api.main:app --reload --port 8000
```

To check it is running, open `http://localhost:8000/health` in your browser. You should get a short JSON response showing the server status and the last time predictions were generated.

**Terminal 2 — Dashboard:**

```
cd Source_Code/frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## Using the dashboard

When you open the dashboard, you will see several sections. Here is what each one does.

### Health Advisory

This is the first thing at the top of the page. It shows a simple child illustration alongside a plain-English health message based on the current PM2.5 reading. When air quality is good, the child looks happy. When pollution rises above the safe threshold, the illustration shows a face mask and a warning. The advice updates automatically as conditions change.

### Current AQI

The circular gauge shows the most recent sensor reading — the actual measured PM2.5 value, not a model estimate. Below the gauge you can see the LSTM model's prediction for the same time window, which gives you a second reference point. Both values include the AQI category (Good, Moderate, Unhealthy, etc.) with colour coding.

The sensor timestamp is displayed in Tashkent local time (UTC+5). If the timestamp looks a little behind the current clock, it simply means the pipeline has not been refreshed yet in the last hour — the reading is still valid.

### Tashkent Map

An interactive map showing the two sensor locations in the city — the US Embassy compound in Yunusabad and the Sputnik-4 station in Mirzo Ulugbek district. Each marker shows the current PM2.5 reading inside a coloured circle. Click any marker to see more detail. The shaded area over the city represents the approximate pollution coverage zone.

### Historical PM2.5

A time-series chart of past measurements. Use the filter buttons at the top right to switch between Yesterday, 3 Days, 7 Days, and 30 Days. The data combines real sensor readings with CAMS satellite estimates to fill any gaps in coverage.

### PM2.5 Forecast

This is the main forecast chart. It shows three lines:

- **Green dashed** — Random Forest prediction
- **Yellow dashed** — XGBoost prediction
- **Orange solid** — LSTM No Lags prediction (the primary model)

You can choose the forecast window: 24 hours, 3 days, or 7 days. To generate a fresh forecast with the latest data, click the **Run Forecast** button. A progress bar will walk through the four pipeline steps — fetching data, preprocessing, evaluating, and forecasting. The whole process takes about 60 to 90 seconds.

One thing worth knowing: the Random Forest and XGBoost lines tend to flatten out after about 3 days. This is expected behaviour, not a bug. Both models rely on rolling averages of past PM2.5 values, and once the forecast window extends beyond 72 hours, those rolling averages stabilise and the predictions converge to a near-constant value. The LSTM model does not have this limitation because it was trained without lag features — it uses a sliding 48-hour window and time-of-day patterns instead, which is why its 7-day forecast continues to show daily variation.

### Model Comparison

A small table showing how each model performed on the held-out test set. The key metric is RMSE (root mean squared error) — lower is better. All three models score between 7.2 and 7.4 µg/m³, which means typical prediction errors are in the 3–5 µg/m³ range.

### Feature Importance and Monthly Averages

The feature importance chart ranks the input variables by how much the XGBoost model relies on them. The monthly bar chart shows how PM2.5 levels change across seasons — winter months are significantly worse due to coal heating and temperature inversions.

---

## Refreshing data manually

If you prefer to run the pipeline from the terminal rather than through the dashboard button:

```
# Fetch the latest WAQI reading
python fetch_data.py

# Rebuild the processed dataset
python preprocess.py

# Re-evaluate models on the test set
python evaluate.py

# Generate a new 7-day forecast
python predict.py --hours 168
```

Run these in order, from inside the `Source_Code/backend` folder. Use the lstm_env Python executable if you want LSTM output.

---

## If something goes wrong

**Dashboard says "API server is not running"**
The uvicorn server is not started or crashed. Go back to Terminal 1 and start it again.

**LSTM values are missing or the forecast falls back to XGBoost**
The server is running with the standard Python environment, not lstm_env. Restart uvicorn using the lstm_env path shown above.

**The map tiles are not loading**
This is a network issue — the map tiles come from OpenStreetMap. Check your internet connection.

**"No forecast available" on the chart**
This means `predictions.json` either does not exist or has no forecast data yet. Click the Run Forecast button or run `predict.py` manually.

**UnicodeEncodeError on Windows**
This can happen in the default Windows terminal with certain print statements. Switch to Git Bash or Windows Terminal, which handle Unicode correctly.

---

## API reference

The backend exposes a simple REST API at `http://localhost:8000`. These endpoints are used internally by the dashboard but can also be queried directly for testing.

| Endpoint | What it returns |
|----------|-----------------|
| `GET /health` | Server status, last update time, forecast model info |
| `GET /aqi` | Current PM2.5 from sensor and LSTM forecast |
| `GET /predictions?days=7` | Historical actual vs predicted values |
| `GET /forecast?hours=168` | 7-day forecast arrays for all three models |
| `GET /metrics` | RMSE, MAE, R² for each model |
| `GET /feature-importance` | Top 15 feature importance scores |
| `GET /monthly` | Monthly average PM2.5 by calendar month |
| `POST /refresh-forecast?hours=168` | Starts the full pipeline in the background |
| `GET /refresh-status` | Current pipeline step and progress message |

---

*This manual covers everything needed to run and use the application. If you encounter an issue not listed here, check that both services are running and that the lstm_env Python path is correct for your machine.*
