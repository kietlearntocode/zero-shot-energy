import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import openmeteo_requests
import requests_cache
from retry_requests import retry
import pandas as pd
from datetime import datetime
import os
import numpy as np

def fetch_historical_weather(start_date="2008-01-01", end_date="2015-12-31"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu kéo dữ liệu Thời tiết quá khứ (Pure Extraction) từ {start_date} đến {end_date}")
    
    # Setup Open-Meteo API
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    # Tọa độ thủ đô của 17 quốc gia (Khớp với file fetch_weather)
    capitals = {
        'DE': (52.52, 13.41), 'FR': (48.85, 2.35), 'ES': (40.42, -3.70), 'IT': (41.89, 12.51),
        'NL': (52.37, 4.89), 'BE': (50.85, 4.35), 'PL': (52.23, 21.01), 'CZ': (50.08, 14.43),
        'SK': (48.15, 17.11), 'HU': (47.50, 19.04), 'PT': (38.72, -9.14), 'NO': (59.91, 10.75),
        'SE': (59.33, 18.06), 'FI': (60.17, 24.94), 'DK': (55.68, 12.57), 'GB': (51.51, -0.13),
        'IE': (53.34, -6.26)
    }

    all_dfs = []
    
    for country, (lat, lon) in capitals.items():
        print(f"  -> Đang tải {country}...")
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m",
            "timezone": "UTC"
        }
        try:
            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]
            
            hourly = response.Hourly()
            hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
            
            hourly_data = {"Datetime": pd.date_range(
                start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
                end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
                freq = pd.Timedelta(seconds = hourly.Interval()),
                inclusive = "left"
            )}
            hourly_data["Temperature_Past"] = hourly_temperature_2m
            
            df = pd.DataFrame(data = hourly_data)
            df['Country'] = country
            
            # Đã bỏ Fail-Fast theo luật Unbalanced Panel
            if df.shape[0] < 70000:
                print(f"     [WARN] [WARNING - UNBALANCED PANEL] Thiếu hụt dữ liệu! Chỉ có {df.shape[0]} dòng cho {country}. Chấp nhận NaN.")
                
            all_dfs.append(df)
            print(f"     [OK] Tải xong: {df.shape[0]} dòng.")
        except Exception as e:
            print(f"     [ERROR] Lỗi tại {country}: {e}. Chấp nhận bỏ qua theo luật Unbalanced Panel.")
            pass
            
    df_final = pd.concat(all_dfs, ignore_index=True)
    
    output_dir = os.path.join("data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"weather_historical_2008_2015_raw.csv")
    df_final.to_csv(out_path, index=False)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu thành công file Thời tiết quá khứ: {out_path} ({df_final.shape[0]} dòng)")
    return out_path

if __name__ == "__main__":
    fetch_historical_weather()
