import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_price():
    print("--- CHẠY MODULE: PROCESS PRICE ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "ember_wholesale_price_eu17_2018_2025.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df = df[df['Datetime'].dt.year >= 2018]
    
    # 2. Re-sample (Mean)
    df_resampled = resample_hourly_by_country(df, 'Datetime', 'mean')
    
    # 3. Tính Real Wholesale Price (Deflation)
    macro_path = os.path.join(interim_dir, "processed_macro.csv")
    if os.path.exists(macro_path):
        print(" -> Tìm thấy processed_macro.csv, tiến hành tính Real Wholesale Price...")
        df_macro = pd.read_csv(macro_path)
        df_macro['Datetime'] = pd.to_datetime(df_macro['Datetime'], utc=True)
        # Chỉ lấy cột HICP_excluding_energy
        if 'HICP_excluding_energy' in df_macro.columns:
            df_macro_subset = df_macro[['Datetime', 'Country', 'HICP_excluding_energy']]
            df_resampled = pd.merge(df_resampled, df_macro_subset, on=['Datetime', 'Country'], how='left')
            # Tự động nội suy (ffill/bfill) chỉ số lạm phát HICP theo từng quốc gia nếu thiếu (như tháng 12/2025)
            df_resampled['HICP_excluding_energy'] = df_resampled.groupby('Country')['HICP_excluding_energy'].ffill().bfill().fillna(100.0)
            # Tính Real Price
            df_resampled['Real_Wholesale_Price_EUR'] = df_resampled['Wholesale_Price_EUR'] / (df_resampled['HICP_excluding_energy'] / 100)
            # Nếu vẫn còn bất kỳ giá Real nào bị NaN/Inf, fallback về giá danh nghĩa Wholesale_Price_EUR
            df_resampled['Real_Wholesale_Price_EUR'] = df_resampled['Real_Wholesale_Price_EUR'].fillna(df_resampled['Wholesale_Price_EUR'])
            print("     [OK] Đã tính Real_Wholesale_Price_EUR (hoàn toàn không còn NaN).")
        else:
            print("     [WARN] Không tìm thấy HICP_excluding_energy trong processed_macro.csv")
    else:
        print(" -> [WARN] processed_macro.csv chưa tồn tại. Không thể tính Real Price lúc này. Vui lòng chạy process_macro.py trước.")
    
    # 4. Quét lỗi (Validation)
    if validate_dataset(df_resampled, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_price.csv")
        df_resampled.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hãy lưu file.")

if __name__ == "__main__":
    process_price()

