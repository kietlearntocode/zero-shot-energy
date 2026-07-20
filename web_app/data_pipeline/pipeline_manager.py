"""
pipeline_manager.py -- Công cụ kiểm tra, lấy dữ liệu và huấn luyện AI hằng ngày
=============================================================================
Bạn có thể cài đặt script này vào Windows Task Scheduler hoặc Linux Cron
để chạy mỗi ngày lúc 00:00. Hoặc chạy thủ công bằng lệnh:
    python pipeline_manager.py
"""
import sys
import os
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, '../ai_model'))

import sync_daily
import build_daily_features
import train_daily

def run_pipeline():
    print('============================================================')
    print(f'PIPELINE MANAGER - Bắt đầu lúc: {datetime.now()}')
    print('============================================================')
    
    # 1. Kiểm tra xem có cần lấy dữ liệu không (Tiến trình kiểm tra)
    last_dt = sync_daily.get_last_datetime()
    now_dt = pd.Timestamp.now(tz="UTC").floor("h")
    
    if (now_dt - last_dt).days <= 0:
        print(f'[✓] Dữ liệu đã là mới nhất (tới {last_dt}). Không cần đồng bộ.')
        return
        
    print(f'[!] Dữ liệu cũ nhất từ {last_dt.date()}. Bắt đầu đồng bộ...')
    
    # 2. Chạy Sync API để fetch dữ liệu 1 ngày (hoặc số ngày bị gap)
    sync_daily.sync()
    
    # 3. Tính toán lại đặc trưng (Feature Engineering)
    print('\n[+] Bắt đầu tính toán đặc trưng (Feature Engineering)...')
    build_daily_features.main()
    
    # 4. Huấn luyện lại mô hình XGBoost
    print('\n[+] Bắt đầu huấn luyện lại mô hình XGBoost (Retrain)...')
    train_daily.main()
    
    print('\n============================================================')
    print('[✓] PIPELINE HOÀN TẤT. Dữ liệu và mô hình AI đã được cập nhật!')
    print('============================================================')

if __name__ == "__main__":
    run_pipeline()
