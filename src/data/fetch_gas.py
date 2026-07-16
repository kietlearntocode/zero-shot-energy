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
from dotenv import load_dotenv

load_dotenv()

def fetch_gas_storage_yearly(country='EU', start_year=2018, end_year=2025):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Báº¯t Ä‘áº§u kÃ©o dá»¯ liá»‡u KhÃ­ Ä‘á»‘t tá»« GIE AGSI ({country}) tá»« {start_year} Ä‘áº¿n {end_year}")
    gie_key = os.environ.get("GIE_API_KEY", "")
    
    if not gie_key or gie_key == "your_gie_api_key_here":
        print("âŒ Lá»—i: KhÃ´ng tÃ¬m tháº¥y GIE_API_KEY trong file .env.")
        return None
        
    headers = {"x-key": gie_key}
    all_years_dfs = []
    
    for year in range(start_year, end_year + 1):
        print(f"  -> Äang táº£i dá»¯ liá»‡u nÄƒm {year}...")
        year_dfs = []
        
        # Chia lÃ m 2 ná»­a nÄƒm Ä‘á»ƒ lÃ¡ch luáº­t size=300 cá»§a API
        periods = [
            (f"{year}-01-01", f"{year}-06-30"),
            (f"{year}-07-01", f"{year}-12-31")
        ]
        
        for p_start, p_end in periods:
            if country.upper() == 'EU':
                url = f"https://agsi.gie.eu/api?type=eu&from={p_start}&to={p_end}&size=300"
            else:
                url = f"https://agsi.gie.eu/api?country={country}&from={p_start}&to={p_end}&size=300"
                
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'data' not in data or len(data['data']) == 0:
                        raise ValueError("API trả về phản hồi rỗng (0 dòng) dù không báo lỗi HTTP.")
                        
                    df = pd.DataFrame(data['data'])
                    year_dfs.append(df)
                    break
                except Exception as e:
                    print(f"     [WARN] Lỗi khoảng {p_start} đến {p_end} (Lần {attempt+1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        raise Exception(f"FAIL-FAST: Bắt buộc dừng tiến trình vì dữ liệu Gas rớt mạng liên tục!")
            time.sleep(2) # Nghỉ 2 giây để tránh Rate Limit
            
        if year_dfs:
            df_year = pd.concat(year_dfs)
            # Lọc các cột thiết yếu
            cols_to_keep = ['gasDayStart', 'full', 'trend', 'injection', 'withdrawal']
            df_year = df_year[[c for c in cols_to_keep if c in df_year.columns]]
            df_year['gasDayStart'] = pd.to_datetime(df_year['gasDayStart'])
            df_year.set_index('gasDayStart', inplace=True)
            
            # Bàn Tay Sắt: Kiểm tra năm đó có đủ 365/366 ngày không (chấp nhận sai số 2%)
            if df_year.shape[0] < 358:
                raise ValueError(f"Thiếu hụt dữ liệu Gas nghiêm trọng! Năm {year} chỉ có {df_year.shape[0]} ngày.")
                
            all_years_dfs.append(df_year)
            print(f"     [OK] {year} tải xong: {df_year.shape[0]} dòng.")
        else:
            raise Exception(f"FAIL-FAST: Hoàn toàn trống dữ liệu Gas năm {year}. Dừng tiến trình!")
        
    if all_years_dfs:
        df_final = pd.concat(all_years_dfs)
        df_final = df_final[~df_final.index.duplicated(keep='first')].sort_index()
        
        output_dir = os.path.join("data", "raw")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"gas_storage_{country}_{start_year}_{end_year}.csv")
        df_final.to_csv(out_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] âœ… LÆ°u file thÃ nh cÃ´ng: {out_path} ({df_final.shape[0]} dÃ²ng)")
        return out_path
    else:
        print("âŒ KhÃ´ng táº£i Ä‘Æ°á»£c báº¥t ká»³ dá»¯ liá»‡u khÃ­ Ä‘á»‘t nÃ o.")
        return None

if __name__ == "__main__":
    fetch_gas_storage_yearly()

