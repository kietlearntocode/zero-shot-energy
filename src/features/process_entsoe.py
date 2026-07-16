import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_entsoe():
    print("--- CHẠY MODULE: PROCESS ENTSOE ADVANCED ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "entsoe_advanced_features_raw.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df = df.drop_duplicates(subset=['Datetime', 'Country'], keep='last')
    
    # 2. Xử lý Forecast (Flow = Mean)
    forecast_cols = [c for c in df.columns if 'Forecast' in c]
    df_forecast = df[['Datetime', 'Country'] + forecast_cols].copy()
    df_forecast = resample_hourly_by_country(df_forecast, 'Datetime', 'mean')
    
    # 3. Xử lý Reservoir (Inventory = Ffill)
    hydro_path = os.path.join(raw_dir, "entsoe_hydro_raw.csv")
    if os.path.exists(hydro_path):
        print(" -> Đang tích hợp dữ liệu Hydro Reservoir...")
        df_hydro_raw = pd.read_csv(hydro_path)
        df_hydro_raw['Datetime'] = pd.to_datetime(df_hydro_raw['Datetime'], utc=True)
        # Bỏ duplicate và ffill
        df_hydro_raw.drop_duplicates(subset=['Datetime', 'Country'], keep='last', inplace=True)
        df_hydro = resample_hourly_by_country(df_hydro_raw, 'Datetime', 'ffill')
        # Rename column for consistency if needed, assuming 'Hydro_Reservoir_Level' is the column name
        # Gộp lại
        df_final = pd.merge(df_forecast, df_hydro, on=['Country', 'Datetime'], how='outer')
    elif 'Water_Reservoirs' in df.columns:
        df_hydro = df[['Datetime', 'Country', 'Water_Reservoirs']].copy()
        df_hydro = resample_hourly_by_country(df_hydro, 'Datetime', 'ffill')
        # Gộp lại
        df_final = pd.merge(df_forecast, df_hydro, on=['Country', 'Datetime'], how='outer')
    else:
        df_final = df_forecast
        
    # Sắp xếp lại để Validation chạy đúng (cần sort)
    df_final.sort_values(by=['Country', 'Datetime'], inplace=True)
    
    # 4. Quét lỗi (Validation)
    if validate_dataset(df_final, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_entsoe.csv")
        df_final.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hủy lưu file.")

if __name__ == "__main__":
    process_entsoe()
