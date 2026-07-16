import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import pandas as pd
import time
from datetime import datetime
import os

def fetch_gb_energy():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu tải bù dữ liệu Năng lượng cho GB (Vương quốc Anh) sử dụng mã 'uk'")
    country_dfs = []
    
    for year in range(2018, 2026):
        print(f"  -> Đang tải dữ liệu năm {year}...")
        start_time = f"{year}-01-01T00:00Z"
        end_time = f"{year}-12-31T23:59Z"
        
        url = f"https://api.energy-charts.info/public_power?country=uk&start={start_time}&end={end_time}"
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 429:
                    print(f"     [WARN] Lỗi Rate Limit 429 lần {attempt+1}, chờ 15s...")
                    time.sleep(15)
                    continue
                response.raise_for_status()
                data = response.json()
                
                times = pd.to_datetime(data['unix_seconds'], unit='s', utc=True)
                df_year = pd.DataFrame(index=times)
                
                for prod_type in data.get('production_types', []):
                    df_year[prod_type['name']] = prod_type['data']
                
                country_dfs.append(df_year)
                print(f"     [OK] {year} tải xong: {df_year.shape[0]} dòng.")
                break
            except Exception as e:
                print(f"     [WARN] Lỗi năm {year} lần {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(15)
                else:
                    print(f"     [ERROR] Thất bại hoàn toàn kéo {year} cho GB.")
            
        time.sleep(5)
        
    if country_dfs:
        df_gb = pd.concat(country_dfs)
        df_gb['Country'] = 'GB'
        df_gb.index.name = 'Datetime'
        df_gb = df_gb.reset_index()
        df_gb = df_gb.drop_duplicates(subset=['Datetime', 'Country']).set_index('Datetime').sort_index()
        
        renewables = ['Wind offshore', 'Wind onshore', 'Solar', 'Biomass', 'Hydro Run-of-River', 'Geothermal']
        fossil = ['Fossil coal-derived gas', 'Fossil gas', 'Fossil hard coal', 'Fossil brown coal / lignite', 'Fossil oil']
        nuclear = ['Nuclear']
        
        cols = df_gb.columns
        df_gb['Renewables_MW'] = df_gb[[c for c in renewables if c in cols]].sum(axis=1)
        df_gb['Fossil_MW'] = df_gb[[c for c in fossil if c in cols]].sum(axis=1)
        df_gb['Nuclear_MW'] = df_gb[[c for c in nuclear if c in cols]].sum(axis=1)
        
        # Đọc file gốc và gộp
        master_file = os.path.join("data", "raw", "energy_generation_eu17_2018_2025.csv")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang đọc file gốc để nối thêm GB...")
        df_master = pd.read_csv(master_file, index_col='Datetime', parse_dates=True)
        
        df_final = pd.concat([df_master, df_gb])
        df_final.to_csv(master_file)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu file thành công: {master_file} (Tổng: {df_final.shape[0]} dòng)")
    else:
        print("[ERROR] Không tải được dữ liệu GB.")

if __name__ == "__main__":
    fetch_gb_energy()
