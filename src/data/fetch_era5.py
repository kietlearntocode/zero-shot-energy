import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import requests_cache
from retry_requests import retry
import openmeteo_requests
import time
from datetime import datetime

CITY_COORDS = {
    'DE': [(52.52, 13.41), (48.13, 11.58), (50.11, 8.68)], # Berlin, Munich, Frankfurt
    'FR': [(48.85, 2.35), (45.76, 4.83), (43.30, 5.37)],   # Paris, Lyon, Marseille
    'NL': [(52.37, 4.89), (51.92, 4.48), (52.07, 4.30)],   # Amsterdam, Rotterdam, The Hague
    'BE': [(50.85, 4.35), (51.22, 4.40), (51.05, 3.72)],   # Brussels, Antwerp, Ghent
    'PL': [(52.23, 21.01), (50.06, 19.94), (51.76, 19.45)],# Warsaw, Krakow, Lodz
    'CZ': [(50.08, 14.42), (49.19, 16.61), (49.83, 18.28)],# Prague, Brno, Ostrava
    'SK': [(48.15, 17.11), (48.72, 21.26), (49.00, 21.24)],# Bratislava, Kosice, Presov
    'HU': [(47.50, 19.04), (47.53, 21.62), (46.25, 20.15)],# Budapest, Debrecen, Szeged
    'ES': [(40.42, -3.70), (41.39, 2.16), (39.47, -0.38)], # Madrid, Barcelona, Valencia
    'PT': [(38.72, -9.14), (41.15, -8.61), (41.55, -8.43)],# Lisbon, Porto, Braga
    'IT': [(41.90, 12.50), (45.46, 9.19), (40.85, 14.27)], # Rome, Milan, Naples
    'NO': [(59.91, 10.75), (60.39, 5.32), (63.43, 10.39)], # Oslo, Bergen, Trondheim
    'SE': [(59.33, 18.06), (57.71, 11.97), (55.61, 13.00)],# Stockholm, Gothenburg, Malmo
    'FI': [(60.17, 24.94), (61.50, 23.79), (60.45, 22.27)],# Helsinki, Tampere, Turku
    'DK': [(55.68, 12.57), (56.16, 10.20), (55.40, 10.39)],# Copenhagen, Aarhus, Odense
    'GB': [(51.51, -0.13), (52.48, -1.90), (53.48, -2.24)],# London, Birmingham, Manchester
    'IE': [(53.35, -6.26), (51.90, -8.47), (52.66, -8.63)] # Dublin, Cork, Limerick
}

def fetch_era5(start_date="2018-01-01", end_date="2025-12-31"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu cào dữ liệu Khí tượng ERA5 (17 quốc gia) từ {start_date} đến {end_date}")
    
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://archive-api.open-meteo.com/v1/archive"

    all_countries_dfs = []

    for country, coords in CITY_COORDS.items():
        print(f"\n--- Đang xử lý quốc gia: {country} ({len(coords)} thành phố proxy) ---")
        city_dfs = []
        for i, (lat, lon) in enumerate(coords):
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation,cloud_cover,precipitation,snow_depth"
            }
            try:
                responses = openmeteo.weather_api(url, params=params)
                response = responses[0]
                hourly = response.Hourly()
                
                temp = hourly.Variables(0).ValuesAsNumpy()
                wind = hourly.Variables(1).ValuesAsNumpy()
                solar = hourly.Variables(2).ValuesAsNumpy()
                cloud = hourly.Variables(3).ValuesAsNumpy()
                precip = hourly.Variables(4).ValuesAsNumpy()
                snow = hourly.Variables(5).ValuesAsNumpy()
                
                time_index = pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                )
                df_city = pd.DataFrame(data={
                    f"Temperature_{i}": temp,
                    f"Wind_Speed_{i}": wind,
                    f"Solar_Irradiance_{i}": solar,
                    f"Cloud_Cover_{i}": cloud,
                    f"Precipitation_{i}": precip,
                    f"Snow_Depth_{i}": snow
                }, index=time_index)
                
                city_dfs.append(df_city)
                print(f"     [OK] Thành phố {i+1} tải xong: {len(df_city)} dòng.")
                time.sleep(12) # Chờ 12 giây để không vượt quá 5 request/phút (giới hạn minutely của Open-Meteo cho IP chưa đăng ký)
            except Exception as e:
                print(f"     [ERROR] Lỗi thành phố {i+1} ({lat}, {lon}): {e}")
                time.sleep(20) # Chờ lâu hơn nếu dính lỗi Rate Limit
                pass
            
            time.sleep(5) # Tăng delay lên 5s để tránh Rate limit của Open-Meteo
            
        if city_dfs:
            # Gộp các thành phố và tính trung bình đại diện cho Country
            df_country = pd.concat(city_dfs, axis=1)
            
            # Tính mean cho từng biến
            df_final_country = pd.DataFrame(index=df_country.index)
            for var in ['Temperature', 'Wind_Speed', 'Solar_Irradiance', 'Cloud_Cover', 'Precipitation', 'Snow_Depth']:
                cols = [c for c in df_country.columns if c.startswith(var)]
                df_final_country[var] = df_country[cols].mean(axis=1)
                
            df_final_country['Country'] = country
            df_final_country = df_final_country.reset_index().rename(columns={'index': 'Datetime'})
            
            all_countries_dfs.append(df_final_country)
            print(f"     [OK] Tính trung bình quốc gia {country} thành công.")

    if all_countries_dfs:
        df_final = pd.concat(all_countries_dfs, ignore_index=True)
        output_dir = os.path.join("data", "raw")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"era5_eu17_raw.csv")
        df_final.to_csv(out_path, index=False)
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu file thành công: {out_path} ({df_final.shape[0]} dòng)")
        return out_path
    return None

if __name__ == "__main__":
    fetch_era5(start_date="2018-01-01", end_date="2025-12-31")
