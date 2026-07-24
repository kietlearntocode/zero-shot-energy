"""
sync_daily.py -- Auto-sync data pipeline for EU electricity price forecast
==========================================================================
Run: python sync_daily.py
Logic:
  1. Read last date from master CSV or recent_data.csv
  2. Compute gap: sync_from = last_date + 1 day
  3. Fetch each API at its native frequency:
     - ENTSO-E : hourly (price, load, generation)
     - yfinance : daily  (TTF, Coal, ETS, Brent)
     - GIE AGSI : daily  (EU gas storage)
  4. Merge all -> save recent_data.csv
"""

import os, sys, time, json
import numpy as np
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

ENTSOE_KEY = os.getenv("ENTSOE_API_KEY", "")
GIE_KEY    = os.getenv("GIE_API_KEY", "")

# ── Đường dẫn ────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV  = os.path.join(BASE_DIR, "web_master_dataset.csv")
RECENT_CSV  = os.path.join(BASE_DIR, "recent_data.csv")

# ── 17 nước train + mã ENTSO-E ─────────────────────────────────────────────────
COUNTRIES = {
    "BE": "BE",      # Belgium
    "CZ": "CZ",      # Czechia
    "DE": "DE_LU",   # Germany-Luxembourg
    "DK": "DK_1",    # Denmark West
    "ES": "ES",      # Spain
    "FI": "FI",      # Finland
    "FR": "FR",      # France
    "GB": "GB",      # Great Britain
    "HU": "HU",      # Hungary
    "IE": "IE",      # Ireland
    "IT": "IT_NORD", # Italy North
    "NL": "NL",      # Netherlands
    "NO": "NO_1",    # Norway 1 (Oslo)
    "PL": "PL",      # Poland
    "PT": "PT",      # Portugal
    "SE": "SE_3",    # Sweden 3 (Stockholm)
    "SK": "SK",      # Slovakia
}

RENEWABLE_TYPES = [
    "Biomass", "Geothermal", "Hydro Run-of-river and poundage",
    "Hydro Water Reservoir", "Other renewable",
    "Solar", "Wind Offshore", "Wind Onshore",
]

# ── Ticker yfinance (only reliable active tickers) ───────────────────────────
FINANCE_TICKERS = {
    "TTF=F":    "TTF_Gas_Price",
    "BZ=F":     "Brent_Oil_Price",
    # MTF=F (Rotterdam Coal API2) -- delisted from Yahoo Finance
    # EUA.L (EU ETS) -- unreliable; will be filled from master CSV
}


# ═════════════════════════════════════════════════════════════════════════════
# 1. Tự phát hiện days cuối cùng đã có
# ═════════════════════════════════════════════════════════════════════════════
def get_last_datetimes() -> dict:
    last_dates = {}
    for path in [MASTER_CSV, RECENT_CSV]:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, usecols=["Datetime", "Country"], low_memory=False)
                df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
                grouped = df.groupby("Country")["Datetime"].max()
                for c, dt in grouped.items():
                    if c not in last_dates or dt > last_dates[c]:
                        last_dates[c] = dt
                print(f"  [{os.path.basename(path)}] -> max dates loaded for {len(grouped)} countries")
            except Exception as e:
                print(f"  Warn: {path}: {e}")
    if not last_dates:
        raise RuntimeError("No data files found!")
    return last_dates


# ═════════════════════════════════════════════════════════════════════════════
# 2. Fetch ENTSO-E — Hourly: Price, Load, Generation
# ═════════════════════════════════════════════════════════════════════════════
def fetch_entsoe_country(entsoe_code: str, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Fetch hourly price, load, renewables từ ENTSO-E cho 1 nước."""
    try:
        from entsoe import EntsoePandasClient
    except ImportError:
        print("  [!] entsoe-py not installed. Run: pip install entsoe-py")
        return {}

    if not ENTSOE_KEY:
        print("  [!] Missing ENTSOE_API_KEY")
        return {}

    client = EntsoePandasClient(api_key=ENTSOE_KEY)
    result = {}

    # — Giá Day-Ahead (EUR/MWh) ————————————————————
    try:
        prices = client.query_day_ahead_prices(entsoe_code, start=start, end=end)
        prices = prices.resample("h").mean()
        result["price"] = prices
        print(f"    Price OK: {len(prices)} hours")
    except Exception as e:
        print(f"    Price WARN: {e}")
        result["price"] = None
    time.sleep(1)

    # — Actual Load (MW) ————————————————————
    try:
        load = client.query_load(entsoe_code, start=start, end=end)
        if isinstance(load, pd.DataFrame):
            load = load.iloc[:, 0]
        load = load.resample("h").mean()
        result["load"] = load
        print(f"    Load OK: {len(load)} hours")
    except Exception as e:
        print(f"    Load WARN: {e}")
        result["load"] = None
    time.sleep(1)

    # — Generation (tính Renewables) ————————————————
    try:
        gen = client.query_generation(entsoe_code, start=start, end=end)

        # Flatten MultiIndex columns nếu có
        if isinstance(gen.columns, pd.MultiIndex):
            gen.columns = [" ".join(c).strip() for c in gen.columns]

        # Tổng Renewables
        renewables = pd.Series(0.0, index=gen.index)
        for rtype in RENEWABLE_TYPES:
            # Tìm cột match (có thể là "Actual Aggregated Solar" hoặc "Solar")
            matched = [c for c in gen.columns if rtype.lower() in c.lower()
                      and "consumption" not in c.lower()]
            for col in matched:
                renewables += gen[col].fillna(0)

        renewables = renewables.resample("h").mean()
        result["renewables"] = renewables
        print(f"    Renewables OK: {len(renewables)} hours")
    except Exception as e:
        print(f"    Generation WARN: {e}")
        result["renewables"] = None
    time.sleep(2)

    return result


# ═════════════════════════════════════════════════════════════════════════════
# 3. Fetch yfinance — Daily: TTF, Coal, ETS, Brent, EUR/NOK, EUR/PLN
# ═════════════════════════════════════════════════════════════════════════════
def fetch_finance_daily(start_date: str, end_date: str) -> pd.DataFrame:
    """Download daily close prices từ Yahoo Finance."""
    print(f"\n[yfinance] Fetch {start_date} -> {end_date}")
    frames = {}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    for ticker, col_name in FINANCE_TICKERS.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date,
                             auto_adjust=True, progress=False, session=session)
            if not df.empty:
                s = df["Close"]
                if isinstance(s, pd.DataFrame):
                    s = s.iloc[:, 0]
                frames[col_name] = s.copy()
                print(f"  {col_name}: {len(df)} days")
            else:
                print(f"  {col_name}: No data (ticker {ticker} possibly delisted)")
                frames[col_name] = None
        except Exception as e:
            print(f"  {col_name} ERROR: {e}")
            frames[col_name] = None

    # -- Fallback: Coal_Price + EU_ETS_Price from master CSV last known value --
    for col in ["Coal_Price", "EU_ETS_Price"]:
        if col not in frames or frames[col] is None:
            try:
                df_m = pd.read_csv(MASTER_CSV, usecols=["Datetime", col], low_memory=True)
                df_m["Datetime"] = pd.to_datetime(df_m["Datetime"], utc=True)
                last_val = float(df_m[col].dropna().iloc[-1])
                # Fill constant across date range (best available proxy)
                idx = pd.date_range(start=start_date, end=end_date, freq="D", tz="UTC")
                frames[col] = pd.Series(last_val, index=idx)
                print(f"  {col}: using master CSV fallback = {last_val:.2f}")
            except Exception as e:
                print(f"  {col}: fallback failed ({e})")

    # Combine into daily DataFrame -- normalize all Series to UTC first
    valid = {}
    for k, v in frames.items():
        if v is None:
            continue
        s = v.copy()
        s.index = pd.to_datetime(s.index)
        if s.index.tz is None:
            s.index = s.index.tz_localize("UTC")
        else:
            s.index = s.index.tz_convert("UTC")
        valid[k] = s

    if valid:
        df_fin = pd.DataFrame(valid)
        df_fin = df_fin.sort_index().ffill()
        return df_fin
    return pd.DataFrame()



# ═════════════════════════════════════════════════════════════════════════════
# 4. Fetch GIE AGSI — Daily: EU Gas Storage
# ═════════════════════════════════════════════════════════════════════════════
def fetch_gie_daily(start_date: datetime, end_date: datetime) -> pd.Series:
    """Fetch daily EU gas storage percentage từ GIE AGSI API."""
    if not GIE_KEY:
        print("  [!] Missing GIE_API_KEY")
        return pd.Series(dtype=float)

    print(f"\n[GIE AGSI] Fetch {start_date.date()} -> {end_date.date()}")
    headers = {"x-key": GIE_KEY}
    all_records = []

    # Chia thành chunk 6 tháng để tránh giới hạn size=300
    current = start_date
    while current < end_date:
        chunk_end = min(current + timedelta(days=180), end_date)
        url = (f"https://agsi.gie.eu/api?type=eu"
               f"&from={current.strftime('%Y-%m-%d')}"
               f"&to={chunk_end.strftime('%Y-%m-%d')}"
               f"&size=300")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "data" in data and data["data"]:
                all_records.extend(data["data"])
                print(f"  Chunk {current.date()} -> {chunk_end.date()}: {len(data['data'])} days")
        except Exception as e:
            print(f"  GIE WARN: {e}")
        current = chunk_end + timedelta(days=1)
        time.sleep(1)

    if not all_records:
        return pd.Series(dtype=float)

    df = pd.DataFrame(all_records)
    df["gasDayStart"] = pd.to_datetime(df["gasDayStart"], utc=True)
    df = df.sort_values("gasDayStart").set_index("gasDayStart")
    return df["full"].astype(float)


# ═════════════════════════════════════════════════════════════════════════════
# 5. Tính Gas Storage Anomaly dựa trên lịch sử
# ═════════════════════════════════════════════════════════════════════════════
def compute_gas_anomaly(gas_full_series: pd.Series) -> pd.Series:
    """
    EU_Gas_Storage_Anomaly = (full% - trung_bình_lịch_sử_cùng_doy) / 100
    Trung bình lịch sử lấy từ master CSV giai đoạn 2018-2022 (trước khủng hoảng)
    """
    try:
        # Đọc lịch sử để tính seasonal average
        df_master = pd.read_csv(
            MASTER_CSV,
            usecols=["Datetime", "EU_Gas_Storage_Full"],
            low_memory=True
        )
        df_master["Datetime"] = pd.to_datetime(df_master["Datetime"], utc=True)
        df_master = df_master[df_master["Datetime"].dt.year.between(2018, 2022)]
        df_master["doy"] = df_master["Datetime"].dt.dayofyear
        seasonal_avg = df_master.groupby("doy")["EU_Gas_Storage_Full"].mean()
    except Exception:
        # Fallback: dùng hằng số 65% nếu không đọc được
        seasonal_avg = pd.Series(65.0, index=range(1, 367))

    anomaly = pd.Series(index=gas_full_series.index, dtype=float)
    for ts, val in gas_full_series.items():
        doy = ts.dayofyear if hasattr(ts, "dayofyear") else pd.Timestamp(ts).dayofyear
        avg = seasonal_avg.get(doy, 65.0)
        anomaly[ts] = (float(val) - avg) / 100.0
    return anomaly


# ═════════════════════════════════════════════════════════════════════════════
# 6. Thêm cyclical features
# ═════════════════════════════════════════════════════════════════════════════
def add_cyclical_features(df: pd.DataFrame, dt_col: str = "Datetime") -> pd.DataFrame:
    dt = pd.to_datetime(df[dt_col], utc=True)
    df["Hour"]       = dt.dt.hour
    df["DayOfWeek"]  = dt.dt.dayofweek
    df["Month"]      = dt.dt.month
    df["Is_Weekend"] = (dt.dt.dayofweek >= 5).astype(int)
    df["Hour_Sin"]      = np.sin(2 * np.pi * df["Hour"] / 24)
    df["Hour_Cos"]      = np.cos(2 * np.pi * df["Hour"] / 24)
    df["DayOfWeek_Sin"] = np.sin(2 * np.pi * df["DayOfWeek"] / 7)
    df["DayOfWeek_Cos"] = np.cos(2 * np.pi * df["DayOfWeek"] / 7)
    df["Month_Sin"]     = np.sin(2 * np.pi * df["Month"] / 12)
    df["Month_Cos"]     = np.cos(2 * np.pi * df["Month"] / 12)
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 7. Hàm chính: Sync
# ═════════════════════════════════════════════════════════════════════════════
def sync():
    print("=" * 60)
    print("SYNC DAILY -- EU Electricity Price Pipeline")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── Bước 1: Phát hiện gap ───────────────────────────────────────
    last_dates = get_last_datetimes()
    sync_to = pd.Timestamp.now(tz="UTC").floor("h")

    # Fetch daily finance/gas based on the EARLIEST sync_from across all countries
    min_last_dt = min(last_dates.values())
    global_sync_from = min_last_dt + timedelta(hours=1)
    
    if global_sync_from >= sync_to:
        print("\n Data is up-to-date. No sync needed.")
        return

    print(f"\n Max Gap detected: {(sync_to - global_sync_from).days} days")
    print(f"  From: {global_sync_from.date()} To: {sync_to.date()}")

    # Tạo buffer lùi về 7 ngày để lấy đủ giá trị cũ làm gốc cho hàm ffill()
    sync_from_buffer = global_sync_from - timedelta(days=7)

    fin_start = sync_from_buffer.date().isoformat()
    fin_end   = (sync_to.date() + timedelta(days=1)).isoformat()

    # ── Bước 2: Fetch Finance ────────────
    df_finance = fetch_finance_daily(fin_start, fin_end)

    # ── Bước 3: Fetch GIE Gas Storage ───
    gas_full = fetch_gie_daily(sync_from_buffer.to_pydatetime(), sync_to.to_pydatetime())
    if not gas_full.empty:
        gas_anomaly = compute_gas_anomaly(gas_full)
    else:
        gas_anomaly = None

    # ── Bước 4: Fetch ENTSO-E per country (Hourly) ──────────────────
    all_country_dfs = []

    for country_iso, entsoe_code in COUNTRIES.items():
        c_last = last_dates.get(country_iso, global_sync_from - timedelta(hours=1))
        c_sync_from = c_last + timedelta(hours=1)
        
        if c_sync_from >= sync_to:
            print(f"\n[ENTSO-E] Country: {country_iso} is up to date.")
            continue
            
        print(f"\n[ENTSO-E] Country: {country_iso} ({entsoe_code}) -> Syncing {(sync_to - c_sync_from).days} days")

        c_ts_start = c_sync_from.tz_convert("Europe/Brussels") if c_sync_from.tzinfo else c_sync_from.tz_localize("UTC").tz_convert("Europe/Brussels")
        c_ts_end   = sync_to.tz_convert("Europe/Brussels")

        entsoe = fetch_entsoe_country(entsoe_code, c_ts_start, c_ts_end)

        hourly_idx = pd.date_range(
            start=c_sync_from, end=sync_to, freq="h", tz="UTC"
        )
        df_c = pd.DataFrame({"Datetime": hourly_idx})
        df_c["Country"] = country_iso

        # — Price ─────────────────────────────────────────────────
        if entsoe.get("price") is not None:
            p = entsoe["price"].copy()
            p.index = p.index.tz_convert("UTC")
            p = p.reindex(hourly_idx, method="nearest", tolerance=pd.Timedelta("1h"))
            df_c["Wholesale_Price_EUR"] = p.values
            df_c["Real_Wholesale_Price_EUR"] = p.values  # Dùng nominal làm proxy (không có HICP 2026)
        else:
            df_c["Wholesale_Price_EUR"] = np.nan
            df_c["Real_Wholesale_Price_EUR"] = np.nan

        # — Load ──────────────────────────────────────────────────────
        if entsoe.get("load") is not None:
            l = entsoe["load"].copy()
            l.index = l.index.tz_convert("UTC")
            l = l.reindex(hourly_idx, method="nearest", tolerance=pd.Timedelta("1h"))
            df_c["Load"] = l.values
        else:
            df_c["Load"] = np.nan

        # — Renewables ────────────────────────────────────────────────
        if entsoe.get("renewables") is not None:
            r = entsoe["renewables"].copy()
            r.index = r.index.tz_convert("UTC")
            r = r.reindex(hourly_idx, method="nearest", tolerance=pd.Timedelta("1h"))
            df_c["Renewables_MW"] = r.values
        else:
            df_c["Renewables_MW"] = np.nan

        # — Finance (daily → reindex hourly → ffill) ──────────────────
        if not df_finance.empty:
            for col in df_finance.columns:
                fin_h = df_finance[col].reindex(hourly_idx, method="ffill")
                df_c[col] = fin_h.values

        # — Gas Storage Anomaly (daily → reindex hourly → ffill) ──────
        if gas_anomaly is not None and not gas_anomaly.empty:
            ga_h = gas_anomaly.reindex(hourly_idx, method="ffill")
            df_c["EU_Gas_Storage_Anomaly"] = ga_h.values
        else:
            df_c["EU_Gas_Storage_Anomaly"] = 0.0

        if gas_full is not None and not gas_full.empty:
            gf_h = gas_full.reindex(hourly_idx, method="ffill")
            df_c["EU_Gas_Storage_Full"] = gf_h.values
        else:
            df_c["EU_Gas_Storage_Full"] = np.nan

        # — Cyclical features ─────────────────────────────────────────
        df_c = add_cyclical_features(df_c, "Datetime")

        all_country_dfs.append(df_c)
        print(f"  -> {country_iso}: {len(df_c)} hours processed")

    if not all_country_dfs:
        print("\n No data fetched.")
        return

    # ── Bước 5: Merge and save ─────────────────────────────────────────
    df_new = pd.concat(all_country_dfs, ignore_index=True)
    df_new["Datetime"] = pd.to_datetime(df_new["Datetime"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00:00")

    if os.path.exists(RECENT_CSV):
        df_existing = pd.read_csv(RECENT_CSV)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new

    # Dedup
    df_final = df_final.drop_duplicates(subset=["Datetime", "Country"]).sort_values(
        ["Country", "Datetime"]
    )

    df_final.to_csv(RECENT_CSV, index=False)
    print(f"\n{'='*60}")
    print(f" Sync complete! {len(df_new)} new rows -> {RECENT_CSV}")
    print(f" Total {len(df_final)} rows in recent_data.csv")
    print(f"{'='*60}")


if __name__ == "__main__":
    sync()
