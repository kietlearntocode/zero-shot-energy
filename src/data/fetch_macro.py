import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import requests
import os
from datetime import datetime
import time
import eurostat

def fetch_macro(start_year=2018, end_year=2025):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bắt đầu cào dữ liệu Vĩ mô (HICP & Ind Prod) từ Eurostat")
    
    # 17 quốc gia EU17 (ISO-2)
    COUNTRIES = ['DE', 'FR', 'NL', 'BE', 'PL', 'CZ', 'SK', 'HU', 'ES', 'PT', 'IT', 'NO', 'SE', 'FI', 'DK', 'IE', 'GB', 'UK']
    
    # 1. Fetch HICP Excluding Energy (prc_hicp_midx)
    print(" -> Đang tải dataset HICP (prc_hicp_midx) từ Eurostat...")
    try:
        df_hicp = eurostat.get_data_df('prc_hicp_midx', flags=False)
        if 'geo\\TIME_PERIOD' in df_hicp.columns:
            df_hicp.rename(columns={'geo\\TIME_PERIOD': 'geo'}, inplace=True)
            
        # Lọc: coicop = 'TOT_X_NRG', unit = 'I15'
        df_hicp = df_hicp[(df_hicp['coicop'] == 'TOT_X_NRG') & (df_hicp['unit'] == 'I15')]
        
        # Melt dataframe
        id_vars = ['freq', 'unit', 'coicop', 'geo']
        df_hicp_melt = df_hicp.melt(id_vars=id_vars, var_name='Datetime', value_name='HICP_excluding_energy')
        
        # Chỉ giữ các quốc gia cần thiết
        df_hicp_melt = df_hicp_melt[df_hicp_melt['geo'].isin(COUNTRIES)]
        df_hicp_melt['geo'] = df_hicp_melt['geo'].replace('UK', 'GB')
        
        # Xử lý Datetime
        df_hicp_melt['Datetime'] = pd.to_datetime(df_hicp_melt['Datetime'] + '-01', format='%Y-%m-%d', errors='coerce')
        df_hicp_melt = df_hicp_melt.dropna(subset=['Datetime'])
        
        # Lọc năm
        df_hicp_melt = df_hicp_melt[(df_hicp_melt['Datetime'].dt.year >= start_year) & (df_hicp_melt['Datetime'].dt.year <= end_year)]
        
        df_hicp_final = df_hicp_melt[['Datetime', 'geo', 'HICP_excluding_energy']].rename(columns={'geo': 'Country'})
        print(f"     [OK] Tải HICP thành công: {len(df_hicp_final)} dòng.")
    except Exception as e:
        print(f"     [ERROR] Lỗi khi tải HICP: {e}")
        df_hicp_final = pd.DataFrame()

    # 2. Fetch Industrial Production (sts_inpr_m)
    print(" -> Đang tải dataset Ind Prod (sts_inpr_m) từ Eurostat...")
    try:
        df_ind = eurostat.get_data_df('sts_inpr_m', flags=False)
        if 'geo\\TIME_PERIOD' in df_ind.columns:
            df_ind.rename(columns={'geo\\TIME_PERIOD': 'geo'}, inplace=True)
            
        # Lọc: indic_bt = 'PROD', nace_r2 = 'B-D', s_adj = 'SCA'
        df_ind = df_ind[(df_ind['indic_bt'] == 'PROD') & (df_ind['nace_r2'] == 'B-D') & (df_ind['s_adj'] == 'SCA')]
        
        # Melt dataframe
        id_vars = ['freq', 'indic_bt', 'nace_r2', 's_adj', 'unit', 'geo']
        df_ind_melt = df_ind.melt(id_vars=id_vars, var_name='Datetime', value_name='Industrial_Production_Index')
        
        # Chỉ giữ các quốc gia cần thiết
        df_ind_melt = df_ind_melt[df_ind_melt['geo'].isin(COUNTRIES)]
        df_ind_melt['geo'] = df_ind_melt['geo'].replace('UK', 'GB')
        
        # Xử lý Datetime
        df_ind_melt['Datetime'] = pd.to_datetime(df_ind_melt['Datetime'].str.replace('M', '-'), format='%Y-%m', errors='coerce')
        df_ind_melt = df_ind_melt.dropna(subset=['Datetime'])
        
        # Lọc năm
        df_ind_melt = df_ind_melt[(df_ind_melt['Datetime'].dt.year >= start_year) & (df_ind_melt['Datetime'].dt.year <= end_year)]
        
        # Chọn Base Year: thường unit='I15'
        df_ind_melt = df_ind_melt[df_ind_melt['unit'] == 'I15']
        
        df_ind_final = df_ind_melt[['Datetime', 'geo', 'Industrial_Production_Index']].rename(columns={'geo': 'Country'})
        print(f"     [OK] Tải Ind Prod thành công: {len(df_ind_final)} dòng.")
    except Exception as e:
        print(f"     [ERROR] Lỗi khi tải Ind Prod: {e}")
        df_ind_final = pd.DataFrame()

    # 3. Kéo ONS CPI cho Anh
    if 'GB' not in df_hicp_final['Country'].values or df_hicp_final[df_hicp_final['Country'] == 'GB'].empty:
        try:
            import io
            print(" -> Đang tải CPI của Anh từ ONS để bổ sung HICP...")
            ons_url = 'https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/d7bt/mm23'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            r = requests.get(ons_url, headers=headers)
            r.raise_for_status()
            
            df_gb = pd.read_csv(io.StringIO(r.text), skiprows=7)
            df_gb.columns = ['DATE', 'HICP_excluding_energy']
            df_gb = df_gb[df_gb['DATE'].str.match(r'^\d{4} \w{3}$', na=False)].copy()
            df_gb['Datetime'] = pd.to_datetime(df_gb['DATE'], format='%Y %b', utc=True)
            df_gb['Datetime'] = df_gb['Datetime'].dt.tz_localize(None)
            
            df_gb = df_gb[(df_gb['Datetime'].dt.year >= start_year) & (df_gb['Datetime'].dt.year <= end_year)]
            df_gb = df_gb[['Datetime', 'HICP_excluding_energy']].copy()
            df_gb['Country'] = 'GB'
            df_gb['HICP_excluding_energy'] = pd.to_numeric(df_gb['HICP_excluding_energy'], errors='coerce')
            
            df_hicp_final = pd.concat([df_hicp_final, df_gb], ignore_index=True)
            print(f"     [OK] Tải CPI ONS thành công: {len(df_gb)} dòng.")
        except Exception as e:
            print(f"     [ERROR] Lỗi tải ONS GB: {e}")

    # Merge hai dataset
    if not df_hicp_final.empty and not df_ind_final.empty:
        df_final = pd.merge(df_hicp_final, df_ind_final, on=['Datetime', 'Country'], how='outer')
    elif not df_hicp_final.empty:
        df_final = df_hicp_final
    elif not df_ind_final.empty:
        df_final = df_ind_final
    else:
        print("[ERROR] Không lấy được bất kỳ dữ liệu Macro nào.")
        return None

    output_dir = os.path.join("data", "raw")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"macro_eu17_raw.csv")
    df_final.to_csv(out_path, index=False)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu file thành công: {out_path} ({df_final.shape[0]} dòng)")
    return out_path
    
if __name__ == "__main__":
    fetch_macro()

