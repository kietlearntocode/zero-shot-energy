import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import os
from datetime import datetime
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

def fetch_and_compare_ie():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu chiến dịch tìm nguồn phụ (ENTSO-E) cho Ireland (IE)...")
    
    # 1. Kiểm tra API Key (Cơ chế Fail-Fast)
    load_dotenv()
    api_key = os.getenv('ENTSOE_API_KEY')
    if not api_key:
        print("[ERROR] LỖI: Không tìm thấy ENTSOE_API_KEY trong file .env.")
        print("   Theo quy tắc 'Graceful Degradation', tiến trình tự động dừng lại an toàn.")
        return

    client = EntsoePandasClient(api_key=api_key)
    start = pd.Timestamp('2018-01-01', tz='UTC')
    end = pd.Timestamp('2025-12-31 23:00', tz='UTC')
    country_code = 'IE'

    print(f" -> Đang tải toàn bộ dữ liệu Day-Ahead Price của {country_code} từ {start.date()} đến {end.date()}...")
    try:
        df_new = client.query_day_ahead_prices(country_code, start=start, end=end)
        df_new = df_new.to_frame(name='Price_EUR')
        df_new.index.name = 'Datetime'
        df_new = df_new.reset_index()
        df_new['Country'] = country_code
        print(f"   [OK] Tải thành công {len(df_new)} dòng từ ENTSO-E.")
    except Exception as e:
        print(f"   [ERROR] Lỗi khi tải từ ENTSO-E: {e}")
        print("   -> LÝ DO VẬT LÝ: Thị trường I-SEM (Integrated Single Electricity Market) của Ireland chỉ chính thức hoạt động từ ngày 01/10/2018. Do đó, API Châu Âu KHÔNG TỒN TẠI dữ liệu Day-Ahead Price định dạng chuẩn trước mốc này.")
        return

    # 2. So sánh với Ember
    raw_dir = os.path.join("data", "raw")
    ember_path = os.path.join(raw_dir, "ember_wholesale_price_eu17_2018_2025.csv")
    df_ember = pd.read_csv(ember_path, low_memory=False)
    df_ember['Datetime'] = pd.to_datetime(df_ember['Datetime'], utc=True)
    
    ie_ember = df_ember[df_ember['Country'] == 'IE'].copy()
    print(f" -> Tập Ember hiện tại có {len(ie_ember)} dòng cho IE.")

    # 3. So sánh khoảng chồng lấp
    merged = pd.merge(ie_ember, df_new, on=['Datetime', 'Country'], how='inner', suffixes=('_ember', '_new'))
    
    if len(merged) == 0:
        print("   [ERROR] Không có điểm chồng lấp nào để so sánh.")
        return
        
    diff = (merged['Price_EUR_ember'] - merged['Price_EUR_new']).abs().max()
    print(f" -> Độ lệch tối đa (Max Diff) giữa Ember và Nguồn mới: {diff:.4f} EUR")

    if diff < 0.01:
        print("   [OK] Trùng khớp toàn bộ! Tiến hành thay thế dữ liệu IE trong tập Ember...")
        df_ember_other = df_ember[df_ember['Country'] != 'IE']
        df_ember_new = pd.concat([df_ember_other, df_new], ignore_index=True)
        df_ember_new.to_csv(ember_path, index=False)
        print("   🎉 Đã thay thế thành công dữ liệu Ireland!")
    else:
        print("   [ERROR] Không trùng khớp toàn bộ. Giữ nguyên Ember.")

if __name__ == "__main__":
    fetch_and_compare_ie()
