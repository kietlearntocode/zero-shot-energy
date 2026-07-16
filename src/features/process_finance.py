import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from src.features.validation import validate_dataset

def process_finance():
    print("--- CHẠY MODULE: PROCESS FINANCE ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "finance_2018-01-01_2025-12-31.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['Date'], utc=True)
    df.drop(columns=['Date'], inplace=True, errors='ignore')
    
    # 2. Xử lý Anomaly (Volatility) - Tính trước khi resample 1h để chuẩn window 30 ngày
    # Sắp xếp đúng thứ tự thời gian
    df.sort_values('Datetime', inplace=True)
    
    if 'Coal_Price' in df.columns:
        df['Coal_Price_Volatility'] = df['Coal_Price'].rolling(window=30, min_periods=1).std()
        # std() của 1 số là NaN, điền 0 cho mượt
        df['Coal_Price_Volatility'] = df['Coal_Price_Volatility'].fillna(0)
    
    if 'TTF_Gas_Price' in df.columns:
        df['TTF_Gas_Price_Volatility'] = df['TTF_Gas_Price'].rolling(window=30, min_periods=1).std()
        df['TTF_Gas_Price_Volatility'] = df['TTF_Gas_Price_Volatility'].fillna(0)
    
    # 3. Re-sample (Finance = Ffill kéo dài qua T7, CN)
    df = df.drop_duplicates(subset=['Datetime'], keep='last').set_index('Datetime')
    df_resampled = df.resample('1h').ffill().reset_index()
    
    df_resampled = df_resampled[df_resampled['Datetime'].dt.year >= 2018].copy()
    
    # 4. Quét lỗi (Validation)
    if validate_dataset(df_resampled, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_finance.csv")
        df_resampled.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hãy lưu file.")

if __name__ == "__main__":
    process_finance()

