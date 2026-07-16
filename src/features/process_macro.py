import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_macro():
    print("--- CHẠY MODULE: PROCESS MACRO (HICP & Ind Prod) ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "macro_eu17_raw.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    
    # 2. Re-sample (Macro = Ffill vì là Step-function hàng tháng)
    # Tuân thủ luật No Look-ahead Bias (Interpolate bị cấm cho macro)
    df_resampled = resample_hourly_by_country(df, 'Datetime', 'ffill')
    
    # Lọc bỏ rác trước 2018 nếu có
    df_resampled = df_resampled[df_resampled['Datetime'].dt.year >= 2018].copy()
    
    # 3. Quét lỗi (Validation)
    if validate_dataset(df_resampled, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_macro.csv")
        df_resampled.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hủy lưu file.")

if __name__ == "__main__":
    process_macro()
