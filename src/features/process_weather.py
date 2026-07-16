import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_weather():
    print("--- CHẠY MODULE: PROCESS WEATHER (ERA5 FEATURES) ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "era5_eu17_raw.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}. Cần chạy fetch_era5.py trước.")
        return
        
    df = pd.read_csv(raw_path)
    
    # Ép kiểu Datetime
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df = df[df['Datetime'].dt.year >= 2018].copy()
    
    print(" -> Đang tính toán Climatological Means (Anomalies)...")
    # Lấy thông tin Month, Hour để nhóm
    df['Month'] = df['Datetime'].dt.month
    df['Hour'] = df['Datetime'].dt.hour
    
    # 1. Tính Historical Climatological Mean dựa trên mẫu hiện tại (2018-2025) thay cho 1990-2010 vì giới hạn quota
    # Group by (Country, Month, Hour)
    baseline = df.groupby(['Country', 'Month', 'Hour'])[['Temperature', 'Wind_Speed', 'Solar_Irradiance']].mean().reset_index()
    baseline.rename(columns={
        'Temperature': 'Temp_Baseline',
        'Wind_Speed': 'Wind_Baseline',
        'Solar_Irradiance': 'Solar_Baseline'
    }, inplace=True)
    
    # Merge lại vào df
    df = pd.merge(df, baseline, on=['Country', 'Month', 'Hour'], how='left')
    
    # Tính Anomalies
    df['Temperature_Anomaly'] = df['Temperature'] - df['Temp_Baseline']
    df['Wind_Speed_Anomaly'] = df['Wind_Speed'] - df['Wind_Baseline']
    
    # Xóa cột tạm
    df.drop(columns=['Month', 'Hour', 'Temp_Baseline', 'Wind_Baseline', 'Solar_Baseline'], inplace=True)
    
    print(" -> Đang tính toán Hydrological Stocks (Rolling Sum 7d, 30d)...")
    # Cần sắp xếp chuẩn trước khi rolling
    df.sort_values(by=['Country', 'Datetime'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Tính rolling sum an toàn và nhanh
    df['Precipitation_7d'] = df.groupby('Country')['Precipitation'].rolling(window=168, min_periods=1).sum().reset_index(level=0, drop=True)
    df['Precipitation_30d'] = df.groupby('Country')['Precipitation'].rolling(window=720, min_periods=1).sum().reset_index(level=0, drop=True)
    
    # Re-sample để đảm bảo continuity và xử lý missing values nhỏ lẻ
    # Mean cho các rate (Temperature, Wind, Anomaly, Cloud_Cover)
    # Tổng/Tích lũy sẽ lấy mean để mượt hóa trong lưới giờ
    print(" -> Đang Resample về chuẩn 1h...")
    df_resampled = resample_hourly_by_country(df, 'Datetime', 'mean')
    
    # Quét lỗi (Validation)
    if validate_dataset(df_resampled, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_weather.csv")
        df_resampled.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hãy lưu file.")

if __name__ == "__main__":
    process_weather()

