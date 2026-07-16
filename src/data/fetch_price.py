import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import requests
import zipfile
import io
import os
from datetime import datetime

def fetch_ember_price(start_year=2018, end_year=2025):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu kéo dữ liệu Lõi: Giá điện Ember (Hourly) từ {start_year} đến {end_year}")
    
    url = "https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_hourly.zip"
    output_dir = os.path.join("data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print("  -> Đang tải file ZIP từ máy chủ Ember (Quá trình này có thể mất vài phút vì file khá nặng)...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Đọc ZIP từ memory
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = z.namelist()[0] # Lấy tên file CSV đầu tiên trong ZIP
            print(f"  -> Đang giải nén và đọc file CSV: {csv_filename}...")
            
            with z.open(csv_filename) as f:
                df = pd.read_csv(f)
                
        print(f"  -> Đọc thành công file gốc, kích thước: {df.shape}")
        
        # Lọc dữ liệu
        print("  -> Đang lọc dữ liệu cho 17 quốc gia EU và khung thời gian yêu cầu...")
        
        # Đảm bảo cột Datetime chuẩn hóa
        df['Datetime (UTC)'] = pd.to_datetime(df['Datetime (UTC)'], utc=True)
        df = df[(df['Datetime (UTC)'].dt.year >= start_year) & (df['Datetime (UTC)'].dt.year <= end_year)]
        
        target_countries = ['Germany', 'France', 'Netherlands', 'Belgium', 'Poland', 'Czechia', 'Slovakia', 
                            'Hungary', 'Spain', 'Portugal', 'Italy', 'Norway', 'Sweden', 'Finland', 'Denmark', 
                            'United Kingdom', 'Ireland']
        
        # Trong dữ liệu Ember, cột quốc gia là 'Country'
        if 'Country' in df.columns:
            df = df[df['Country'].isin(target_countries)]
        
        # Map tên quốc gia về chuẩn ISO-2 để đồng nhất với các module khác
        country_map = {
            'Germany': 'DE', 'France': 'FR', 'Netherlands': 'NL', 'Belgium': 'BE', 'Poland': 'PL',
            'Czechia': 'CZ', 'Slovakia': 'SK', 'Hungary': 'HU', 'Spain': 'ES', 'Portugal': 'PT',
            'Italy': 'IT', 'Norway': 'NO', 'Sweden': 'SE', 'Finland': 'FI', 'Denmark': 'DK',
            'United Kingdom': 'GB', 'Ireland': 'IE'
        }
        df['Country_Code'] = df['Country'].map(country_map)
        
        # Đổi tên cột cho chuẩn mực
        df.rename(columns={'Price (EUR/MWhe)': 'Wholesale_Price_EUR', 'Datetime (UTC)': 'Datetime'}, inplace=True)
        
        # Lọc lấy các cột cần thiết
        df_final = df[['Datetime', 'Country_Code', 'Wholesale_Price_EUR']]
        df_final.rename(columns={'Country_Code': 'Country'}, inplace=True)
        
        # Sắp xếp và lưu file
        df_final.sort_values(by=['Country', 'Datetime'], inplace=True)
        out_path = os.path.join(output_dir, f"ember_wholesale_price_eu17_{start_year}_{end_year}.csv")
        df_final.to_csv(out_path, index=False)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Tải hoàn tất! Kích thước dữ liệu Lõi: {df_final.shape}")
        print(f"  -> File lưu tại: {out_path}")
        
    except Exception as e:
        print(f"[ERROR] Lỗi tải dữ liệu Giá điện Ember: {e}")

if __name__ == "__main__":
    fetch_ember_price()
