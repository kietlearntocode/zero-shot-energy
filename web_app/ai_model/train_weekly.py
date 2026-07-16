import pandas as pd
import xgboost as xgb
import os
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

def main():
    print("=== AI MODEL: TRAIN ZERO-SHOT WITH LAG FEATURES ===")
    
    data_path = "../data_pipeline/weekly_zero_shot_data.csv"
    if not os.path.exists(data_path):
        print(f"Lỗi: Không tìm thấy {data_path}")
        return
        
    df = pd.read_csv(data_path)
    
    # 1. Định nghĩa Features bao gồm cả Lag Features (Dữ liệu Lịch sử)
    features = [
        "EU_Residual_Load_Normalized",
        "TTF_Gas_Price",
        "Coal_Price",
        "EU_ETS_Price",
        "Brent_Oil_Price",
        "EU_Gas_Storage_Anomaly",
        "Price_Lag1",
        "Price_Lag2",
        "Residual_Load_Normalized_Lag1",
        "Residual_Load_Normalized_Lag2"
    ]
    target = "Next_Week_Price_EUR"
    
    X = df[features]
    y = df[target]
    
    # 2. Train-Test Split (Cắt 85% Train, 15% Test ngẫu nhiên)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    
    # 3. Khởi tạo & Huấn luyện XGBoost
    model = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    print(f"Đang huấn luyện mô hình (Với {len(features)} Features) trên {len(X_train)} dòng...")
    model.fit(X_train, y_train)
    
    # 4. Đánh giá
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print("\n[ĐÁNH GIÁ TRÊN TẬP TEST]")
    print(f"Mean Absolute Error (MAE): {mae:.2f} EUR")
    print(f"R-squared (R2): {r2:.4f}")
    
    # 5. Lưu Model
    model_path = "weekly_xgb.json"
    model.save_model(model_path)
    print(f"\n[OK] Đã lưu mô hình tại {model_path}")

if __name__ == "__main__":
    main()
