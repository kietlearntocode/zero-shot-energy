import pandas as pd
import os

print("Đang đọc master_dataset_hourly.csv (Có thể mất chút thời gian do file lớn)...")
df = pd.read_csv("data/processed/master_dataset_hourly.csv")

# Chuyển đổi thời gian
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)

# Sắp xếp và forward-fill các biến vĩ mô bị thiếu ở cuối chuỗi
df = df.sort_values(by=['Country', 'Datetime'])
cols_to_fill = [c for c in df.columns if c not in ['Country', 'Datetime']]
df[cols_to_fill] = df.groupby('Country')[cols_to_fill].ffill()

# Tính Residual Load
df['Residual_Load'] = df['Load'] - df['Renewables_MW']

# Chọn các cột cần thiết cho Dashboard
cols = [
    "Datetime", "Country", "Residual_Load", "Real_Wholesale_Price_EUR",
    "TTF_Gas_Price", "Coal_Price", "EU_ETS_Price", 
    "Brent_Oil_Price", "EU_Gas_Storage_Anomaly"
]
df_dashboard = df[cols].copy()
df_dashboard = df_dashboard.dropna() # Bỏ các hàng vẫn còn NaN

out_path = "data/processed/dashboard_data_17.csv"
df_dashboard.to_csv(out_path, index=False)
print(f"Đã lưu dữ liệu Dashboard cho 17 nước tại: {out_path}")
print(f"Số lượng quốc gia: {df_dashboard['Country'].nunique()}")
print(f"Kích thước file mới: {os.path.getsize(out_path) / 1024 / 1024:.2f} MB")
