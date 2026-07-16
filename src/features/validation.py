import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd

def validate_dataset(df, time_col='Datetime', frequency='1h'):
    print("\n--- BÁO CÁO KIỂM TOÁN CHẤT LƯỢNG (VALIDATION SCAN) ---")
    
    if df.empty:
        print("[ERROR] LỖI: Dataset trống rỗng!")
        return False
        
    # 1. Check Timezone (UTC)
    tz = df[time_col].dt.tz
    if tz is None or str(tz) != 'UTC':
        print(f"[ERROR] LỖI: Cột {time_col} không phải định dạng UTC. Hiện tại là: {tz}")
        return False
    print(f"[OK] Timezone Check: Pass ({tz})")
    
    # 2. Check Missing Values
    print("\n[Tình trạng Dữ liệu Khuyết - NaN]")
    missing = df.isnull().sum()
    has_missing = False
    for col, count in missing.items():
        if count > 0:
            print(f"   [WARN] {col}: {count} dòng bị thiếu (Sẽ được giữ nguyên theo luật Unbalanced Panel)")
            has_missing = True
    if not has_missing:
        print("   [OK] Không có dữ liệu khuyết.")
    print("[OK] NaN Policy Check: Pass (Đã ghi nhận dữ liệu khuyết, nếu có)")
    
    # 3. Check Frequency
    # Để check frequency cho Panel Data, ta phải check theo từng quốc gia
    if 'Country' in df.columns:
        countries = df['Country'].unique()
        for c in countries:
            df_c = df[df['Country'] == c].sort_values(time_col)
            time_diff = df_c[time_col].diff().dropna()
            expected_diff = pd.Timedelta(frequency)
            if not all(time_diff == expected_diff):
                print(f"[ERROR] LỖI: Khoảng cách thời gian bị đứt gãy tại quốc gia {c}. Tần suất không phải là {frequency}.")
                return False
    else:
        df_sorted = df.sort_values(time_col)
        time_diff = df_sorted[time_col].diff().dropna()
        expected_diff = pd.Timedelta(frequency)
        if not all(time_diff == expected_diff):
            print(f"[ERROR] LỖI: Khoảng cách thời gian bị đứt gãy. Tần suất không phải là {frequency}.")
            return False
            
    print(f"[OK] Frequency Check: Pass (Mạch thời gian {frequency} liên tục tuyệt đối)")
    print("--- KẾT THÚC KIỂM TOÁN ---\n")
    return True

def resample_hourly_by_country(df, time_col, method='mean'):
    if df.empty: return df
    df = df.drop_duplicates(subset=[time_col, 'Country'], keep='last')
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df = df.set_index(time_col)
    if method == 'mean':
        df_resampled = df.groupby('Country').resample('1h').mean(numeric_only=True).reset_index()
    elif method == 'ffill':
        df_resampled = df.groupby('Country').resample('1h').ffill().reset_index()
    return df_resampled
