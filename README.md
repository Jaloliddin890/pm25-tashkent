# PM2.5 Air Quality Forecasting — Tashkent

A machine learning system that forecasts PM2.5 air pollution levels in Tashkent, Uzbekistan. Combines real sensor data with three ML models — Random Forest, XGBoost, and LSTM — and presents everything through a live React dashboard.

Built as a BTEC Level 6 Unit 2 Independent Project.

---

## What it does

- Fetches hourly PM2.5 readings from the WAQI sensor network (Tashkent Chilanzar station)
- Combines sensor data with CAMS satellite reanalysis to cover historical gaps
- Trains three forecasting models and evaluates them on a held-out test set
- Generates a 7-day forecast with all three models shown simultaneously
- Serves everything through a FastAPI backend and displays it in a React dashboard

---

## Model performance

| Model | RMSE | MAE | R² |
|-------|------|-----|----|
| Random Forest | 7.24 | 3.44 | 0.915 |
| XGBoost | 7.38 | 3.64 | 0.912 |
| **LSTM No Lags** | **7.34** | **3.96** | **0.912** |

All three models were trained on ~17,000 hourly observations (January 2024 – June 2026). The LSTM model was retrained without lag and rolling features — this reduced RMSE by 37% compared to the original LSTM, because the model learned true temporal patterns from the raw 48-hour input window rather than relying on engineered shortcuts.

---

## Dashboard

The dashboard shows:

- **Health Advisory** — a child illustration with plain-English advice that changes with AQI level (happy face when air is clean, mask when it is not)
- **Current AQI** — latest sensor reading alongside the LSTM forecast for the same hour
- **Tashkent Map** — interactive Leaflet map with coloured PM2.5 markers at both sensor locations
- **Historical chart** — actual measurements going back up to 30 days
- **Forecast chart** — three model lines for up to 7 days ahead
- **Model comparison** — RMSE, MAE, R² for all three models
- **Feature importance** — top 15 predictors ranked by XGBoost importance score
- **Monthly averages** — seasonal pollution patterns from 2024 to present

All times are shown in Tashkent local time (UTC+5).

---

## Project structure

```
pm25_project/
├── service1/               Python ML pipeline
│   ├── fetch_data.py       Pulls latest WAQI readings
│   ├── preprocess.py       Cleans data and engineers features
│   ├── evaluate.py         Runs all models on test set, builds predictions.json
│   ├── predict.py          Generates 7-day forecast for all three models
│   ├── train_models.py     Trains Random Forest and XGBoost
│   ├── train_lstm_nolags.py  Trains the LSTM (no lag features)
│   ├── models/             Saved model files (.pkl, .keras, .json)
│   └── data/               Processed CSVs and feature config
├── service2_api/           FastAPI REST server
│   ├── main.py
│   ├── routes.py           9 endpoints
│   └── state.py
└── dashboard/              React frontend
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/     AQIGauge, ForecastChart, TashkentMap, HealthAdvisory, ...
```

---

## Getting started

**Requirements:** Python 3.12, Node.js 18+

### Backend

```bash
cd service1
pip install -r requirements.txt
```

Run the pipeline to generate predictions:

```bash
python fetch_data.py
python preprocess.py
python evaluate.py
python predict.py --hours 168
```

Start the API server:

```bash
uvicorn service2_api.main:app --port 8000
```

> For LSTM predictions, use the `lstm_env` Python 3.12 environment with TensorFlow 2.21 installed.

### Frontend

```bash
cd dashboard
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Data sources

| Source | Coverage | Used for |
|--------|----------|----------|
| US Embassy sensor (OpenAQ #25916) | Jan 2024 – Mar 2025 | Training data |
| Sputnik-4 sensor (OpenAQ #13465748) | Oct 2025 – Jan 2026 | Training data |
| CAMS reanalysis (Open-Meteo) | All periods | Gap filling + weather features |
| WAQI Chilanzar station | Real-time | Live dashboard readings |

Sensor data covers 54% of the dataset; CAMS fills the remaining 46%. Synthetic interpolation was used for short transition gaps but excluded from model training.

---

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Server status |
| `GET /aqi` | Current PM2.5 — sensor reading + LSTM forecast |
| `GET /predictions?days=7` | Historical actual vs predicted |
| `GET /forecast?hours=168` | 7-day forecast for all three models |
| `GET /metrics` | RMSE, MAE, R² per model |
| `GET /feature-importance` | Top 15 feature importance scores |
| `GET /monthly` | Monthly average PM2.5 |
| `POST /refresh-forecast?hours=168` | Trigger full pipeline update |
| `GET /refresh-status` | Pipeline progress |

---

## Notes

- `random_forest.pkl` is excluded from this repository (107 MB, exceeds GitHub's file limit). Regenerate it by running `python service1/train_models.py`.
- `node_modules/` and generated output files are also excluded. See `.gitignore`.
- The WAQI API token is embedded in `fetch_data.py`. Replace it with your own if you fork this project.

---

*Jaloloddin Temirov — Pearson BTEC Level 6, Unit 2 Independent Project, 2026*
