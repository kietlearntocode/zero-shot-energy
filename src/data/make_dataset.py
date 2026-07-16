import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from src.data.fetch_energy import fetch_energy_charts_yearly
from src.data.fetch_gas import fetch_gas_storage_yearly
from src.data.fetch_weather import fetch_weather
from src.data.fetch_finance import fetch_finance
from src.data.fetch_macro import fetch_macro_fred
from src.data.fetch_historical_weather import fetch_historical_weather
from src.data.fetch_entsoe_advanced import fetch_entsoe_advanced
import time

def run_pipeline():
    print("==================================================")
    print(" BẮT ĐẦU CHẠY DATA PIPELINE (2016 - 2025)")
    print("==================================================")
    
    start_time = time.time()
    
    # 1. Energy-Charts (17 countries)
    fetch_energy_charts_yearly(start_year=2018, end_year=2025)
    print("-" * 50)
    
    # 2. GIE AGSI (EU Aggregate)
    fetch_gas_storage_yearly(country='EU', start_year=2018, end_year=2025)
    print("-" * 50)
    
    # 3. Open-Meteo (17 countries, 3 cities each)
    fetch_weather(start_date="2018-01-01", end_date="2025-12-31")
    print("-" * 50)
    
    # 4. Yahoo Finance
    fetch_finance(start_date="2018-01-01", end_date="2025-12-31")
    print("-" * 50)
    
    # 5. Macro (World Bank / Eurostat for 17 countries)
    fetch_macro_fred(start_year=2018, end_year=2025)
    print("-" * 50)
    
    # 6. Historical Weather (For Climate Drift)
    fetch_historical_weather(start_date="2008-01-01", end_date="2015-12-31")
    print("-" * 50)
    
    # 7. ENTSO-E Advanced Features
    fetch_entsoe_advanced()
    print("-" * 50)
    
    elapsed = time.time() - start_time
    print(f"[OK] HOÀN TẤT DATA PIPELINE TRONG {elapsed:.2f} GIÂY.")
    print("Tất cả file .csv đã được lưu tại data/raw/")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()
