import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from datetime import datetime
from entsoe import EntsoePandasClient
from dotenv import load_dotenv
import time

def fetch_hydro(start_year=2018, end_year=2025):
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))
    api_key = os.getenv('ENTSOE_API_KEY')
    if not api_key:
        print("[ERROR] ENTSOE_API_KEY không được tìm thấy.")
        return None
        
    client = EntsoePandasClient(api_key=api_key)
    
    # Chỉ tập trung vào các quốc gia có tỷ trọng thủy điện cực lớn / quan trọng
    HYDRO_COUNTRIES = ['NO', 'SE', 'AT', 'FR', 'ES']
    
    all_dfs = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu cào Hydro Reservoir từ ENTSO-E (Tập trung: NO, SE, AT, FR, ES)")
    
    for country in HYDRO_COUNTRIES:
        print(f"\\n--- Đang kéo Hydro Reservoir cho: {country} ---")
        country_dfs = []
        # Tải từng năm để tránh timeout
        for year in range(start_year, end_year + 1):
            start = pd.Timestamp(f'{year}-01-01', tz='Europe/Oslo')
            end = pd.Timestamp(f'{year+1}-01-01', tz='Europe/Oslo')
            
            try:
                # Dữ liệu tuần (Weekly)
                df_year = client.query_aggregate_water_reservoirs_and_hydro_storage(country, start=start, end=end)
                if not df_year.empty:
                    # Trả về series, cần chuyển sang dataframe
                    df_year = pd.DataFrame({'Hydro_Reservoir_Level': df_year})
                    country_dfs.append(df_year)
                    print(f"     [OK] Kéo năm {year} thành công ({df_year.shape[0]} tuần).")
                else:
                    print(f"     [WARN] Năm {year} không có dữ liệu.")
            except Exception as e:
                print(f"     [ERROR] Năm {year} lỗi: {e}")
            time.sleep(1) # Tránh Rate limit
            
        if country_dfs:
            df_country = pd.concat(country_dfs)
            # Remove duplicated indexes if any
            df_country = df_country[~df_country.index.duplicated(keep='first')]
            df_country['Country'] = country
            all_dfs.append(df_country)
            
    if all_dfs:
        df_final = pd.concat(all_dfs)
        df_final.index.name = 'Datetime'
        df_final = df_final.reset_index()
        
        output_dir = os.path.join("data", "raw")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"entsoe_hydro_raw.csv")
        df_final.to_csv(out_path, index=False)
        print(f"\\n[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu file thành công: {out_path} ({df_final.shape[0]} dòng)")
        return out_path
    else:
        print("[WARN] Không lấy được bất kỳ dữ liệu Hydro Reservoir nào.")
        return None

if __name__ == "__main__":
    fetch_hydro()
