"""
baseline.py — Mô hình hồi quy tuyến tính OLS và Đa cộng tuyến (VIF)
=================================================================
Mô-đun thuần logic tính toán hồi quy tuyến tính cổ điển, hệ số phóng đại
phương sai (VIF) và độ ổn định mô hình qua kiểm định chéo.
Không chứa code vẽ đồ thị. Có thể import trực tiếp từ Jupyter Notebook.

Các bước xử lý chính:
  Bước 1: Huấn luyện hồi quy tuyến tính OLS (Ordinary Least Squares) cổ điển.
  Bước 2: Đánh giá độ ổn định R² qua TimeSeriesSplit (tránh rò rỉ dữ liệu).
  Bước 3: Định lượng đa cộng tuyến qua Variance Inflation Factor (VIF).
  Bước 4: Trích xuất báo cáo thống kê đầy đủ qua statsmodels.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import TimeSeriesSplit

warnings.filterwarnings("ignore")

# ── Tập đặc trưng vĩ mô an toàn — 18 biến (Bảng 1, methodology §2.1) ─────────
# Loại trừ Fossil_MW (đồng sinh cận biên) và P_{t-1} (rò rỉ thông tin).
# Physical_Cluster (nhãn HDBSCAN) chỉ dùng trong XGBoost C2, không có ở đây.
SAFE_FEATURES = [
    # Nhóm Phụ tải (3)
    "Load", "Residual_Load", "Net_Import",
    # Nhóm Nhiên liệu (5)
    "TTF_Gas_Price", "Coal_Price", "EU_ETS_Price",
    "Brent_Oil_Price", "EU_Gas_Storage_Anomaly",
    # Nhóm Nguồn phát (8)
    "Wind_Onshore_MW", "Wind_Offshore_MW", "Solar_MW",
    "Biomass_MW", "Geothermal_MW", "Hydro_RoR_MW", "Hydro_Reservoir_MW",
    "Nuclear_MW",
    # Nhóm Thời gian (2)
    "Hour_Sin", "Hour_Cos",
]

TARGET = "Real_Wholesale_Price_EUR"
COUNTRIES = ["DE", "DK", "ES", "FR", "IT", "PL"]


def fit_ols(
    df: pd.DataFrame,
    features: list[str] = SAFE_FEATURES,
    target: str = TARGET,
) -> tuple[LinearRegression, pd.Series, float]:
    """
    Bước 1: Huấn luyện OLS trên tập dữ liệu được chỉ định.

    Args:
        df:       DataFrame dữ liệu đầu vào.
        features: Danh sách các cột đặc trưng độc lập.
        target:   Cột biến mục tiêu (mặc định là giá điện thực tế).

    Returns:
        (model, residuals, r2):
            model     — Đối tượng LinearRegression đã fitted.
            residuals — Chuỗi sai số phần dư (Thực tế − Dự báo).
            r2        — Hệ số xác định R² của mô hình.
    """
    X = df[features]
    y = df[target]

    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)

    residuals = pd.Series(y.values - y_pred, index=df.index, name="OLS_Residual")
    return model, residuals, float(r2_score(y, y_pred))


def run_stability(
    df: pd.DataFrame,
    features: list[str] = SAFE_FEATURES,
    target: str = TARGET,
    n_splits: int = 5,
) -> dict:
    """
    Bước 2: Đánh giá độ ổn định cấu trúc của OLS qua kiểm định chéo TimeSeriesSplit.
    Sử dụng chia cắt theo dòng thời gian để tránh rò rỉ dữ liệu từ tương lai.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    X = df[features].values
    y = df[target].values

    scores = []
    for tr, te in tscv.split(X):
        m = LinearRegression().fit(X[tr], y[tr])
        scores.append(float(r2_score(y[te], m.predict(X[te]))))

    return {
        "mean_r2": np.mean(scores),
        "std_r2": np.std(scores),
        "r2_scores": scores,
    }


def get_vif(
    df: pd.DataFrame,
    features: list[str] = SAFE_FEATURES,
) -> pd.DataFrame:
    """
    Bước 3: Định lượng mức độ đa cộng tuyến bằng Variance Inflation Factor (VIF).
    Loại trừ đặc trưng có VIF > 10 để đảm bảo OLS ước lượng ổn định hệ số.
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    X = df[features]
    X_const = sm.add_constant(X)

    vifs = []
    for i, col in enumerate(X_const.columns):
        if col == "const":
            continue
        try:
            v = variance_inflation_factor(X_const.values, i)
        except Exception:
            v = float("nan")
        vifs.append({"Feature": col, "VIF": round(v, 2)})

    return (
        pd.DataFrame(vifs)
        .sort_values("VIF", ascending=False)
        .reset_index(drop=True)
    )


def get_statsmodels_summary(
    df: pd.DataFrame,
    features: list[str] = SAFE_FEATURES,
    target: str = TARGET,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Bước 4: Trích xuất báo cáo thống kê OLS đầy đủ qua statsmodels.
    Cung cấp p-value của từng hệ số, Durbin-Watson (tự tương quan) và các
    kiểm định thống kê chính thống phục vụ báo cáo học thuật.
    """
    X = sm.add_constant(df[features])
    y = df[target]
    return sm.OLS(y, X).fit()


def run_all_countries(
    df: pd.DataFrame,
    features: list[str] = SAFE_FEATURES,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Hàm tổng hợp: Huấn luyện OLS và kiểm tra độ ổn định tự động cho 6 quốc gia.
    """
    log = print if verbose else (lambda *a, **k: None)
    rows = []

    for country in COUNTRIES:
        avail = [f for f in features if f in df.columns]
        df_c = df[df["Country"] == country].dropna(subset=avail + [TARGET]).copy()

        _, _, r2 = fit_ols(df_c, avail, TARGET)
        stab = run_stability(df_c, avail, TARGET)

        rows.append({
            "Country": country,
            "R2_full": round(r2, 4),
            "CV_mean_R2": round(stab["mean_r2"], 4),
            "CV_std_R2": round(stab["std_r2"], 4),
            "N": len(df_c),
        })
        log(
            f"  [{country}] OLS hoàn tất: "
            f"R2={r2:.3f} | CV={stab['mean_r2']:.3f} ± {stab['std_r2']:.3f}"
        )

    return pd.DataFrame(rows)
