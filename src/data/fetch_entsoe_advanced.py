import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import time
import pandas as pd
from datetime import datetime
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=r'd:\Projects\data\ember\.env')
api_key = os.getenv('ENTSOE_API_KEY')
if not api_key or api_key == 'your_entsoe_api_key_here':
    print("[WARN] WARNING: ENTSOE_API_KEY chưa được thiết lập. Bỏ qua tải dữ liệu ENTSO-E nâng cao.")
    exit(0)

client = EntsoePandasClient(api_key=api_key)

# 17 Quốc gia EU17 (Chuyển sang In hoa để dùng cho ENTSO-E)
COUNTRIES = ['DE', 'FR', 'NL', 'BE', 'PL', 'CZ', 'SK', 'HU', 'ES', 'PT', 'IT', 'NO', 'SE', 'FI', 'DK', 'GB', 'IE']
YEARS = range(2018, 2026)

def fetch_entsoe_advanced():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu cào dữ liệu ENTSO-E Nâng cao (2018-2025) cho {len(COUNTRIES)} quốc gia (Pure Extraction)")
    
    output_dir = os.path.join("data", "raw", "entsoe_advanced")
    os.makedirs(output_dir, exist_ok=True)
    
    all_data = []

    for country in COUNTRIES:
        print(f"\n--- Đang xử lý: {country} ---")
        # Kiểm tra Checkpoint
        temp_path = os.path.join(output_dir, f"entsoe_{country}_raw.csv")
        if os.path.exists(temp_path):
            print(f"  ⏭️ Đã tìm thấy dữ liệu bộ đệm cho {country}. Bỏ qua API.")
            df_country_all_years = pd.read_csv(temp_path, index_col='Datetime', parse_dates=True)
            all_data.append(df_country_all_years)
            continue
            
        country_df_list = []
        
        for year in YEARS:
            print(f"  -> Năm {year}...")
            start = pd.Timestamp(f'{year}-01-01', tz='UTC')
            end = pd.Timestamp(f'{year}-12-31 23:59:59', tz='UTC')
            
            # Lưu ý: Ở mô hình ELT Thuần túy, ta KHÔNG khởi tạo khung 1H nữa.
            # Ta sẽ lấy Outer Join của tất cả các API call để giữ nguyên timestamp gốc.
            df_year = pd.DataFrame()
            
            # 1. Load Forecast
            try:
                load_fc = client.query_load_forecast(country, start=start, end=end)
                if isinstance(load_fc, pd.Series):
                    load_fc = load_fc.to_frame(name='Forecasted_Load')
                # Không resample. Chỉ join
                if df_year.empty:
                    df_year = load_fc
                else:
                    df_year = df_year.join(load_fc, how='outer')
                time.sleep(1)
            except Exception as e:
                pass # Không có dữ liệu thì không tạo cột
                
            # 2. Wind and Solar Forecast
            try:
                ws_fc = client.query_wind_and_solar_forecast(country, start=start, end=end)
                # Đổi tên cột để rõ ràng hơn
                ws_fc = ws_fc.add_prefix('Forecast_')
                if df_year.empty:
                    df_year = ws_fc
                else:
                    df_year = df_year.join(ws_fc, how='outer')
                time.sleep(1)
            except Exception as e:
                pass
                
            # 3. Water Reservoirs
            try:
                hydro = client.query_aggregate_water_reservoirs_and_hydro_storage(country, start=start, end=end)
                # Không resample, không ffill.
                if df_year.empty:
                    df_year = hydro
                else:
                    df_year = df_year.join(hydro, how='outer')
                time.sleep(1)
            except Exception as e:
                pass
                
            if not df_year.empty:
                df_year['Country'] = country
                country_df_list.append(df_year)
            
        # Gộp các năm của quốc gia này
        if country_df_list:
            df_country_all_years = pd.concat(country_df_list)
            df_country_all_years.index.name = 'Datetime'
            # Lưu tạm checkpoint
            df_country_all_years.to_csv(temp_path)
            all_data.append(df_country_all_years)
            
    if all_data:
        df_final = pd.concat(all_data)
        out_path = os.path.join("data", "raw", "entsoe_advanced_features_raw.csv")
        df_final.to_csv(out_path)
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [OK] HOÀN TẤT TẢI ENTSO-E ADVANCED (ELT PURE)! Kích thước: {df_final.shape}")
        
if __name__ == "__main__":
    fetch_entsoe_advanced()
