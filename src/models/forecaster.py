"""
forecaster.py — Mô hình XGBoost & Giải nghĩa đóng góp đặc trưng SHAP
==========================================================================
Mô-đun chứa thuật toán dự báo giá điện và tính toán đóng góp đặc trưng SHAP.
Không chứa code vẽ đồ thị. Được thiết kế để import vào Jupyter Notebook.

Quy trình gồm các bước chính:
  Bước 1: Chia dữ liệu huấn luyện/kiểm thử theo trình tự thời gian (Walk-Forward).
  Bước 2: Phân tách 20% cuối tập huấn luyện làm validation set phục vụ Early Stopping.
  Bước 3: Huấn luyện XGBoost Regressor (Objective: reg:squarederror).
  Bước 4: Ước lượng giá trị SHAP (TreeExplainer) để giải nghĩa đóng góp đặc trưng.
  Bước 5: Lưu mô hình XGBoost dưới dạng JSON phục vụ inference.

Hai cấu hình đặc trưng (theo methodology §2.2):
  C1 — Cấu hình Nhân quả Cốt lõi (6 biến vật lý-kinh tế vĩ mô, không có nhãn thể chế).
  C2 — Cấu hình Có Nhãn Thể chế (7 biến): C1 + Physical_Cluster từ HDBSCAN.
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings("ignore")

# ── Cấu hình C1: Nhân quả Cốt lõi — 6 biến vật lý-kinh tế vĩ mô ─────────────
# Kiểm định "tính đủ" (sufficiency): 6 biến này cũng chính là không gian phân
# cụm HDBSCAN → đảm bảo nhất quán lý thuyết xuyên suốt (methodology §2.2).
C1_FEATURES = [
    "Residual_Load",
    "TTF_Gas_Price",
    "Coal_Price",
    "EU_ETS_Price",
    "Brent_Oil_Price",
    "EU_Gas_Storage_Anomaly",
]

# ── Cấu hình C2: Có Nhãn Thể chế — C1 + Physical_Cluster (7 biến) ────────────
# Kiểm định "giá trị gia tăng" (added value): nhãn HDBSCAN có cải thiện R²
# so với C1 không? (methodology §2.2, dòng 36)
C2_FEATURES = [
    "Residual_Load",
    "TTF_Gas_Price",
    "Coal_Price",
    "EU_ETS_Price",
    "Brent_Oil_Price",
    "EU_Gas_Storage_Anomaly",
    "Physical_Cluster",
]

TARGET = "Real_Wholesale_Price_EUR"
COUNTRIES = ["DE", "DK", "ES", "FR", "IT", "PL"]

# Cấu hình cửa sổ Walk-Forward mở rộng hàng năm (6 cửa sổ)
WINDOWS = [
    {"train_end": 2019, "test_year": 2020, "label": "W1"},
    {"train_end": 2020, "test_year": 2021, "label": "W2"},
    {"train_end": 2021, "test_year": 2022, "label": "W3 (Crisis)"},
    {"train_end": 2022, "test_year": 2023, "label": "W4"},
    {"train_end": 2023, "test_year": 2024, "label": "W5"},
    {"train_end": 2024, "test_year": 2025, "label": "W6"},
    {"train_end": 2025, "test_year": 2026, "label": "W7"},
]

# Siêu tham số XGBoost — đã xác nhận max_depth=5 là giá trị thực tế trong code
_XGB_PARAMS = dict(
    max_depth=5,
    learning_rate=0.05,
    n_estimators=500,
    subsample=0.8,
    colsample_bytree=0.8,
    early_stopping_rounds=50,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
)


def train_window(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    features: list[str],
    target: str = TARGET,
) -> tuple[xgb.XGBRegressor, dict]:
    """
    Bước 2 & 3: Huấn luyện XGBoost trên một cửa sổ dữ liệu xác định.

    Args:
        df_train: Tập huấn luyện.
        df_test:  Tập kiểm thử.
        features: Danh sách tên đặc trưng.
        target:   Tên cột biến mục tiêu.

    Returns:
        (model, metrics):
            model   — XGBRegressor đã fitted.
            metrics — Dict chứa r2, mae, n_train, n_test, best_iteration.
    """
    avail = [f for f in features if f in df_train.columns]
    X_train = df_train[avail].fillna(0)
    y_train = df_train[target]
    X_test  = df_test[avail].fillna(0)
    y_test  = df_test[target]

    # Trích 20% cuối tập huấn luyện làm validation set (Early Stopping)
    val_cutoff = int(len(X_train) * 0.8)
    X_tr, y_tr   = X_train.iloc[:val_cutoff], y_train.iloc[:val_cutoff]
    X_val, y_val = X_train.iloc[val_cutoff:], y_train.iloc[val_cutoff:]

    model = xgb.XGBRegressor(**_XGB_PARAMS)
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

    y_pred = model.predict(X_test)
    metrics = {
        "r2":             float(r2_score(y_test, y_pred)),
        "mae":            float(mean_absolute_error(y_test, y_pred)),
        "n_train":        len(X_train),
        "n_test":         len(X_test),
        "best_iteration": model.best_iteration,
    }
    return model, metrics


def run_walk_forward(
    df: pd.DataFrame,
    country: str,
    feature_set: str = "both",
    artifacts_dir: str | None = "artifacts",
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Bước 1: Kiểm định chéo mở rộng (Walk-Forward) qua 6 cửa sổ lịch sử.

    Args:
        df:           DataFrame tổng hợp (có cột 'Country').
        country:      Mã quốc gia.
        feature_set:  'C1', 'C2' hoặc 'both'.
        artifacts_dir: Thư mục lưu mô hình. None = không lưu.
        verbose:      In log tiến trình.

    Returns:
        DataFrame kết quả R²/MAE theo từng cửa sổ.
    """
    log = print if verbose else (lambda *a, **k: None)

    df_c = df[df["Country"] == country].copy()
    df_c["Datetime"] = pd.to_datetime(df_c["Datetime"], utc=True)
    df_c["Year"] = df_c["Datetime"].dt.year

    # Chỉ huấn luyện trên thể chế bình thường — loại Anomaly (-2) và Noise (-1)
    df_c = df_c[df_c["Physical_Cluster"] >= 0].copy()

    rows = []
    for w in WINDOWS:
        df_train = df_c[df_c["Year"] <= w["train_end"]]
        df_test  = df_c[df_c["Year"] == w["test_year"]]

        if df_train.empty or df_test.empty:
            log(f"  [{country}] {w['label']}: Thiếu dữ liệu, bỏ qua.")
            continue

        row = {
            "Country":    country,
            "Window":     w["label"],
            "train_end":  w["train_end"],
            "test_year":  w["test_year"],
        }

        if feature_set in ("C1", "both"):
            model_c1, m1 = train_window(df_train, df_test, C1_FEATURES)
            row.update({"r2_c1": m1["r2"], "mae_c1": m1["mae"]})
            log(f"  [{country}] {w['label']} C1  R²={m1['r2']:.3f} | MAE={m1['mae']:.1f}")
            if artifacts_dir and w["test_year"] == 2026:
                _save_xgb(model_c1, artifacts_dir, country, "c1")

        if feature_set in ("C2", "both"):
            avail_c2 = [f for f in C2_FEATURES if f in df_c.columns]
            model_c2, m2 = train_window(df_train, df_test, avail_c2)
            row.update({"r2_c2": m2["r2"], "mae_c2": m2["mae"]})
            log(f"  [{country}] {w['label']} C2  R²={m2['r2']:.3f} | MAE={m2['mae']:.1f}")
            if artifacts_dir and w["test_year"] == 2026:
                _save_xgb(model_c2, artifacts_dir, country, "c2")

        rows.append(row)

    return pd.DataFrame(rows)


def run_all_countries(
    df: pd.DataFrame,
    feature_set: str = "both",
    artifacts_dir: str | None = "artifacts",
    verbose: bool = True,
) -> pd.DataFrame:
    """Chạy kiểm định chéo Walk-Forward tự động cho toàn bộ 6 quốc gia song song."""
    from joblib import Parallel, delayed

    results = Parallel(n_jobs=6)(
        delayed(run_walk_forward)(df, country, feature_set, artifacts_dir, verbose)
        for country in COUNTRIES
    )
    return pd.concat(results, ignore_index=True)


def compute_shap(
    df: pd.DataFrame,
    country: str,
    feature_set: str = "C2",
    n_sample: int = 2000,
    artifacts_dir: str | None = "artifacts",
) -> tuple[shap.Explanation, list[str]]:
    """
    Bước 4: Tính giá trị SHAP để giải nghĩa đóng góp của từng biến độc lập.
    Huấn luyện trên dữ liệu ≤2024 và tính SHAP trên mẫu ngẫu nhiên năm 2025.

    Args:
        df:           DataFrame tổng hợp.
        country:      Mã quốc gia.
        feature_set:  'C1' hoặc 'C2'.
        n_sample:     Số quan sát mẫu để tính SHAP (giảm tải tính toán).
        artifacts_dir: Không dùng trực tiếp — truyền qua để tương thích API.

    Returns:
        (shap_values, features): Giá trị SHAP và danh sách tên đặc trưng.
    """
    df_c = df[df["Country"] == country].copy()
    df_c["Datetime"] = pd.to_datetime(df_c["Datetime"], utc=True)
    df_c["Year"] = df_c["Datetime"].dt.year
    df_c = df_c[df_c["Physical_Cluster"] >= 0]

    features = (
        C1_FEATURES if feature_set == "C1"
        else [f for f in C2_FEATURES if f in df_c.columns]
    )

    df_train = df_c[df_c["Year"] <= 2025]
    df_test  = df_c[df_c["Year"] == 2026]

    if df_test.empty:
        raise ValueError(f"Không có dữ liệu năm 2026 cho quốc gia {country}.")

    model, _ = train_window(df_train, df_test, features)

    # Lấy mẫu ngẫu nhiên để giảm tải thời gian tính SHAP
    rng = np.random.default_rng(42)
    idx = rng.choice(len(df_test), size=min(n_sample, len(df_test)), replace=False)
    X_sample = df_test[features].fillna(0).iloc[idx]

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer(X_sample)
    return shap_vals, features


def load_model(
    country: str,
    config: str = "c2",
    artifacts_dir: str = "artifacts",
) -> xgb.XGBRegressor:
    """Tải mô hình XGBoost JSON từ đĩa."""
    path = os.path.join(artifacts_dir, country, f"xgboost_{config}.json")
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model


def predict_price(
    features: dict | pd.DataFrame,
    country: str,
    config: str = "c2",
    artifacts_dir: str = "artifacts",
) -> np.ndarray:
    """
    Inference: Dự báo giá điện dựa trên mô hình đã huấn luyện sẵn.

    Args:
        features:     Dict hoặc DataFrame chứa đặc trưng đầu vào.
        country:      Mã quốc gia.
        config:       'c1' hoặc 'c2'.
        artifacts_dir: Thư mục chứa mô hình JSON.

    Returns:
        Array dự báo giá điện (EUR/MWh).
    """
    model = load_model(country, config, artifacts_dir)
    feat_list = C1_FEATURES if config == "c1" else C2_FEATURES
    if isinstance(features, dict):
        features = pd.DataFrame([features])
    avail = [f for f in feat_list if f in features.columns]
    return model.predict(features[avail].fillna(0))


# ── Hàm bổ trợ nội bộ ────────────────────────────────────────────────────────

def _save_xgb(
    model: xgb.XGBRegressor,
    art_dir: str,
    country: str,
    config: str,
) -> None:
    """Lưu mô hình XGBoost dưới dạng JSON (nhẹ, portable, cross-platform)."""
    out = os.path.join(art_dir, country)
    os.makedirs(out, exist_ok=True)
    model.save_model(os.path.join(out, f"xgboost_{config}.json"))
