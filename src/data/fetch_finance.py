import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def fetch_finance(start_date="2018-01-01", end_date="2025-12-31"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Báº¯t Ä‘áº§u kÃ©o dá»¯ liá»‡u TÃ i chÃ­nh tá»« Yahoo Finance tá»« {start_date} Ä‘áº¿n {end_date}")
    
    tickers = {
        "TTF=F": "TTF_Gas_Price",
        "MTF=F": "Coal_Price",
        "EUA.L": "EU_ETS_Price",
        "EURNOK=X": "EUR_NOK",
        "EURPLN=X": "EUR_PLN"
    }
    
    try:
        # yfinance end_date là exclusive, cần cộng thêm 1 ngày để lấy trọn vẹn ngày cuối cùng
        end_date_yf = (pd.to_datetime(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        # Download all at once
        df = yf.download(list(tickers.keys()), start=start_date, end=end_date_yf)
        
        if isinstance(df.columns, pd.MultiIndex):
            # Láº¥y giÃ¡ Ä‘Ã³ng cá»­a (Close)
            df_close = df['Close'].copy()
        else:
            df_close = pd.DataFrame(df['Close'])
            
        # Ä á»•i tÃªn cá»™t
        df_close.rename(columns=tickers, inplace=True)
        
        # Forward fill Ä‘á»ƒ xá»­ lÃ½ cÃ¡c ngÃ y nghá»‰ lá»… / cuá»‘i tuáº§n khÃ´ng giao dá»‹ch
        df_close.ffill(inplace=True)
        
        # Bàn Tay Sắt: 8 năm có khoảng 2000 ngày giao dịch (loại trừ cuối tuần)
        if df_close.shape[0] < 2000:
            raise ValueError(f"Thiếu hụt dữ liệu Tài chính nghiêm trọng! Chỉ có {df_close.shape[0]} ngày giao dịch.")
            
        output_dir = os.path.join("data", "raw")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"finance_{start_date}_{end_date}.csv")
        df_close.to_csv(out_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] Lưu file thành công: {out_path} ({df_close.shape[0]} dòng)")
        return out_path
    except Exception as e:
        print(f"[ERROR] Lỗi kéo dữ liệu Tài chính: {e}")
        raise Exception(f"FAIL-FAST: Bắt buộc dừng tiến trình vì dữ liệu Tài chính (Yahoo) rớt mạng hoặc thiếu hụt!")

if __name__ == "__main__":
    fetch_finance()
