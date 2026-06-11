================================================================
  PM2.5 AIR QUALITY FORECASTING — TASHKENT
  BTEC Level 6 Unit 2: Independent Project
================================================================

PROJECT TITLE  : Forecasting Air Pollution (PM2.5) in Tashkent
                 Using Machine Learning
AUTHOR         : Jaloloddin Temirov
INSTITUTION    : Pearson BTEC Level 6
DATE           : June 2026

----------------------------------------------------------------
PROGRAMMING LANGUAGES
----------------------------------------------------------------
  Python 3.12    — ML pipeline, data processing, API
  JavaScript     — React frontend (dashboard)
  HTML / CSS     — Dashboard styling (via Tailwind CSS)

----------------------------------------------------------------
FRAMEWORKS & TECHNOLOGIES
----------------------------------------------------------------
  Backend (ML + API):
    - scikit-learn 1.x       Random Forest model
    - XGBoost 2.x            Gradient boosting model
    - TensorFlow 2.21.0      LSTM neural network
    - FastAPI 0.x            REST API server
    - Uvicorn                ASGI server
    - APScheduler            Background task scheduler
    - pandas, numpy          Data processing
    - requests               WAQI API calls

  Frontend:
    - React 18 + Vite        UI framework
    - Tailwind CSS           Styling
    - Recharts               Charts (historical + forecast)
    - Leaflet / react-leaflet Interactive map

  Data Sources:
    - OpenAQ API             US Embassy sensor (historical)
    - WAQI API               Real-time Tashkent sensor
    - Open-Meteo CAMS        Weather + air quality reanalysis

----------------------------------------------------------------
DATABASE
----------------------------------------------------------------
  Type: Flat-file (CSV)  — No relational database used.

  Key files in Source_Code/database/:
    tashkent_pm25_weather.csv  — Raw combined dataset (~21,400 rows)
    processed.csv              — Feature-engineered dataset
    train.csv                  — Training split (80%)
    test.csv                   — Test split (20%)
    feature_cols.json          — Feature column names

----------------------------------------------------------------
QUICK START GUIDE
----------------------------------------------------------------

STEP 1 — Install Python environments
  # Main environment (Python 3.x)
  pip install -r Source_Code/backend/requirements.txt

  # LSTM environment (Python 3.12 required for TensorFlow)
  # Already set up at: lstm_env/ (included separately)

STEP 2 — Run the data pipeline (optional — data already included)
  cd Source_Code/backend
  python fetch_data.py       # Fetch latest WAQI data
  python preprocess.py       # Feature engineering
  python evaluate.py         # Generate predictions.json
  python predict.py          # Generate 7-day forecast

STEP 3 — Start the API server
  cd Source_Code/backend
  uvicorn service2_api.main:app --reload --port 8000

  NOTE: Use Python 3.12 (lstm_env) if LSTM predictions are needed:
  C:\path\to\lstm_env\Scripts\python.exe -m uvicorn service2_api.main:app --port 8000

STEP 4 — Start the dashboard
  cd Source_Code/frontend
  npm install
  npm run dev

  Open browser: http://localhost:5173

STEP 5 — View dashboard
  The dashboard will load with:
  - Current AQI (sensor + LSTM forecast)
  - 7-day forecast (3 models: RF, XGBoost, LSTM)
  - Interactive Tashkent map with AQI markers
  - Historical PM2.5 chart
  - Model performance comparison
  - Health Advisory card

----------------------------------------------------------------
MODELS INCLUDED (pre-trained)
----------------------------------------------------------------
  Source_Code/backend/models/
    random_forest.pkl       Random Forest (RMSE=7.24, R²=0.915)
    xgboost.json            XGBoost     (RMSE=7.38, R²=0.912)
    lstm_nolags.keras       LSTM No Lags (RMSE=7.34, R²=0.912)
    lstm_nolags_scaler.pkl  Feature scaler for LSTM

----------------------------------------------------------------
SYSTEM REQUIREMENTS
----------------------------------------------------------------
  OS       : Windows 10/11, macOS, or Linux
  Python   : 3.12 (for LSTM), 3.9+ (for RF/XGBoost)
  Node.js  : 18+
  RAM      : 4 GB minimum, 8 GB recommended
  Storage  : ~500 MB (including models and dataset)

================================================================
END OF README
================================================================
