"""
regimes.py — Gom cụm phát hiện Thể chế thị trường (Regime Discovery)
=============================================================================
Mô-đun chứa các thuật toán không giám sát phân mảnh không gian vật lý-kinh tế vĩ mô.
Không vẽ đồ thị. Được thiết kế để import vào notebooks và các file nghiên cứu.

Quy trình phát hiện thể chế gồm 6 bước:
  Bước 1: Loại bỏ quan sát ngoại lệ bằng Isolation Forest (contamination=5%).
  Bước 2: Lấy mẫu phân tầng 10% theo TTF Gas quartile — đảm bảo đại diện đồng đều
           trong không gian đặc trưng clustering 6D, không stratify theo giá điện
           vì HDBSCAN hoạt động trên không gian vật lý, không phải không gian target.
  Bước 3: Chuẩn hóa (StandardScaler) và giảm chiều phi tuyến (UMAP 2D) trên tập mẫu.
  Bước 4: Gom cụm mật độ bằng HDBSCAN trên không gian UMAP 2D.
  Bước 5: Huấn luyện KNN trên không gian 6D SCALED gốc (không phải UMAP 2D) để:
           (a) Inference chỉ cần scaler + KNN, không cần load UMAP (nhẹ hơn).
           (b) Tránh rủi ro UMAP.transform() thiếu nhất quán với out-of-sample data.
           Nhãn KNN lấy từ kết quả HDBSCAN (fully valid — KNN là supervised classifier).
  Bước 6: Lưu artifacts: scaler.pkl, knn_regime.pkl phục vụ inference;
           umap_reducer.pkl lưu riêng phục vụ visualization trong notebook.

Không gian đặc trưng phân cụm (6D) — nhất quán với cấu hình C₁ của XGBoost:
  TTF_Gas_Price, Coal_Price, EU_ETS_Price, Brent_Oil_Price,
  Residual_Load, EU_Gas_Storage_Anomaly.
"""
from __future__ import annotations

import json
import os
import pickle
import warnings
from pathlib import Path

import hdbscan
import numpy as np
import pandas as pd
import umap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Không gian đặc trưng đầu vào phân cụm (6D) ──────────────────────────────
# Nhất quán với cấu hình C₁ của XGBoost. Không chứa giá điện để tránh leakage.
CLUSTERING_FEATURES = [
    "TTF_Gas_Price",
    "Coal_Price",
    "EU_ETS_Price",
    "Brent_Oil_Price",
    "Residual_Load",
    "EU_Gas_Storage_Anomaly",
]

COUNTRIES = ["DE", "DK", "ES", "FR", "IT", "PL"]

# Tham số HDBSCAN tối ưu từ Grid Search (hdbscan_tuning_results.csv)
# Tiêu chí: argmax(Silhouette) với điều kiện Noise_Ratio < 20%
_BEST_CONFIGS: dict[str, dict] = {
    "DE": {"mcs": 300, "ms": 50},   # Silhouette=0.670, 4 clusters
    "DK": {"mcs": 500, "ms": 10},   # Silhouette=0.596, 6 clusters
    "ES": {"mcs": 500, "ms": 10},   # Silhouette=0.544, 6 clusters
    "FR": {"mcs": 400, "ms": 10},   # Silhouette=0.591, 5 clusters
    "IT": {"mcs": 500, "ms": 10},   # Silhouette=0.637, 4 clusters
    "PL": {"mcs": 400, "ms": 10},   # Silhouette=0.623, 5 clusters
}


def run_country(
    df_country: pd.DataFrame,
    country: str,
    artifacts_dir: str | None = None,
    *,
    tuning_df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Chạy toàn bộ quy trình phát hiện thể chế cho một quốc gia.

    Args:
        df_country:    DataFrame chứa dữ liệu của một quốc gia.
        country:       Mã quốc gia (DE, DK, ...).
        artifacts_dir: Thư mục lưu artifacts. None = không lưu.
        tuning_df:     Kết quả Grid Search HDBSCAN. None = dùng hard-coded defaults.
        verbose:       In log tiến trình.

    Returns:
        (df_labeled, stats):
            df_labeled — DataFrame gốc với thêm cột Physical_Cluster, UMAP1, UMAP2,
                         Economic_Context.
            stats      — Dict chứa các chỉ số đánh giá chất lượng phân cụm.
    """
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    df = df_country.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    df = df.sort_values("Datetime").reset_index(drop=True)

    # Kiểm tra đủ đặc trưng
    missing = [f for f in CLUSTERING_FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"[{country}] Thiếu các đặc trưng: {missing}")

    # Lọc hàng có dữ liệu đặc trưng hợp lệ
    df_valid = df.dropna(subset=CLUSTERING_FEATURES).copy()
    if len(df_valid) < 100:
        raise ValueError(f"[{country}] Không đủ dữ liệu hợp lệ: {len(df_valid)} hàng.")

    # ── Bước 1: Loại bỏ ngoại lệ bằng Isolation Forest ──────────────────────
    log(f"  [{country}] Bước 1: Isolation Forest phát hiện ngoại lệ...")
    iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    iso_labels = iso.fit_predict(df_valid[CLUSTERING_FEATURES].fillna(0))

    df_normal = df_valid[iso_labels == 1].copy()
    df_anomaly = df_valid[iso_labels == -1].copy()
    df_anomaly["Physical_Cluster"] = -2  # Nhãn đặc biệt cho ngoại lệ Isolation Forest
    log(f"  [{country}]   → Ngoại lệ: {len(df_anomaly)} ({len(df_anomaly)/len(df_valid)*100:.1f}%)")

    # ── Bước 2: Lấy mẫu phân tầng 10% theo TTF quartile ─────────────────────
    # Stratify theo TTF Gas quartile để đảm bảo đại diện đồng đều
    # trong không gian 6D, bao gồm giai đoạn khủng hoảng 2022.
    log(f"  [{country}] Bước 2: Lấy mẫu phân tầng 10% theo TTF quartile...")
    df_normal["_ttf_q"] = pd.qcut(
        df_normal["TTF_Gas_Price"].clip(lower=0),
        q=4,
        labels=False,
        duplicates="drop",
    )
    sample_size = max(int(len(df_normal) * 0.10), 200)
    df_sample = (
        df_normal.groupby("_ttf_q", group_keys=False)
        .apply(lambda x: x.sample(frac=0.10, random_state=42))
        .sample(n=min(sample_size, len(df_normal)), random_state=42)
    )
    df_sample = df_sample.drop(columns=["_ttf_q"], errors="ignore")
    df_rest = df_normal.drop(index=df_sample.index).drop(columns=["_ttf_q"], errors="ignore")
    log(f"  [{country}]   → Mẫu 10%: {len(df_sample)} | Còn lại 90%: {len(df_rest)}")

    # ── Bước 3: Chuẩn hóa + UMAP giảm chiều 6D → 2D ─────────────────────────
    log(f"  [{country}] Bước 3: StandardScaler + UMAP 6D→2D...")
    X_sample = df_sample[CLUSTERING_FEATURES].fillna(0).values

    scaler = StandardScaler()
    X_sample_scaled = scaler.fit_transform(X_sample)

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=30,
        min_dist=0.0,   # 0.0 tối ưu phân tách mật độ (methodology §2.2, dòng 142)
        random_state=42,
        n_jobs=1,       # n_jobs=1 để đảm bảo tái hiện kết quả ổn định
    )
    emb_sample = reducer.fit_transform(X_sample_scaled)
    df_sample = df_sample.copy()
    df_sample["UMAP1"] = emb_sample[:, 0]
    df_sample["UMAP2"] = emb_sample[:, 1]

    # ── Bước 4: Gom cụm HDBSCAN trên không gian UMAP 2D ─────────────────────
    log(f"  [{country}] Bước 4: Gom cụm HDBSCAN trên không gian UMAP 2D...")
    cfg = _get_config(country, tuning_df)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=cfg["mcs"],
        min_samples=cfg["ms"],
        prediction_data=True,
    )
    clusterer.fit(emb_sample)
    df_sample["Physical_Cluster"] = clusterer.labels_

    # Tính chỉ số Silhouette trong không gian UMAP 2D
    valid_mask = df_sample["Physical_Cluster"] >= 0
    sil = float("nan")
    n_unique = len(df_sample.loc[valid_mask, "Physical_Cluster"].unique())
    if valid_mask.sum() >= 10 and n_unique >= 2:
        sil = silhouette_score(
            emb_sample[valid_mask.values],
            df_sample.loc[valid_mask, "Physical_Cluster"],
        )
    log(f"  [{country}]   → Cấu hình: {cfg} | Silhouette: {sil:.4f}")

    # ── Bước 5: KNN lan truyền nhãn sang 90% còn lại ─────────────────────────
    # Thiết kế: KNN train trên không gian 6D scaled (StandardScaler),
    # KHÔNG phải trên UMAP 2D, để:
    #   (a) Inference chỉ cần scaler + KNN (O(KB)), không cần UMAP (~5.7 MB/quốc gia).
    #   (b) UMAP.transform() trên điểm out-of-sample không đảm bảo nhất quán
    #       với không gian đã huấn luyện → rủi ro tính ổn định khi triển khai.
    log(f"  [{country}] Bước 5: KNN lan truyền nhãn (train trên 6D scaled, K=5)...")

    knn = KNeighborsClassifier(n_neighbors=5, n_jobs=-1)
    knn.fit(X_sample_scaled, df_sample["Physical_Cluster"].values)

    X_rest_scaled = scaler.transform(df_rest[CLUSTERING_FEATURES].fillna(0))
    emb_rest = reducer.transform(X_rest_scaled)
    df_rest = df_rest.copy()
    df_rest["UMAP1"] = emb_rest[:, 0]
    df_rest["UMAP2"] = emb_rest[:, 1]
    df_rest["Physical_Cluster"] = knn.predict(X_rest_scaled)

    # ── Bước 6: Lưu artifacts ────────────────────────────────────────────────
    if artifacts_dir:
        _save_artifacts(artifacts_dir, country, scaler, knn, reducer, cfg)
        log(f"  [{country}] Bước 6: Artifacts đã lưu → {artifacts_dir}")

    # Khôi phục UMAP NaN cho ngoại lệ (tránh lỗi khi vẽ scatter plot)
    df_anomaly = df_anomaly.copy()
    df_anomaly["UMAP1"] = np.nan
    df_anomaly["UMAP2"] = np.nan

    df_labeled = pd.concat([df_sample, df_rest, df_anomaly], ignore_index=True)
    df_labeled = df_labeled.sort_values("Datetime").reset_index(drop=True)
    df_labeled["Economic_Context"] = df_labeled["Physical_Cluster"].map(
        _economic_context(df_labeled)
    )

    n_clusters = int(df_sample["Physical_Cluster"].max()) + 1 if valid_mask.sum() > 0 else 0
    stats = {
        "silhouette_umap": sil,
        "n_clusters": n_clusters,
        "noise_pct": float((df_labeled["Physical_Cluster"] == -1).mean() * 100),
        "anomaly_pct": float((df_labeled["Physical_Cluster"] == -2).mean() * 100),
        "config": cfg,
    }

    log(f"  [{country}] ✓ Hoàn thành: {n_clusters} cụm | Noise {stats['noise_pct']:.1f}%")
    return df_labeled, stats


def run_all_countries(
    df: pd.DataFrame,
    output_path: str = "data/processed/electricity_dataset_with_regimes.csv",
    artifacts_dir: str | None = "artifacts",
    *,
    tuning_df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Chạy gom cụm cho toàn bộ 6 quốc gia song song và xuất file CSV đã gắn nhãn cụm.

    Args:
        df:           DataFrame tổng hợp tất cả quốc gia (có cột 'Country').
        output_path:  Đường dẫn xuất file CSV kết quả.
        artifacts_dir: Thư mục gốc lưu artifacts (mỗi quốc gia một thư mục con).
        tuning_df:    Kết quả Grid Search HDBSCAN. None = dùng defaults.
        verbose:      In log tiến trình.

    Returns:
        DataFrame tổng hợp đã gắn nhãn thể chế, được lưu ra output_path.
    """
    from joblib import Parallel, delayed

    df = df.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    df = df.sort_values(["Country", "Datetime"]).reset_index(drop=True)

    def _process_country(country: str) -> pd.DataFrame:
        df_c = df[df["Country"] == country]
        art_dir = os.path.join(artifacts_dir, country) if artifacts_dir else None
        if art_dir:
            os.makedirs(art_dir, exist_ok=True)
        df_labeled, _ = run_country(df_c, country, art_dir, tuning_df=tuning_df, verbose=verbose)
        return df_labeled

    results = Parallel(n_jobs=6)(
        delayed(_process_country)(country) for country in COUNTRIES
    )

    df_out = pd.concat(results, ignore_index=True)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)

    if verbose:
        print(f"\n[OK] Xuất file dữ liệu đã gắn nhãn thể chế → {output_path}")

    return df_out


def predict_regime(
    features: dict | pd.DataFrame,
    country: str,
    artifacts_dir: str = "artifacts",
) -> np.ndarray:
    """
    Inference nhanh (production): Gán nhãn thể chế cho dữ liệu mới.

    Thiết kế cố ý: Chỉ cần scaler.pkl + knn_regime.pkl — không cần UMAP.
    KNN được train trên không gian 6D scaled, nên inference ổn định và nhẹ.

    Args:
        features:     Dict hoặc DataFrame chứa đặc trưng đầu vào (CLUSTERING_FEATURES).
        country:      Mã quốc gia.
        artifacts_dir: Thư mục chứa artifacts đã lưu.

    Returns:
        Array nhãn thể chế (Physical_Cluster).
    """
    art_dir = os.path.join(artifacts_dir, country)
    with open(os.path.join(art_dir, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(art_dir, "knn_regime.pkl"), "rb") as f:
        knn = pickle.load(f)

    if isinstance(features, dict):
        features = pd.DataFrame([features])

    X = scaler.transform(features[CLUSTERING_FEATURES].fillna(0))
    return knn.predict(X)


# ── Hàm bổ trợ nội bộ ────────────────────────────────────────────────────────

def _get_config(country: str, tuning_df: pd.DataFrame | None) -> dict:
    """Lấy tham số HDBSCAN tốt nhất từ Grid Search hoặc hard-coded fallback."""
    if tuning_df is None:
        return _BEST_CONFIGS.get(country, {"mcs": 200, "ms": 10})

    cands = tuning_df[
        (tuning_df["Country"] == country)
        & (tuning_df["N_Clusters"] >= 2)
        & (tuning_df["N_Clusters"] <= 8)
    ]
    low_noise = cands[cands["Noise_Ratio"] < 20.0]
    pool = low_noise if not low_noise.empty else cands

    if pool.empty:
        return _BEST_CONFIGS.get(country, {"mcs": 200, "ms": 10})

    best = pool.loc[pool["Silhouette"].idxmax()]
    return {"mcs": int(best["min_cluster_size"]), "ms": int(best["min_samples"])}


def _economic_context(df: pd.DataFrame) -> dict:
    """
    Ánh xạ nhãn cụm số sang ngữ cảnh kinh tế định tính.
    Dựa trên giá TTF Gas trung bình của từng cụm.
    """
    ctx: dict[int, str] = {}
    for reg in df["Physical_Cluster"].unique():
        if reg == -2:
            ctx[reg] = "Anomaly (Isolation Forest)"
        elif reg == -1:
            ctx[reg] = "Noise (HDBSCAN)"
        else:
            ttf_mean = df[df["Physical_Cluster"] == reg]["TTF_Gas_Price"].mean()
            if ttf_mean >= 90:
                ctx[reg] = "Spike (Crisis)"
            elif ttf_mean >= 40:
                ctx[reg] = "Transition (Pre/Post-Crisis)"
            elif ttf_mean >= 20:
                ctx[reg] = "Base (Normal)"
            else:
                ctx[reg] = "Drop (Surplus)"
    return ctx


def _save_artifacts(
    art_dir: str,
    country: str,
    scaler: StandardScaler,
    knn: KNeighborsClassifier,
    reducer,
    config: dict,
) -> None:
    """
    Lưu artifacts theo hai nhóm chức năng:
      - Inference (production): scaler.pkl, knn_regime.pkl
      - Visualization only:     umap_reducer.pkl (không cần khi deploy)
    """
    os.makedirs(art_dir, exist_ok=True)

    with open(os.path.join(art_dir, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    with open(os.path.join(art_dir, "knn_regime.pkl"), "wb") as f:
        pickle.dump(knn, f)

    # UMAP reducer chỉ phục vụ notebook visualization
    with open(os.path.join(art_dir, "umap_reducer.pkl"), "wb") as f:
        pickle.dump(reducer, f)

    with open(os.path.join(art_dir, "regime_config.json"), "w", encoding="utf-8") as f:
        json.dump({"country": country, **config}, f, indent=2, ensure_ascii=False)
