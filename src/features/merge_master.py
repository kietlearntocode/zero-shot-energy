import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import numpy as np
from datetime import datetime
try:
    import holidays
except ImportError:
    holidays = None

def get_holiday_flag(country_code, dt):
    if holidays is None:
        return 0
    try:
        country_holidays = holidays.country_holidays(country_code)
        return 1 if dt in country_holidays else 0
    except Exception:
        return 0

def merge_master_dataset():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu Phase 3B: Gộp dữ liệu thành Master Dataset (1 Giờ)")
    interim_dir = os.path.join("data", "interim")
    processed_dir = os.path.join("data", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    # 1. Tải Base Data (Ember Price)
    print(" -> Tải dữ liệu Xương sống (Price)...")
    master_path = os.path.join(interim_dir, "processed_price.csv")
    if not os.path.exists(master_path):
        print("[ERROR] LỖI: Chưa chạy process_price.py")
        return
        
    df_master = pd.read_csv(master_path)
    df_master['Datetime'] = pd.to_datetime(df_master['Datetime'], utc=True)
    
    # Danh sách các file vệ tinh (Interim)
    satellites = [
        ("Energy", "processed_energy.csv", ['Country', 'Datetime']),
        ("ENTSO-E", "processed_entsoe.csv", ['Country', 'Datetime']),
        ("Macro (CPI)", "processed_macro.csv", ['Country', 'Datetime']),
        ("Weather", "processed_weather.csv", ['Country', 'Datetime'])
    ]
    
    for name, file_name, join_keys in satellites:
        print(f" -> Merge {name}...")
        file_path = os.path.join(interim_dir, file_name)
        if os.path.exists(file_path):
            df_sat = pd.read_csv(file_path)
            df_sat['Datetime'] = pd.to_datetime(df_sat['Datetime'], utc=True)
            cols_to_use = [col for col in df_sat.columns if col not in df_master.columns or col in join_keys]
            df_master = pd.merge(df_master, df_sat[cols_to_use], on=join_keys, how='left')
        else:
            print(f"    [WARN] Bỏ qua {name} vì không tìm thấy file {file_name}")

    # Merge EU/Global level data (chỉ join theo Datetime)
    global_satellites = [
        ("Gas Storage", "processed_gas.csv"),
        ("Finance", "processed_finance.csv")
    ]
    
    for name, file_name in global_satellites:
        print(f" -> Merge {name} (Global Level)...")
        file_path = os.path.join(interim_dir, file_name)
        if os.path.exists(file_path):
            df_sat = pd.read_csv(file_path)
            df_sat['Datetime'] = pd.to_datetime(df_sat['Datetime'], utc=True)
            cols_to_use = [col for col in df_sat.columns if col not in df_master.columns or col == 'Datetime']
            df_master = pd.merge(df_master, df_sat[cols_to_use], on=['Datetime'], how='left')
        else:
            print(f"    [WARN] Bỏ qua {name} vì không tìm thấy file {file_name}")

    # Ghép Climate Drift
    print(" -> Merge Khí hậu quá khứ (Climate Drift)...")
    climate_path = os.path.join(interim_dir, "processed_climate_past.csv")
    if os.path.exists(climate_path):
        df_climate = pd.read_csv(climate_path)
        
        df_master['Join_Year'] = df_master['Datetime'].dt.year - 10
        df_master['Month'] = df_master['Datetime'].dt.month
        df_master['Day'] = df_master['Datetime'].dt.day
        df_master['Hour'] = df_master['Datetime'].dt.hour
        
        df_master = pd.merge(df_master, df_climate, on=['Country', 'Join_Year', 'Month', 'Day', 'Hour'], how='left')
        
        if 'Temperature' in df_master.columns and 'Temperature_Past' in df_master.columns:
            df_master['Climate_Drift_10Y'] = df_master['Temperature'] - df_master['Temperature_Past']
            
        df_master.drop(columns=['Temperature_Past', 'Join_Year', 'Month', 'Day', 'Hour'], inplace=True, errors='ignore')
        
    # ==========================================================================
    # Kỹ Nghệ Đặc Trưng Nâng Cao (Advanced Feature Engineering)
    # ==========================================================================
    print(" -> Tính toán Tỷ trọng Sản lượng (Generation Shares)...")
    if 'Load' in df_master.columns:
        if 'Renewables_MW' in df_master.columns:
            df_master['%_Renewables'] = df_master['Renewables_MW'] / df_master['Load']
        if 'Fossil_MW' in df_master.columns:
            df_master['%_Fossil'] = df_master['Fossil_MW'] / df_master['Load']
        if 'Nuclear_MW' in df_master.columns:
            df_master['%_Nuclear'] = df_master['Nuclear_MW'] / df_master['Load']

    print(" -> Tính toán Sai số Dự báo (Forecast Errors)...")
    if 'Load' in df_master.columns and 'Forecasted Load' in df_master.columns:
        df_master['Load_Forecast_Error'] = df_master['Load'] - df_master['Forecasted Load']
    if 'Renewables_MW' in df_master.columns and 'Forecast_Solar' in df_master.columns and 'Forecast_Wind Onshore' in df_master.columns:
        df_master['Renewable_Forecast_Error'] = df_master['Renewables_MW'] - (df_master['Forecast_Solar'] + df_master.get('Forecast_Wind Offshore', 0) + df_master['Forecast_Wind Onshore'])
        
    print(" -> Thiết lập Biến cờ Địa chính trị (Geopolitical Flags)...")
    df_master['GB_Brexit_Flag'] = np.where((df_master['Country'] == 'GB') & (df_master['Datetime'] >= '2021-01-01'), 1, 0)
    df_master['Regime_Crisis'] = np.where(df_master['Datetime'] >= '2021-09-01', 1, 0)

    print(" -> Căn chỉnh Cross Border Spread (EU Average Price)...")
    if 'Wholesale_Price_EUR' in df_master.columns:
        eu_avg_price = df_master.groupby('Datetime')['Wholesale_Price_EUR'].transform('mean')
        df_master['Cross_Border_Spread_vs_EU'] = df_master['Wholesale_Price_EUR'] - eu_avg_price
    
    print(" -> Bẻ cong Thời gian và Lịch trình (Time & Schedules)...")
    df_master['Hour'] = df_master['Datetime'].dt.hour
    df_master['DayOfWeek'] = df_master['Datetime'].dt.dayofweek
    df_master['Month'] = df_master['Datetime'].dt.month
    
    df_master['Is_Weekend'] = np.where(df_master['DayOfWeek'] >= 5, 1, 0)
    df_master['Is_Market_Open'] = np.where(df_master['DayOfWeek'] < 5, 1, 0)
    
    print(" -> Đang gắn nhãn Ngày Lễ (Holidays)...")
    unique_dates_countries = df_master[['Country', 'Datetime']].copy()
    unique_dates_countries['Date'] = unique_dates_countries['Datetime'].dt.date
    unique_dates_countries = unique_dates_countries.drop_duplicates(subset=['Country', 'Date'])
    unique_dates_countries['Is_Holiday'] = unique_dates_countries.apply(lambda row: get_holiday_flag(row['Country'], row['Date']), axis=1)
    
    df_master['Date'] = df_master['Datetime'].dt.date
    df_master = pd.merge(df_master, unique_dates_countries[['Country', 'Date', 'Is_Holiday']], on=['Country', 'Date'], how='left')
    df_master.drop(columns=['Date'], inplace=True)
    
    df_master['Hour_Sin'] = np.sin(2 * np.pi * df_master['Hour']/24)
    df_master['Hour_Cos'] = np.cos(2 * np.pi * df_master['Hour']/24)
    df_master['DayOfWeek_Sin'] = np.sin(2 * np.pi * df_master['DayOfWeek']/7)
    df_master['DayOfWeek_Cos'] = np.cos(2 * np.pi * df_master['DayOfWeek']/7)
    df_master['Month_Sin'] = np.sin(2 * np.pi * df_master['Month']/12)
    df_master['Month_Cos'] = np.cos(2 * np.pi * df_master['Month']/12)
    
    print(" -> Phân Cụm Địa Lý (Region_Cluster)...")
    region_map = {
        'AT': 'CWE', 'BE': 'CWE', 'DE': 'CWE', 'FR': 'CWE', 'NL': 'CWE', 'CH': 'CWE',
        'CZ': 'CEE', 'HU': 'CEE', 'PL': 'CEE', 'SK': 'CEE',
        'DK': 'Nordic', 'FI': 'Nordic', 'NO': 'Nordic', 'SE': 'Nordic',
        'IT': 'South', 'ES': 'South', 'PT': 'South', 'GR': 'South'
    }
    df_master['Region_Cluster'] = df_master['Country'].map(region_map).fillna('British_Isles')
    
    print(f" -> Kích thước Master Dataset Cuối Cùng: {df_master.shape}")
    master_path_final = os.path.join(processed_dir, "master_dataset_hourly.csv")
    df_master.to_csv(master_path_final, index=False)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] HOÀN TẤT PHASE 3B! Master Dataset lưu tại: {master_path_final}")

if __name__ == "__main__":
    merge_master_dataset()
