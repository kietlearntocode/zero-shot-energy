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

def fetch_energy_charts_yearly(countries=None, start_year=2018, end_year=2025):
    if countries is None:
        countries = ['de', 'fr', 'nl', 'be', 'pl', 'cz', 'sk', 'hu', 'es', 'pt', 'it', 'no', 'se', 'fi', 'dk', 'gb', 'ie']
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Báº¯t Ä‘áº§u kÃ©o dá»¯ liá»‡u NÄƒng lÆ°á»£ng tá»« Energy-Charts ({len(countries)} quá»‘c gia) tá»« {start_year} Ä‘áº¿n {end_year}")
    
    all_countries_dfs = []
    
    for country in countries:
        print(f"\n--- Ä ang xá»­ lÃ½ quá»‘c gia: {country.upper()} ---")
        
        # Cơ chế Checkpoint: Nếu đã tải thành công quốc gia này, bỏ qua để tiết kiệm thời gian
        os.makedirs("data/raw/temp_energy", exist_ok=True)
        temp_file = f"data/raw/temp_energy/energy_{country}.csv"
        if os.path.exists(temp_file):
            print(f"  ⏭️ Đã tìm thấy dữ liệu bộ đệm cho {country.upper()}. Bỏ qua API.")
            df_country = pd.read_csv(temp_file, index_col='Datetime', parse_dates=True)
            all_countries_dfs.append(df_country)
            continue
            
        country_dfs = []
    
        # Energy-Charts sử dụng mã 'uk' thay vì 'gb'
        api_country = 'uk' if country == 'gb' else country
    
        for year in range(start_year, end_year + 1):
            print(f"  -> Ä ang táº£i dá»¯ liá»‡u nÄƒm {year}...")
            start_time = f"{year}-01-01T00:00Z"
            end_time = f"{year}-12-31T23:59Z"
            
            url = f"https://api.energy-charts.info/public_power?country={api_country}&start={start_time}&end={end_time}"
            
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    
                    times = pd.to_datetime(data['unix_seconds'], unit='s', utc=True)
                    df_year = pd.DataFrame(index=times)
                    
                    for prod_type in data.get('production_types', []):
                        df_year[prod_type['name']] = prod_type['data']
                    
                    min_rows_required = 8322
                    if df_year.shape[0] < min_rows_required:
                        print(f"     [WARN] [WARNING - UNBALANCED PANEL] Thiếu hụt dữ liệu! Chỉ tải được {df_year.shape[0]} dòng cho {country.upper()} năm {year}. Tiếp tục giữ dữ liệu thiếu làm NaN.")
                        
                    country_dfs.append(df_year)
                    print(f"     [OK] {year} tải xong và vượt qua kiểm định: {df_year.shape[0]} dòng.")
                    break
                except Exception as e:
                    print(f"     [WARN] Lỗi năm {year} ({country.upper()}) lần {attempt+1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(10)
                    else:
                        print(f"     [ERROR] Thất bại hoàn toàn kéo {year} ({country.upper()}). Hệ thống áp dụng luật Unbalanced Panel: Điền NaN cho mảng này và tiếp tục.")
                        # Tạo một DataFrame trống (hoặc bỏ qua) để ghép nối sau này
                        pass
                
            time.sleep(4)
            
        if country_dfs:
            df_country = pd.concat(country_dfs)
            df_country['Country'] = country.upper()
            df_country.index.name = 'Datetime'
            # Lưu ngay xuống ổ cứng để làm Checkpoint chống sập
            df_country.to_csv(temp_file)
            all_countries_dfs.append(df_country)
            
    if all_countries_dfs:
        df_final = pd.concat(all_countries_dfs)
        df_final.index.name = 'Datetime'
        df_final = df_final.reset_index()
        # Drop duplicate timestamps per country
        df_final = df_final.drop_duplicates(subset=['Datetime', 'Country']).set_index('Datetime').sort_index()
        
        output_dir = os.path.join("data", "raw")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"energy_generation_eu17_raw.csv")
        df_final.to_csv(out_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] âœ… LÆ°u file thÃ nh cÃ´ng: {out_path} ({df_final.shape[0]} dÃ²ng)")
        return out_path
    else:
        print("âŒ KhÃ´ng táº£i Ä‘Æ°á»£c báº¥t ká»³ dá»¯ liá»‡u nÃ o.")
        return None

if __name__ == "__main__":
    fetch_energy_charts_yearly()

