"""
main.py — FastAPI Daily Forecast Server
========================================
Endpoints:
  GET /api/countries              → ["DE","DK","ES","FR","IT","PL"]
  GET /api/date_range?country=DE  → {min_date, max_date, max_forecast_date}
  GET /api/forecast?country=DE&date=2025-06-01  → 7-day rolling forecast
"""

import json, os
import numpy as np
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from live_api import get_live_features, fetch_live_actual_prices

app = FastAPI(title="EU Electricity Daily Forecast API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE, "../ai_model/daily_xgb.json")
DATA_PATH   = os.path.join(BASE, "../data_pipeline/daily_features_data.csv")
SCALER_PATH = os.path.join(BASE, "../ai_model/country_scalers.json")
PROFILE_PATH = os.path.join(BASE, "../data_pipeline/country_profiles.json")

FEATURE_COLS = [
    # Macro (10 biến: Lag 1, Lag 2)
    "TTF_Gas_Lag1", "TTF_Gas_Lag2",
    "Coal_Lag1", "Coal_Lag2",
    "EU_ETS_Lag1", "EU_ETS_Lag2",
    "Brent_Oil_Lag1", "Brent_Oil_Lag2",
    "EU_Gas_Storage_Lag1", "EU_Gas_Storage_Lag2",
    # Cyclical (4)
    "DayOfWeek_Sin", "DayOfWeek_Cos", "Month_Sin", "Month_Cos",
    # Lag price (5)
    "Price_Lag1", "Price_Lag2", "Price_Lag7", "Price_Lag14", "Price_Lag30",
    # Lag load (3)
    "Load_Lag1", "Load_Lag2", "Load_Lag7",
    # Rolling stats (3)
    "Price_Roll7_Mean", "Price_Roll7_Std", "Load_Roll7_Mean",
    # Country Profiles (3)
    "Country_Avg_Load", "Country_Avg_Residual_Load", "Country_Avg_Price"
]

COUNTRIES = [
    "BE", "CZ", "DE", "DK", "ES", "FI", "FR", "GB", 
    "HU", "IE", "IT", "NL", "NO", "PL", "PT", "SE", "SK"
]

# ── Global state ──────────────────────────────────────────────────────────────
model   = None
df_feat = None
scalers = {}
country_profiles_dict = {}


@app.on_event("startup")
def load_assets():
    global model, df_feat, scalers, country_profiles_dict

    if os.path.exists(MODEL_PATH):
        model = xgb.XGBRegressor()
        model.load_model(MODEL_PATH)
        print(f"[OK] Model loaded: {MODEL_PATH}")
    else:
        print(f"[WARN] Model not found: {MODEL_PATH} — run train_daily.py first")

    if os.path.exists(DATA_PATH):
        df_feat = pd.read_csv(DATA_PATH, low_memory=True)
        df_feat["Date"] = pd.to_datetime(df_feat["Date"])
        df_feat = df_feat.sort_values(["Country", "Date"])
        print(f"[OK] Data loaded: {len(df_feat):,} rows")
    else:
        print(f"[WARN] Data not found: {DATA_PATH} — run build_daily_features.py first")

    if os.path.exists(SCALER_PATH):
        with open(SCALER_PATH) as f:
            scalers.update(json.load(f))
        print(f"[OK] Scalers loaded: {list(scalers.keys())}")

    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH) as f:
            country_profiles_dict.update(json.load(f))
        print(f"[OK] Country Profiles loaded: {len(country_profiles_dict)} countries")
    else:
        print(f"[WARN] Profiles not found: {PROFILE_PATH}")


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════
def _cyclical(date: pd.Timestamp) -> dict:
    dow = date.dayofweek
    mon = date.month
    return {
        "DayOfWeek_Sin": float(np.sin(2 * np.pi * dow / 7)),
        "DayOfWeek_Cos": float(np.cos(2 * np.pi * dow / 7)),
        "Month_Sin":     float(np.sin(2 * np.pi * mon / 12)),
        "Month_Cos":     float(np.cos(2 * np.pi * mon / 12)),
    }


def _get_row(country: str, date: pd.Timestamp) -> dict:
    """Lấy 1 row từ daily_features_data cho (country, date) dạng dictionary."""
    if df_feat is None:
        return {}
    mask = (df_feat["Country"] == country) & (df_feat["Date"] == date)
    rows = df_feat[mask]
    return rows.iloc[0].to_dict() if len(rows) > 0 else {}


def _build_feature_vector(country: str, target_date: pd.Timestamp,
                           historical_prices: dict = None) -> dict | None:
    """
    Xây dựng vector features để predict giá ngày target_date.
    Features là thông tin của ngày T-1 (hôm trước target_date).
    """
    if historical_prices is None:
        historical_prices = {}
        
    prev_date = target_date - timedelta(days=1)

    # ── Macro C1: Lấy từ T-1, T-2 ──────────────────────────────────────────
    macro_row_t1 = _get_row(country, target_date - timedelta(days=1))
    macro_row_t2 = _get_row(country, target_date - timedelta(days=2))

    def _safe_get(row, key):
        val = row.get(key)
        if val is None or pd.isna(val):
            return None
        return float(val)

    macro = {
        "TTF_Gas_Lag1":          _safe_get(macro_row_t1, "TTF_Gas_Price"),
        "TTF_Gas_Lag2":          _safe_get(macro_row_t2, "TTF_Gas_Price"),
        "Coal_Lag1":             _safe_get(macro_row_t1, "Coal_Price"),
        "Coal_Lag2":             _safe_get(macro_row_t2, "Coal_Price"),
        "EU_ETS_Lag1":           _safe_get(macro_row_t1, "EU_ETS_Price"),
        "EU_ETS_Lag2":           _safe_get(macro_row_t2, "EU_ETS_Price"),
        "Brent_Oil_Lag1":        _safe_get(macro_row_t1, "Brent_Oil_Price"),
        "Brent_Oil_Lag2":        _safe_get(macro_row_t2, "Brent_Oil_Price"),
        "EU_Gas_Storage_Lag1":   _safe_get(macro_row_t1, "EU_Gas_Storage_Anomaly"),
        "EU_Gas_Storage_Lag2":   _safe_get(macro_row_t2, "EU_Gas_Storage_Anomaly"),
    }

    # ── Cyclical: tính từ target_date ────────────────────────────────────
    cyc = _cyclical(target_date)

    # ── Lag features ─────────────────────────────────────────────────────
    def _price(date):
        if date in historical_prices:
            return float(historical_prices[date])
        r = _get_row(country, date)
        if r and not pd.isna(r.get("Real_Wholesale_Price_EUR")):
            return float(r["Real_Wholesale_Price_EUR"])
        return None

    def _load(date):
        r = _get_row(country, date)
        if r and not pd.isna(r.get("Residual_Load_Normalized")):
            return float(r["Residual_Load_Normalized"])
        return None

    # Lấy các lag prices 
    price_lag1  = _price(target_date - timedelta(days=1))
    price_lag2  = _price(target_date - timedelta(days=2))
    price_lag7  = _price(target_date - timedelta(days=7))
    price_lag14 = _price(target_date - timedelta(days=14))
    price_lag30 = _price(target_date - timedelta(days=30))

    load_lag1  = _load(target_date - timedelta(days=1))
    load_lag2  = _load(target_date - timedelta(days=2))
    load_lag7  = _load(target_date - timedelta(days=7))

    roll_prices = [p for p in [_price(target_date - timedelta(days=d)) for d in range(1, 8)] if p is not None]
    roll7_mean = float(np.mean(roll_prices)) if len(roll_prices) > 0 else None
    roll7_std  = float(np.std(roll_prices)) if len(roll_prices) > 0 else None

    roll_loads = [l for l in [_load(target_date - timedelta(days=d)) for d in range(1, 8)] if l is not None]
    load_roll7_mean = float(np.mean(roll_loads)) if len(roll_loads) > 0 else None

    lags = {
        "Price_Lag1": price_lag1, "Price_Lag2": price_lag2,
        "Price_Lag7": price_lag7, "Price_Lag14": price_lag14,
        "Price_Lag30": price_lag30,
        "Load_Lag1": load_lag1, "Load_Lag2": load_lag2, "Load_Lag7": load_lag7,
        "Price_Roll7_Mean": roll7_mean, "Price_Roll7_Std": roll7_std,
        "Load_Roll7_Mean": load_roll7_mean,
    }

    # ── Country Profiles ──────────────────────────────────────────────────
    c_prof = country_profiles_dict.get(country, {})
    prof = {
        "Country_Avg_Load": c_prof.get("Country_Avg_Load", 0.0),
        "Country_Avg_Residual_Load": c_prof.get("Country_Avg_Residual_Load", 0.0),
        "Country_Avg_Price": c_prof.get("Country_Avg_Price", 0.0),
    }

    return {**macro, **cyc, **lags, **prof}


# ═════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═════════════════════════════════════════════════════════════════════════════
@app.get("/api/countries")
def get_countries():
    if scalers:
        return sorted(scalers.keys())
    return COUNTRIES


@app.get("/api/date_range")
def get_date_range(country: str = Query("DE")):
    if df_feat is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    cdf = df_feat[df_feat["Country"] == country]
    if cdf.empty:
        raise HTTPException(status_code=404, detail=f"No data for {country}")

    max_date = cdf["Date"].max()
    min_date = cdf["Date"].min()
    max_forecast = max_date + timedelta(days=7)

    return {
        "country":            country,
        "min_date":           min_date.strftime("%Y-%m-%d"),
        "max_date":           max_date.strftime("%Y-%m-%d"),
        "max_forecast_date":  max_forecast.strftime("%Y-%m-%d"),
    }


@app.get("/api/forecast")
def get_forecast(
    country: str = Query("DE", description="Country ISO-2"),
    date:    str = Query(...,   description="Start date YYYY-MM-DD"),
):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded — run train_daily.py")
    if df_feat is None:
        raise HTTPException(status_code=500, detail="Data not loaded — run build_daily_features.py")

    try:
        start_date = pd.Timestamp(date)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format — use YYYY-MM-DD")

    if country not in COUNTRIES:
        raise HTTPException(status_code=400, detail=f"Country must be one of {COUNTRIES}")

    # Giới hạn max forecast
    if df_feat is not None:
        cdf = df_feat[df_feat["Country"] == country]
        max_hist = cdf["Date"].max() if not cdf.empty else pd.Timestamp("2025-12-31")
    else:
        max_hist = pd.Timestamp("2025-12-31")

    max_allowed = max_hist + timedelta(days=7)
    if start_date > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Date too far in future. Max allowed: {max_allowed.strftime('%Y-%m-%d')}"
        )

    # ── Kéo Live Actual Prices nếu Tương Lai ───────────────────────────────
    live_actuals = {}
    if start_date > max_hist:
        live_actuals = fetch_live_actual_prices(country, start_date.strftime("%Y-%m-%d"), days=7)

    # ── Rolling 7-day forecast ─────────────────────────────────────────────
    results = []
    historical_prices = {}

    for i in range(7):
        forecast_date = start_date + timedelta(days=i)

        feat_vec = _build_feature_vector(country, forecast_date, historical_prices)
        if feat_vec is None:
            break

        X = pd.DataFrame([feat_vec])[FEATURE_COLS]
        predicted = float(model.predict(X)[0])

        # Lấy actual chỉ để hiển thị lên biểu đồ (đánh giá)
        actual_row = _get_row(country, forecast_date)
        actual = float(actual_row["Real_Wholesale_Price_EUR"]) if actual_row and not pd.isna(actual_row.get("Real_Wholesale_Price_EUR")) else None

        # Nếu không có trong CSV, cố lấy từ Live ENTSO-E
        if actual is None and start_date > max_hist:
            date_str = forecast_date.strftime("%Y-%m-%d")
            actual = live_actuals.get(date_str)

        results.append({
            "date":      forecast_date.strftime("%Y-%m-%d"),
            "weekday":   forecast_date.strftime("%A"),
            "predicted": round(predicted, 2),
            "actual":    round(actual, 2) if actual is not None else None,
            "inputs":    {k: round(float(v), 4) for k, v in feat_vec.items()},
        })

        # CHUNG MỘT CÔNG THỨC DUY NHẤT CHO MỌI NGÀY (Quá khứ hay Tương lai):
        # - Nếu ngày đó ĐÃ CÓ Giá Thực Tế (Actual) -> Gán Actual làm mồi.
        # - Nếu ngày đó CHƯA CÓ Giá Thực Tế (VD: T+2, T+3 tương lai) -> Gán Predicted làm mồi (Lag Forecast).
        historical_prices[forecast_date] = actual if actual is not None else predicted

    if not results:
        raise HTTPException(status_code=500, detail="Không thể tạo forecast")

    # Macro snapshot (từ ngày đầu tiên)
    inputs_snapshot = results[0]["inputs"] if results else {}

    return {
        "country":        country,
        "forecast_start": date,
        "mode":           "backtest" if results[0]["actual"] is not None else "forecast",
        "data_last_date": max_hist.strftime("%Y-%m-%d"),
        "forecast":       results,
        "macro_snapshot": {
            "TTF_Gas_Lag1":            inputs_snapshot.get("TTF_Gas_Lag1"),
            "Coal_Lag1":               inputs_snapshot.get("Coal_Lag1"),
            "EU_ETS_Lag1":             inputs_snapshot.get("EU_ETS_Lag1"),
            "Brent_Oil_Lag1":          inputs_snapshot.get("Brent_Oil_Lag1"),
            "Country_Avg_Residual_Load":inputs_snapshot.get("Country_Avg_Residual_Load"),
            "EU_Gas_Storage_Lag1":     inputs_snapshot.get("EU_Gas_Storage_Lag1"),
        }
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "data_loaded":  df_feat is not None,
        "countries":    COUNTRIES,
        "data_rows":    len(df_feat) if df_feat is not None else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
