import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from src.features.validation import validate_dataset

def process_gas():
    print("--- CHẠY MODULE: PROCESS GAS STORAGE ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "gas_storage_EU_2018_2025.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['gasDayStart'], utc=True)
    df.drop(columns=['gasDayStart'], inplace=True, errors='ignore')
    
    df = df.rename(columns={
        'full': 'EU_Gas_Storage_Full', 
        'trend': 'EU_Gas_Storage_Trend', 
        'injection': 'EU_Gas_Injection', 
        'withdrawal': 'EU_Gas_Withdrawal'
    })
    
    # 2. Xử lý tính toán Anomaly (Task 3.3)
    df['Month'] = df['Datetime'].dt.month
    df['Day'] = df['Datetime'].dt.day
    
    # Lấy trung bình toàn dải để làm Historical Average (proxy 5-year average)
    baseline = df.groupby(['Month', 'Day'])[['EU_Gas_Storage_Full']].mean().reset_index()
    baseline.rename(columns={'EU_Gas_Storage_Full': 'EU_Gas_Storage_Baseline'}, inplace=True)
    
    df = pd.merge(df, baseline, on=['Month', 'Day'], how='left')
    df['EU_Gas_Storage_Anomaly'] = df['EU_Gas_Storage_Full'] - df['EU_Gas_Storage_Baseline']
    df.drop(columns=['Month', 'Day', 'EU_Gas_Storage_Baseline'], inplace=True)
    
    # 3. Re-sample (Inventory = Ffill)
    df = df.drop_duplicates(subset=['Datetime'], keep='last').set_index('Datetime')
    df_resampled = df.resample('1h').ffill().reset_index()
    
    df_resampled = df_resampled[df_resampled['Datetime'].dt.year >= 2018].copy()
    
    # 4. Quét lỗi (Validation)
    if validate_dataset(df_resampled, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_gas.csv")
        df_resampled.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hãy lưu file.")

if __name__ == "__main__":
    process_gas()

