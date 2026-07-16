import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import numpy as np
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.features.validation import validate_dataset, resample_hourly_by_country

def process_energy():
    print("--- CHẠY MODULE: PROCESS ENERGY ---")
    raw_dir = os.path.join("data", "raw")
    interim_dir = os.path.join("data", "interim")
    os.makedirs(interim_dir, exist_ok=True)
    
    raw_path = os.path.join(raw_dir, "energy_generation_eu17_raw.csv")
    if not os.path.exists(raw_path):
        print(f"[ERROR] Không tìm thấy file {raw_path}")
        return
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    # 1. Ép kiểu và lọc thời gian
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df = df[df['Datetime'].dt.year >= 2018]
    
    # 2. Re-sample (Mean)
    df_resampled = resample_hourly_by_country(df, 'Datetime', 'mean')
    
    # 3. Tính toán Năng lượng — 2 tầng: tổng hợp + nguyên tử
    # ============================================================
    # TẦNG TỔNG HỢP (cho Residual_Load và Dominant_Source)
    renewables = ['Wind offshore', 'Wind onshore', 'Solar', 'Biomass', 'Geothermal']
    hydro = ['Hydro Run-of-River', 'Hydro water reservoir']
    fossil = ['Fossil coal-derived gas', 'Fossil gas', 'Fossil hard coal', 'Fossil brown coal / lignite', 'Fossil oil']
    nuclear = ['Nuclear']
    
    cols = df_resampled.columns
    df_resampled['Renewables_MW'] = df_resampled[[c for c in renewables if c in cols]].sum(axis=1, min_count=1)
    df_resampled['Hydro_MW'] = df_resampled[[c for c in hydro if c in cols]].sum(axis=1, min_count=1)
    df_resampled['Fossil_MW'] = df_resampled[[c for c in fossil if c in cols]].sum(axis=1, min_count=1)
    df_resampled['Nuclear_MW'] = df_resampled[[c for c in nuclear if c in cols]].sum(axis=1, min_count=1)
    
    # ============================================================
    # TẦNG NGUYÊN TỬ (biến thực tế vào mô hình)
    # Mỗi nguồn có cơ chế ảnh hưởng giá riêng:
    #   Wind_Onshore:     biến thiên mạnh, phổ biến tất cả nước
    #   Wind_Offshore:    biến thiên mạnh, chỉ DE/DK/FR có đáng kể
    #   Solar:            chỉ ban ngày → "đường cong vịt"
    #   Biomass:          gần base-load, ổn định (DE rất lớn: 4,400 MW)
    #   Geothermal:       base-load, chỉ IT có (628 MW)
    #   Hydro_RoR:        dòng chảy tự nhiên — KHÔNG điều phối được (giống gió)
    #   Hydro_Reservoir:  hồ chứa — ĐIỀU PHỐI ĐƯỢC (giống hạt nhân)
    # ============================================================
    atomic_map = {
        'Wind_Onshore_MW':    ['Wind onshore'],
        'Wind_Offshore_MW':   ['Wind offshore'],
        'Solar_MW':           ['Solar'],
        'Biomass_MW':         ['Biomass'],
        'Geothermal_MW':      ['Geothermal'],
        'Hydro_RoR_MW':       ['Hydro Run-of-River'],
        'Hydro_Reservoir_MW': ['Hydro water reservoir'],
        # Fossil atomic (Chỉ để Phân tích (Analytics), KHÔNG ĐƯỢC CHẠY ML)
        'Fossil_Gas_MW':      ['Fossil gas'],
        'Fossil_Hard_Coal_MW':['Fossil hard coal'],
        'Fossil_Brown_Coal_MW':['Fossil brown coal / lignite'],
        'Fossil_Oil_MW':      ['Fossil oil']
    }
    for new_col, raw_cols in atomic_map.items():
        available = [c for c in raw_cols if c in cols]
        if available:
            df_resampled[new_col] = df_resampled[available].sum(axis=1, min_count=1)
        else:
            df_resampled[new_col] = 0.0
    
    # Tính năng mở rộng
    if 'Cross border electricity trading' in cols:
        df_resampled.rename(columns={'Cross border electricity trading': 'Net_Import'}, inplace=True)
        
    if 'Hydro pumped storage' in cols and 'Hydro pumped storage consumption' in cols:
        df_resampled['Pumped_Storage_Activity'] = df_resampled['Hydro pumped storage'] - df_resampled['Hydro pumped storage consumption']
        
    # Nguồn thống trị (Dominant Source)
    sources = df_resampled[['Renewables_MW', 'Fossil_MW', 'Nuclear_MW']]
    valid_mask = sources.notna().any(axis=1)
    df_resampled['Dominant_Source'] = pd.Series(None, dtype='object', index=df_resampled.index)
    df_resampled.loc[valid_mask, 'Dominant_Source'] = sources.loc[valid_mask].idxmax(axis=1).str.replace('_MW', '')
    
    # Rút gọn cột — giữ cả tổng hợp (cho Residual_Load) và nguyên tử (cho mô hình)
    keep_cols = [
        'Datetime', 'Country',
        # Tổng hợp (tính Residual_Load, không vào model trực tiếp)
        'Renewables_MW', 'Hydro_MW', 'Fossil_MW', 'Nuclear_MW',
        # Nguyên tử (vào model)
        'Wind_Onshore_MW', 'Wind_Offshore_MW', 'Solar_MW',
        'Biomass_MW', 'Geothermal_MW',
        'Hydro_RoR_MW', 'Hydro_Reservoir_MW',
        # Hóa thạch nguyên tử (Chỉ phân tích nhiên liệu, tránh Data Leakage)
        'Fossil_Gas_MW', 'Fossil_Hard_Coal_MW', 'Fossil_Brown_Coal_MW', 'Fossil_Oil_MW',
        # Khác
        'Net_Import', 'Pumped_Storage_Activity', 'Dominant_Source', 'Load'
    ]
    df_final = df_resampled[[c for c in keep_cols if c in df_resampled.columns]].copy()
    
    # 4. Quét lỗi (Validation)
    if validate_dataset(df_final, time_col='Datetime', frequency='1h'):
        output_path = os.path.join(interim_dir, "processed_energy.csv")
        df_final.to_csv(output_path, index=False)
        print(f"[OK] Đã lưu file Interim: {output_path}")
    else:
        print("[ERROR] Dữ liệu không vượt qua Validation Scan. Hủy lưu file.")

if __name__ == "__main__":
    process_energy()
