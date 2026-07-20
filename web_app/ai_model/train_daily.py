"""
train_daily.py — Train XGBoost Daily Forecast Model
=====================================================
Input : daily_features_data.csv
Output: daily_xgb.json + training_report.json

Split: Walk-Forward
  Train: 2018-01-31 → 2025-11-30 (toàn bộ 17 nước gộp lại, khớp mốc bài báo)
  Test : 2025-12-01 → 2026-12-31
"""

import os, json, sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score, mean_absolute_error

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "../data_pipeline/daily_features_data.csv")
MODEL_PATH  = os.path.join(BASE_DIR, "daily_xgb.json")
REPORT_PATH = os.path.join(BASE_DIR, "training_report.json")

COUNTRIES = [
    "BE", "CZ", "DE", "DK", "ES", "FI", "FR", "GB", 
    "HU", "IE", "IT", "NL", "NO", "PL", "PT", "SE", "SK"
]

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


TARGET = "Real_Wholesale_Price_EUR"

# Walk-Forward split
TRAIN_END = "2025-11-30"
TEST_START = "2025-12-01"
TEST_END = "2026-12-31"


def load_data():
    print("[1] Đọc dữ liệu...")
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])

    # Kiểm tra coverage
    for country in COUNTRIES:
        cdf = df[df["Country"] == country]
        print(f"   {country}: {len(cdf)} ngày | {cdf['Date'].min().date()} → {cdf['Date'].max().date()}")

    return df


def prepare_splits(df):
    print(f"\n[2] Walk-Forward Split:")
    
    train_mask = df["Date"] <= TRAIN_END
    test_mask  = df["Date"] >= TEST_START

    df_train = df[train_mask].copy()
    df_test  = df[test_mask].copy()

    train_start = df_train["Date"].min().strftime('%Y-%m-%d')
    print(f"   Train: {train_start} → {TRAIN_END}")
    print(f"   Test : {TEST_START} → {TEST_END}")

    train_mask = df["Date"] <= TRAIN_END
    test_mask  = df["Date"] >= TEST_START

    df_train = df[train_mask].copy()
    df_test  = df[test_mask].copy()

    # Fill missing features by Forward-fill, then 0 for leftovers (like Gas Storage)
    df_train[FEATURE_COLS] = df_train[FEATURE_COLS].ffill().fillna(0)
    df_test[FEATURE_COLS]  = df_test[FEATURE_COLS].ffill().fillna(0)
    
    # Only drop rows where TARGET is missing
    df_train = df_train.dropna(subset=[TARGET])
    df_test  = df_test.dropna(subset=[TARGET])

    X_train = df_train[FEATURE_COLS]
    y_train = df_train[TARGET]
    X_test  = df_test[FEATURE_COLS]
    y_test  = df_test[TARGET]

    print(f"   Train samples: {len(X_train):,}")
    print(f"   [OK] All {len(FEATURE_COLS)} features available")
    print(f"   Test samples : {len(X_test):,}")
    return X_train, y_train, X_test, y_test, df_train, df_test


def train_model(X_train, y_train, X_test, y_test):
    print("\n[3] Training XGBoost...")

    model = xgb.XGBRegressor(
        n_estimators=800,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=50,
        eval_metric="mae",
        verbosity=0,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    return model


def evaluate(model, X_train, y_train, X_test, y_test, df_train, df_test):
    print("\n[4] Đánh giá kết quả...")

    y_pred_train = model.predict(X_train)
    y_pred_test  = model.predict(X_test)

    r2_train  = r2_score(y_train, y_pred_train)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    r2_test   = r2_score(y_test, y_pred_test)
    mae_test  = mean_absolute_error(y_test, y_pred_test)

    print(f"\n   ┌─────────────────────────────────┐")
    print(f"   │ Train  R² = {r2_train:.4f}  MAE = {mae_train:.2f} EUR │")
    print(f"   │ Test   R² = {r2_test:.4f}  MAE = {mae_test:.2f} EUR │")
    print(f"   └─────────────────────────────────┘")

    # Per-country test performance
    country_metrics = {}
    print("\n   Per-country (Test 2026):")
    for country in COUNTRIES:
        mask = df_test["Country"] == country
        if mask.sum() == 0:
            continue
        yt = df_test.loc[mask, TARGET]
        Xt = df_test.loc[mask, FEATURE_COLS]
        yp = model.predict(Xt)
        r2  = r2_score(yt, yp)
        mae = mean_absolute_error(yt, yp)
        country_metrics[country] = {"R2": round(r2, 4), "MAE": round(mae, 2)}
        print(f"     {country}: R²={r2:.4f}  MAE={mae:.2f} EUR/MWh")

    # Feature importance
    importance = pd.Series(
        model.feature_importances_, index=FEATURE_COLS
    ).sort_values(ascending=False)
    print("\n   Top 10 Features:")
    for feat, imp in importance.head(10).items():
        bar = "█" * int(imp * 200)
        print(f"     {feat:<35} {imp:.4f} {bar}")

    return {
        "train": {"R2": round(r2_train, 4), "MAE": round(mae_train, 2)},
        "test":  {"R2": round(r2_test, 4),  "MAE": round(mae_test, 2)},
        "by_country": country_metrics,
        "feature_importance": importance.round(4).to_dict(),
    }


def main():
    print("=" * 60)
    print("TRAIN DAILY XGBOOST — EU Electricity Price Forecast")
    print("=" * 60)

    df = load_data()
    X_train, y_train, X_test, y_test, df_train, df_test = prepare_splits(df)
    model = train_model(X_train, y_train, X_test, y_test)

    report = evaluate(model, X_train, y_train, X_test, y_test, df_train, df_test)

    # Lưu model
    model.save_model(MODEL_PATH)
    print(f"\n[5] Model đã lưu: {MODEL_PATH}")

    # Lưu report
    report["model_path"] = MODEL_PATH
    report["features"] = FEATURE_COLS
    
    train_start = df_train["Date"].min().strftime('%Y-%m-%d')
    report["train_period"] = f"{train_start} → {TRAIN_END}"
    report["test_period"]  = f"{TEST_START} → {TEST_END}"
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"   Report đã lưu: {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
