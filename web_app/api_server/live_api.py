"""
live_api.py — Fetch live market data cho forecast mode (date > max_hist)
=========================================================================
Được gọi bởi main.py khi ngày cần dự báo vượt quá dữ liệu lịch sử.
"""

import os, time
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

ENTSOE_KEY = os.getenv("ENTSOE_API_KEY", "")
GIE_KEY    = os.getenv("GIE_API_KEY", "")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(BASE_DIR, "../data_pipeline/daily_features_data.csv")

ENTSOE_CODES = {
    "DE": "DE_LU", "DK": "DK_1", "ES": "ES",
    "FR": "FR",    "IT": "IT_NORD", "PL": "PL",
}

RENEWABLE_TYPES = [
    "Biomass", "Geothermal", "Hydro Run-of-river and poundage",
    "Hydro Water Reservoir", "Other renewable", "Solar",
    "Wind Offshore", "Wind Onshore",
]


# ═════════════════════════════════════════════════════════════════════════════
def _fetch_entsoe_latest(country_code: str) -> dict:
    """Lấy Load + Renewables hôm qua từ ENTSO-E."""
    if os.getenv("RENDER") or os.getenv("VERCEL"):
        return {}
    if not ENTSOE_KEY:
        return {}
    try:
        from entsoe import EntsoePandasClient
        client = EntsoePandasClient(api_key=ENTSOE_KEY)

        end   = pd.Timestamp.now(tz="Europe/Brussels")
        start = end - pd.Timedelta(days=2)

        entsoe_code = ENTSOE_CODES.get(country_code, country_code)

        load_total = 0.0
        renew_total = 0.0

        try:
            load = client.query_load(entsoe_code, start=start, end=end)
            if isinstance(load, pd.DataFrame):
                load = load.iloc[:, 0]
            load_total = float(load.mean())
        except Exception as e:
            print(f"  [live] Load error {country_code}: {e}")

        try:
            gen = client.query_generation(entsoe_code, start=start, end=end)
            if isinstance(gen.columns, pd.MultiIndex):
                gen.columns = [" ".join(c).strip() for c in gen.columns]
            for rtype in RENEWABLE_TYPES:
                matched = [c for c in gen.columns if rtype.lower() in c.lower()
                          and "consumption" not in c.lower()]
                for col in matched:
                    renew_total += float(gen[col].fillna(0).mean())
        except Exception as e:
            print(f"  [live] Generation error {country_code}: {e}")

        return {"Load_MW": load_total, "Renewables_MW": renew_total}

    except Exception as e:
        print(f"  [live] ENTSO-E error: {e}")
        return {}


def _fetch_yfinance_latest() -> dict:
    """Lấy giá đóng cửa gần nhất: TTF, Brent."""
    tickers = {"TTF=F": "TTF_Gas_Price", "BZ=F": "Brent_Oil_Price"}
    results = {}
    
    # Try fetching with strict 3-second timeout to prevent Render/Vercel hanging
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    for ticker, name in tickers.items():
        try:
            # yfinance uses the session, but we also patch requests directly if it hangs
            # using timeout inside the ticker if possible, but yfinance doesn't easily support timeout
            # To be safe, we just skip yfinance if on Render to avoid 3-minute hangs
            if os.getenv("RENDER") or os.getenv("VERCEL"):
                return {}
            hist = yf.Ticker(ticker, session=session).history(period="5d")
            if not hist.empty:
                results[name] = float(hist["Close"].iloc[-1])
        except Exception as e:
            print(f"  [live] yfinance {name}: {e}")
    return results


def _fetch_gie_latest() -> float:
    """Lấy EU Gas Storage % mới nhất từ GIE."""
    if not GIE_KEY:
        return 0.0
    try:
        headers = {"x-key": GIE_KEY}
        res = requests.get(
            "https://agsi.gie.eu/api?type=eu&size=3",
            headers=headers, timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if data.get("data"):
                full = float(data["data"][0]["full"])
                return (full - 65.0) / 100.0   # Simplified anomaly
    except Exception as e:
        print(f"  [live] GIE error: {e}")
    return 0.0


def _get_fallback_from_csv(country: str) -> dict:
    """Lấy giá trị cuối cùng từ daily_features_data.csv làm fallback."""
    try:
        df = pd.read_csv(DATA_PATH)
        df["Date"] = pd.to_datetime(df["Date"])
        row = df[df["Country"] == country].sort_values("Date").iloc[-1]
        return {
            "TTF_Gas_Price":             float(row.get("TTF_Gas_Price", 40.0)),
            "Coal_Price":                float(row.get("Coal_Price", 100.0)),
            "EU_ETS_Price":              float(row.get("EU_ETS_Price", 70.0)),
            "Brent_Oil_Price":           float(row.get("Brent_Oil_Price", 80.0)),
            "Residual_Load_Normalized":  float(row.get("Residual_Load_Normalized", 0.5)),
            "EU_Gas_Storage_Anomaly":    float(row.get("EU_Gas_Storage_Anomaly", 0.0)),
        }
    except Exception:
        return {
            "TTF_Gas_Price": 40.0, "Coal_Price": 100.0, "EU_ETS_Price": 70.0,
            "Brent_Oil_Price": 80.0, "Residual_Load_Normalized": 0.5,
            "EU_Gas_Storage_Anomaly": 0.0,
        }


def get_live_features(country: str) -> dict:
    """
    Hàm tổng hợp được gọi bởi main.py khi cần features live.
    Thứ tự ưu tiên: Live API → Fallback từ CSV cuối cùng.
    """
    print(f"  [live] Fetching live features for {country}...")

    # Lấy fallback trước (luôn có)
    result = _get_fallback_from_csv(country)

    # Ghi đè bằng live data nếu có
    live_macro = _fetch_yfinance_latest()
    if live_macro.get("TTF_Gas_Price"):
        result["TTF_Gas_Price"] = live_macro["TTF_Gas_Price"]
    if live_macro.get("Brent_Oil_Price"):
        result["Brent_Oil_Price"] = live_macro["Brent_Oil_Price"]

    # ENTSO-E: Load + Renewables
    import json
    scaler_path = os.path.join(BASE_DIR, "../ai_model/country_scalers.json")
    scalers = {}
    if os.path.exists(scaler_path):
        with open(scaler_path) as f:
            scalers = json.load(f)

    entsoe_data = _fetch_entsoe_latest(country)
    if entsoe_data.get("Load_MW", 0) > 0:
        residual = entsoe_data["Load_MW"] - entsoe_data.get("Renewables_MW", 0)
        s = scalers.get(country, {"min": 0, "max": residual * 2})
        denom = s["max"] - s["min"]
        if denom > 0:
            result["Residual_Load_Normalized"] = float(
                np.clip((residual - s["min"]) / denom, 0, 1)
            )

    # GIE Gas Storage
    gas_anomaly = _fetch_gie_latest()
    result["EU_Gas_Storage_Anomaly"] = gas_anomaly

    return result


def fetch_live_actual_prices(country_code: str, start_date_str: str, days: int = 7) -> dict:
    """Lấy mảng Day-ahead Prices thật từ ENTSO-E cho khoảng thời gian tương lai."""
    # Vercel/Render IPs get heavily rate-limited or blocked, causing 2-minute hangs. Fast-fail for demos.
    if os.getenv("RENDER") or os.getenv("VERCEL"):
        return {}
    if not ENTSOE_KEY:
        return {}
    try:
        from entsoe import EntsoePandasClient
        client = EntsoePandasClient(api_key=ENTSOE_KEY)
        
        start = pd.Timestamp(start_date_str, tz="Europe/Brussels")
        end = start + pd.Timedelta(days=days)
        entsoe_code = ENTSOE_CODES.get(country_code, country_code)
        
        prices = client.query_day_ahead_prices(entsoe_code, start=start, end=end)
        
        if isinstance(prices, (pd.Series, pd.DataFrame)):
            if isinstance(prices, pd.DataFrame):
                prices = prices.iloc[:, 0]
            prices_daily = prices.resample('D').mean()
            
            result = {}
            for date_idx, val in prices_daily.items():
                date_key = date_idx.strftime("%Y-%m-%d")
                if not pd.isna(val):
                    result[date_key] = float(val)
            return result
    except Exception as e:
        print(f"  [live] fetch_live_actual_prices error: {e}")
    return {}


if __name__ == "__main__":
    print("Test live_api.py:")
    for c in ["DE", "FR"]:
        data = get_live_features(c)
        print(f"\n{c}:")
        for k, v in data.items():
            print(f"  {k}: {v}")
