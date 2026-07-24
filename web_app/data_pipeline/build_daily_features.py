"""
build_daily_features.py -- Feature Engineering for Daily XGBoost
=================================================================
Input : master_dataset_hourly.csv + recent_data.csv (optional)
Output: daily_features_data.csv + country_scalers.json

Features (21):
  C1 macro (6): TTF_Gas_Price, Coal_Price, EU_ETS_Price, Brent_Oil_Price,
                Residual_Load_Normalized, EU_Gas_Storage_Anomaly
  Cyclical (4): DayOfWeek_Sin/Cos, Month_Sin/Cos
  Lag price (6): Price_Lag1, Lag2, Lag7, Lag14, Lag30, Lag365
  Lag load  (3): Load_Lag1, Load_Lag7, Load_Lag14
  Rolling   (2): Price_Roll7_Mean, Price_Roll7_Std
Target: Next_Day_Price_EUR
"""

import os, json
import numpy as np
import pandas as pd

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV  = os.path.join(BASE_DIR, "web_master_dataset.csv")
RECENT_CSV  = os.path.join(BASE_DIR, "recent_data.csv")
OUTPUT_CSV  = os.path.join(BASE_DIR, "daily_features_data.csv")
SCALER_JSON = os.path.join(BASE_DIR, "../ai_model/country_scalers.json")

COUNTRIES = [
    "BE", "CZ", "DE", "DK", "ES", "FI", "FR", "GB", 
    "HU", "IE", "IT", "NL", "NO", "PL", "PT", "SE", "SK"
]

# Columns to aggregate from hourly -> daily
DAILY_AGG = {
    "Real_Wholesale_Price_EUR": "mean",
    "Load":                     "mean",
    "Renewables_MW":            "mean",
    "TTF_Gas_Price":            "mean",
    "Coal_Price":               "mean",
    "EU_ETS_Price":             "mean",
    "Brent_Oil_Price":          "mean",
    "EU_Gas_Storage_Anomaly":   "mean",
    "DayOfWeek_Sin":            "mean",
    "DayOfWeek_Cos":            "mean",
    "Month_Sin":                "mean",
    "Month_Cos":                "mean",
}


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


# =============================================================================
def load_and_merge() -> pd.DataFrame:
    """Load master CSV + recent_data.csv, filter 6 countries, merge."""
    print("[1] Loading data...")

    cols_needed = ["Country", "Datetime"] + list(DAILY_AGG.keys())

    # Master CSV (2018-2025)
    df_master = pd.read_csv(
        MASTER_CSV,
        usecols=lambda c: c in cols_needed,
        low_memory=True
    )
    df_master["Datetime"] = pd.to_datetime(df_master["Datetime"], utc=True)
    df_master = df_master[df_master["Country"].isin(COUNTRIES)]
    print(f"   Master: {len(df_master):,} rows")

    frames = [df_master]

    # Recent data (2026-present)
    if os.path.exists(RECENT_CSV):
        df_recent = pd.read_csv(RECENT_CSV, low_memory=True)
        df_recent["Datetime"] = pd.to_datetime(df_recent["Datetime"], utc=True)
        df_recent = df_recent[df_recent["Country"].isin(COUNTRIES)]
        available = [c for c in cols_needed if c in df_recent.columns]
        df_recent = df_recent[available]
        frames.append(df_recent)
        print(f"   Recent: {len(df_recent):,} rows")

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["Country", "Datetime"]).sort_values(["Country", "Datetime"])
    print(f"   Total : {len(df):,} rows")
    return df


# =============================================================================
def aggregate_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly -> daily mean."""
    print("[2] Aggregating hourly -> daily...")
    df["Date"] = df["Datetime"].dt.date

    agg_dict = {k: v for k, v in DAILY_AGG.items() if k in df.columns}
    df_daily = df.groupby(["Country", "Date"]).agg(agg_dict).reset_index()
    df_daily["Date"] = pd.to_datetime(df_daily["Date"])
    df_daily = df_daily.sort_values(["Country", "Date"])

    print(f"   Result: {len(df_daily):,} day-country rows")
    return df_daily


# =============================================================================
def compute_residual_load(df: pd.DataFrame) -> dict:
    """Residual_Load = Load - Renewables_MW, normalized per country (2018-2024)."""
    print("[3] Computing Residual Load + Normalizing...")
    df["Residual_Load"] = df["Load"] - df["Renewables_MW"]

    scalers = {}
    train_mask = df["Date"].dt.year <= 2024

    for country in COUNTRIES:
        cmask = (df["Country"] == country) & train_mask
        vals = df.loc[cmask, "Residual_Load"].dropna()
        rmin = float(vals.min()) if len(vals) else 0.0
        rmax = float(vals.max()) if len(vals) else 1.0
        scalers[country] = {"min": rmin, "max": rmax}

    def normalize(row):
        s = scalers.get(row["Country"], {"min": 0, "max": 1})
        denom = s["max"] - s["min"]
        if denom == 0:
            return 0.5
        return float(np.clip((row["Residual_Load"] - s["min"]) / denom, 0, 1))

    df["Residual_Load_Normalized"] = df.apply(normalize, axis=1)
    print(f"   Scalers computed for {len(scalers)} countries")
    return scalers


# =============================================================================
def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add all lag + rolling features per country."""
    print("[4] Adding lag + rolling features...")

    all_parts = []
    for country in COUNTRIES:
        cdf = df[df["Country"] == country].copy().sort_values("Date")
        price = cdf["Real_Wholesale_Price_EUR"].ffill().bfill()
        load  = cdf["Residual_Load_Normalized"].ffill().bfill()

        # Price lags
        cdf["Price_Lag1"]   = price.shift(1)
        cdf["Price_Lag2"]   = price.shift(2)
        cdf["Price_Lag7"]   = price.shift(7)
        cdf["Price_Lag14"]  = price.shift(14)
        cdf["Price_Lag30"]  = price.shift(30)

        # Macro lags (Lag 1, Lag 2) - ffill/bfill trước khi shift để tránh NaN
        ttf  = cdf["TTF_Gas_Price"].ffill().bfill()
        coal = cdf["Coal_Price"].ffill().bfill()
        ets  = cdf["EU_ETS_Price"].ffill().bfill()
        oil  = cdf["Brent_Oil_Price"].ffill().bfill()
        stor = cdf["EU_Gas_Storage_Anomaly"].ffill().bfill()

        cdf["TTF_Gas_Lag1"] = ttf.shift(1)
        cdf["TTF_Gas_Lag2"] = ttf.shift(2)
        cdf["Coal_Lag1"]    = coal.shift(1)
        cdf["Coal_Lag2"]    = coal.shift(2)
        cdf["EU_ETS_Lag1"]  = ets.shift(1)
        cdf["EU_ETS_Lag2"]  = ets.shift(2)
        cdf["Brent_Oil_Lag1"] = oil.shift(1)
        cdf["Brent_Oil_Lag2"] = oil.shift(2)
        cdf["EU_Gas_Storage_Lag1"] = stor.shift(1)
        cdf["EU_Gas_Storage_Lag2"] = stor.shift(2)

        # Load lags (Lag 1, 2, 7)
        cdf["Load_Lag1"]  = load.shift(1)
        cdf["Load_Lag2"]  = load.shift(2)
        cdf["Load_Lag7"]  = load.shift(7)

        # Rolling
        cdf["Price_Roll7_Mean"] = cdf["Price_Lag1"].rolling(7).mean()
        cdf["Price_Roll7_Std"]  = cdf["Price_Lag1"].rolling(7).std()
        cdf["Load_Roll7_Mean"]  = cdf["Load_Lag1"].rolling(7, min_periods=4).mean()

        all_parts.append(cdf)

    df_out = pd.concat(all_parts, ignore_index=True)
    print("   Lags OK: Price(1..365), Load(2/7/14), Macro(Lag2), Roll7Mean/Std")
    return df_out





# =============================================================================
def add_country_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Inject the 3 continuous profile features (Avg Load, Avg Residual Load, Avg Price)."""
    print("[5] Injecting Country Profiles...")
    profile_path = os.path.join(BASE_DIR, "country_profiles.json")
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Missing {profile_path}. Run build_country_profiles.py first.")
    
    with open(profile_path, "r") as f:
        profiles = json.load(f)
        
    def get_profile_val(country, key):
        return profiles.get(country, {}).get(key, 0.0)

    df["Country_Avg_Load"] = df["Country"].apply(lambda c: get_profile_val(c, "Country_Avg_Load"))
    df["Country_Avg_Residual_Load"] = df["Country"].apply(lambda c: get_profile_val(c, "Country_Avg_Residual_Load"))
    df["Country_Avg_Price"] = df["Country"].apply(lambda c: get_profile_val(c, "Country_Avg_Price"))
    
    print("   Injected 3 profile features for all rows.")
    return df


# =============================================================================
def main():
    print("=" * 60)
    print("BUILD DAILY FEATURES  (24 features, 17 countries)")
    print("=" * 60)

    df = load_and_merge()
    df_daily = aggregate_to_daily(df)
    scalers = compute_residual_load(df_daily)
    df_daily = add_lags(df_daily)
    df_daily = add_country_profiles(df_daily)
    
    # Drop rows with missing critical features (Lag30 needs 1 month of history)
    before = len(df_daily)
    df_daily = df_daily.dropna(subset=["Price_Lag30", "Real_Wholesale_Price_EUR"])
    print(f"\n[6] Dropped {before - len(df_daily)} rows (Lag30/Target NaN)")
    print(f"   Remaining: {len(df_daily):,} day-country rows")

    # Check all feature columns present
    missing = [c for c in FEATURE_COLS if c not in df_daily.columns]
    if missing:
        print(f"   [!] Missing columns: {missing}")
    else:
        print(f"   [OK] All {len(FEATURE_COLS)} features present")

    # Save
    df_daily.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[7] Saved: {OUTPUT_CSV}")

    os.makedirs(os.path.dirname(SCALER_JSON), exist_ok=True)
    with open(SCALER_JSON, "w") as f:
        json.dump(scalers, f, indent=2)
    print(f"   Saved scalers: {SCALER_JSON}")

    print(f"\n{'='*60}")
    print("Dataset summary:")
    for country in COUNTRIES:
        cdf = df_daily[df_daily["Country"] == country]
        if len(cdf) > 0:
            print(f"  {country}: {len(cdf)} days | {cdf['Date'].min().date()} -> {cdf['Date'].max().date()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
