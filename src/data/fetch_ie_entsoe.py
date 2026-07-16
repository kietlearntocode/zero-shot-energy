import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ENTSOE_API_KEY')
if not api_key:
    raise ValueError("ENTSOE_API_KEY not found in .env")

def fetch_entsoe_xml(start_str, end_str):
    domain = '10Y1001A1001A59C' # IE
    base_url = "https://web-api.tp.entsoe.eu/api"
    params = {
        'securityToken': api_key,
        'documentType': 'A44',
        'in_Domain': domain,
        'out_Domain': domain,
        'periodStart': start_str,
        'periodEnd': end_str
    }
    r = requests.get(base_url, params=params)
    if r.status_code != 200:
        raise Exception(f"API Error {r.status_code}: {r.text[:200]}")
    return r.text

def parse_entsoe_xml(xml_text):
    root = ET.fromstring(xml_text)
    ns = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}
    
    records = []
    
    for ts in root.findall('.//ns:TimeSeries', ns):
        period = ts.find('ns:Period', ns)
        if period is not None:
            time_interval = period.find('ns:timeInterval', ns)
            start_time_str = time_interval.find('ns:start', ns).text
            start_time = pd.to_datetime(start_time_str)
            
            resolution = period.find('ns:resolution', ns).text
            # PT30M -> 30 minutes, PT60M -> 60 minutes
            res_minutes = 30 if '30M' in resolution else 60 if '60M' in resolution else 60
            
            for p in period.findall('ns:Point', ns):
                pos = int(p.find('ns:position', ns).text)
                price = float(p.find('ns:price.amount', ns).text)
                
                # Position is 1-indexed. pos=1 means the period from start_time to start_time + res
                dt = start_time + pd.Timedelta(minutes=(pos - 1) * res_minutes)
                records.append({'Datetime': dt, 'Price': price})
                
    return pd.DataFrame(records)

def main():
    print("Bắt đầu vá dữ liệu Ireland 2018 từ ENTSO-E API...")
    
    # We need from 2018-01-01 to 2018-10-01
    # Fetch month by month to avoid timeout or large payload limits
    date_ranges = [
        ('201801010000', '201802010000'),
        ('201802010000', '201803010000'),
        ('201803010000', '201804010000'),
        ('201804010000', '201805010000'),
        ('201805010000', '201806010000'),
        ('201806010000', '201807010000'),
        ('201807010000', '201808010000'),
        ('201808010000', '201809010000'),
        ('201809010000', '201810010000'),
    ]
    
    all_df = []
    
    for start_str, end_str in date_ranges:
        print(f" -> Fetching {start_str[:8]} to {end_str[:8]}...")
        xml_data = fetch_entsoe_xml(start_str, end_str)
        df_month = parse_entsoe_xml(xml_data)
        all_df.append(df_month)
        
    df_ie = pd.concat(all_df, ignore_index=True)
    df_ie = df_ie.sort_values('Datetime').drop_duplicates(subset=['Datetime'])
    
    print(f"Tổng số điểm dữ liệu 30-phút cào được: {len(df_ie)}")
    
    # Resample to 1 Hour
    df_ie = df_ie.set_index('Datetime')
    df_ie_hourly = df_ie.resample('1h').mean().reset_index()
    
    print(f"Số lượng dòng 1-Giờ sau Resample: {len(df_ie_hourly)}")
    
    # Kiểm tra Bàn Tay Sắt (Fail-Fast)
    expected_hours = 6552 # 273 days from Jan 1 to Oct 1 = 6552 hours
    missing_count = df_ie_hourly['Price'].isna().sum()
    
    print(f"Số dòng bị khuyết (NaN) sau khi chuyển về 1H: {missing_count}")
    if missing_count > 0:
        print("CẢNH BÁO: Dữ liệu ENTSO-E cũng bị thủng lỗ! Không đủ tiêu chuẩn ghép nối.")
        # Print the missing timestamps
        missing_dts = df_ie_hourly[df_ie_hourly['Price'].isna()]['Datetime']
        print(missing_dts.head())
        # Raise exception according to Fail-Fast rule
        raise Exception(f"Bàn Tay Sắt: Lỗi khuyết {missing_count} giờ dữ liệu từ ENTSO-E. Phải chuyển sang Phương án 1 (Drop IE).")
        
    print("Dữ liệu HOÀN HẢO! Đang lưu thành file bổ sung...")
    df_ie_hourly['Country'] = 'IE'
    df_ie_hourly = df_ie_hourly[['Datetime', 'Country', 'Price']]
    
    os.makedirs(os.path.join("data", "interim"), exist_ok=True)
    df_ie_hourly.to_csv(os.path.join("data", "interim", "ie_supplement_2018.csv"), index=False)
    print("Đã lưu `ie_supplement_2018.csv`.")

if __name__ == "__main__":
    main()
