import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_climate_drift():
    print("--- CHẠY MODULE: PROCESS CLIMATE DRIFT ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    climate_raw_path = os.path.join(raw_dir, "weather_historical_2008_2015_raw.csv")
    if not os.path.exists(climate_raw_path):
        print(f"[ERROR] Không tìm thấy file {climate_raw_path}")
        return
        
    df = pd.read_csv(climate_raw_path)
    
    # Ép kiểu Datetime
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    
    # Re-sample
    df_resampled = resample_hourly_by_country(df, 'Datetime', 'mean')
    
    # Rã thời gian để join
    df_resampled['Join_Year'] = df_resampled['Datetime'].dt.year
    df_resampled['Month'] = df_resampled['Datetime'].dt.month
    df_resampled['Day'] = df_resampled['Datetime'].dt.day
    df_resampled['Hour'] = df_resampled['Datetime'].dt.hour
    
    # Trung bình nhiệt
    temp_cols = [c for c in df_resampled.columns if 'Temp_City' in c]
    if temp_cols:
        df_resampled['Temperature_Past'] = df_resampled[temp_cols].mean(axis=1)
    elif 'Temperature' in df_resampled.columns:
        df_resampled.rename(columns={'Temperature': 'Temperature_Past'}, inplace=True)
        
    df_final = df_resampled[['Country', 'Datetime', 'Join_Year', 'Month', 'Day', 'Hour', 'Temperature_Past']].copy()
    
    # Quét lỗi (Validation)
    if validate_dataset(df_final, time_col='Datetime', frequency='1h'):
        # Drop cột Datetime trước khi lưu vì nó là của quá khứ (không dùng để join index)
        df_final.drop(columns=['Datetime'], inplace=True)
        output_path = os.path.join(interim_dir, "processed_climate_past.csv")
        df_final.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hủy lưu file.")

if __name__ == "__main__":
    process_climate_drift()
