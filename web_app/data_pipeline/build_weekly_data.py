import pandas as pd
import numpy as np
import json
import os

def main():
    print("=== DATA PIPELINE: BUILD MULTI-COUNTRY WEEKLY DATA (WITH LAG FEATURES) ===")
    
    master_path = "../../data/processed/master_dataset_hourly.csv"
    if not os.path.exists(master_path):
        print(f"Lỗi: Không tìm thấy {master_path}")
        return
        
    print("Đang đọc dữ liệu Master (Hourly)...")
    df = pd.read_csv(master_path)
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    
    # 1. Điền khuyết dữ liệu
    df = df.sort_values(by=['Country', 'Datetime'])
    cols_to_fill = [c for c in df.columns if c not in ['Country', 'Datetime']]
    df[cols_to_fill] = df.groupby('Country')[cols_to_fill].ffill()
    
    # 2. Tính Residual Load cho TỪNG giờ, TỪNG nước
    df['Residual_Load'] = df['Load'] - df['Renewables_MW']
    
    # 3. Resample theo Tuần cho TỪNG Nước
    print("Đang Resample theo chuẩn Tuần (Weekly) cho từng Quốc gia...")
    
    weekly_list = []
    country_scalers = {}
    
    for country, group in df.groupby('Country'):
        group_ts = group.set_index('Datetime')
        weekly = group_ts.resample('W').mean(numeric_only=True).reset_index()
        weekly = weekly.dropna(subset=['Residual_Load', 'Real_Wholesale_Price_EUR'])
        if len(weekly) == 0:
            continue
            
        # Tính Min-Max Scaler riêng cho Quốc gia này
        res_min = float(weekly['Residual_Load'].min())
        res_max = float(weekly['Residual_Load'].max())
        
        if res_max == res_min:
            res_max = res_min + 1.0
            
        country_scalers[country] = {
            "min": res_min,
            "max": res_max
        }
        
        # Chuẩn hóa
        weekly['EU_Residual_Load_Normalized'] = (weekly['Residual_Load'] - res_min) / (res_max - res_min)
        weekly['EU_Residual_Load_Normalized'] = weekly['EU_Residual_Load_Normalized'].clip(0, 1)
        
        # --- THÊM LAG FEATURES (Dữ liệu lịch sử) ---
        weekly['Price_Lag1'] = weekly['Real_Wholesale_Price_EUR'].shift(1)
        weekly['Price_Lag2'] = weekly['Real_Wholesale_Price_EUR'].shift(2)
        weekly['Residual_Load_Normalized_Lag1'] = weekly['EU_Residual_Load_Normalized'].shift(1)
        weekly['Residual_Load_Normalized_Lag2'] = weekly['EU_Residual_Load_Normalized'].shift(2)
        
        # Shift T+1 cho Target (Giá Tuần Tới)
        weekly['Next_Week_Price_EUR'] = weekly['Real_Wholesale_Price_EUR'].shift(-1)
        
        # Drop NaN do tạo Lag và Shift Target
        weekly = weekly.dropna(subset=[
            'Next_Week_Price_EUR', 
            'Price_Lag1', 'Price_Lag2', 
            'Residual_Load_Normalized_Lag1', 'Residual_Load_Normalized_Lag2'
        ])
        
        # Gắn lại nhãn quốc gia
        weekly['Country'] = country
        
        weekly_list.append(weekly)
        
    final_df = pd.concat(weekly_list, ignore_index=True)
    
    # Lưu Min-Max Scaler Dictionary
    scaler_dir = "../ai_model"
    os.makedirs(scaler_dir, exist_ok=True)
    with open(os.path.join(scaler_dir, "country_scalers.json"), "w") as f:
        json.dump(country_scalers, f, indent=4)
        
    print(f"Đã lưu Scaler của {len(country_scalers)} quốc gia.")
    
    # Lưu dữ liệu thô (đã sort theo thời gian) để API Server dùng tra cứu Lag!
    # Quan trọng: Không xáo trộn ở đây để API có thể tìm 2 tuần gần nhất.
    out_path = "weekly_zero_shot_data.csv"
    final_df.to_csv(out_path, index=False)
    
    print(f"[OK] Đã tạo thành công {out_path} ({len(final_df)} dòng)")
    print("Mẫu dữ liệu:")
    print(final_df[['Country', 'Datetime', 'Price_Lag1', 'Next_Week_Price_EUR']].head())

if __name__ == "__main__":
    main()
