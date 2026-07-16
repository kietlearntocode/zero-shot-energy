import json
import os
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from live_api import get_live_dashboard_data

app = FastAPI(title="Anonymous Weekly Forecaster API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = "../ai_model/weekly_xgb.json"
DATA_PATH = "../data_pipeline/weekly_zero_shot_data.csv"
SCALER_PATH = "../ai_model/country_scalers.json"

model = None
df = None
scalers = {}

FEATURES = [
    "EU_Residual_Load_Normalized",
    "TTF_Gas_Price",
    "Coal_Price",
    "EU_ETS_Price",
    "Brent_Oil_Price",
    "EU_Gas_Storage_Anomaly",
    "Price_Lag1",
    "Price_Lag2",
    "Residual_Load_Normalized_Lag1",
    "Residual_Load_Normalized_Lag2"
]

@app.on_event("startup")
def load_assets():
    global model, df
    if os.path.exists(MODEL_PATH):
        model = xgb.XGBRegressor()
        model.load_model(MODEL_PATH)
        print("Loaded Weekly XGBoost Model")
    else:
        print("Model file not found!")

    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
        df = df.sort_values(by=['Country', 'Datetime'])
        print("Loaded Weekly Historical Data")
        
    if os.path.exists(SCALER_PATH):
        with open(SCALER_PATH, "r") as f:
            scalers.update(json.load(f))
        print(f"Loaded Residual Load Scalers for {len(scalers)} countries")

@app.get("/api/countries")
def get_countries():
    return list(scalers.keys())

@app.get("/api/fetch_live")
def fetch_live_data(country: str = "DE"):
    try:
        data = get_live_dashboard_data(country)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/historical/EU")
def get_historical_eu(weeks: int = 52):
    if df is None or df.empty:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    df_sorted = df.sort_values("Datetime")
    df_sorted["Date"] = df_sorted["Datetime"].dt.date
    recent = df_sorted.tail(weeks)
    
    return {
        "dates": recent["Date"].astype(str).tolist(),
        "prices": recent["Real_Wholesale_Price_EUR"].tolist(),
        "residual_load_norm": recent["EU_Residual_Load_Normalized"].tolist(),
        "gas_price": recent["TTF_Gas_Price"].tolist(),
        "coal_price": recent["Coal_Price"].tolist(),
        "ets_price": recent["EU_ETS_Price"].tolist(),
        "oil_price": recent["Brent_Oil_Price"].tolist(),
        "gas_anomaly": recent["EU_Gas_Storage_Anomaly"].tolist(),
    }

class PredictRequest(BaseModel):
    country_code: str
    eu_load_mw: float
    eu_renewables_mw: float
    ttf_gas_price: float
    coal_price: float
    eu_ets_price: float
    brent_oil_price: float
    eu_gas_storage_anomaly: float

@app.post("/api/predict_weekly")
def predict_price(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
        
    country_scaler = scalers.get(req.country_code)
    if not country_scaler:
        raise HTTPException(status_code=400, detail=f"No scaler found for {req.country_code}")
        
    # Tính Tải dư và Chuẩn hóa
    residual_load = req.eu_load_mw - req.eu_renewables_mw
    norm_load = (residual_load - country_scaler["min"]) / (country_scaler["max"] - country_scaler["min"])
    norm_load = max(0.0, min(1.0, norm_load))
            
    # Lấy tự động Lag Features từ Lịch sử
    price_lag1 = 40.0
    price_lag2 = 40.0
    res_lag1 = 0.5
    res_lag2 = 0.5
    
    if df is not None:
        country_df = df[df["Country"] == req.country_code]
        if len(country_df) > 0:
            last_row = country_df.iloc[-1]
            price_lag1 = float(last_row["Real_Wholesale_Price_EUR"])
            price_lag2 = float(last_row["Price_Lag1"])
            res_lag1 = float(last_row["EU_Residual_Load_Normalized"])
            res_lag2 = float(last_row["Residual_Load_Normalized_Lag1"])
            
    X = pd.DataFrame([{
        "EU_Residual_Load_Normalized": norm_load,
        "TTF_Gas_Price": req.ttf_gas_price,
        "Coal_Price": req.coal_price,
        "EU_ETS_Price": req.eu_ets_price,
        "Brent_Oil_Price": req.brent_oil_price,
        "EU_Gas_Storage_Anomaly": req.eu_gas_storage_anomaly,
        "Price_Lag1": price_lag1,
        "Price_Lag2": price_lag2,
        "Residual_Load_Normalized_Lag1": res_lag1,
        "Residual_Load_Normalized_Lag2": res_lag2
    }])
    
    y_pred = model.predict(X)[0]
    
    return {
        "predicted_next_week_price_eur": float(y_pred)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
