# HDBSCAN Regime Discovery — Báo cáo Phương pháp luận Đầy đủ

## 1. Tổng quan Pipeline

**Mục tiêu:** Phân vùng không gian vật lý-kinh tế của thị trường điện thành các **Market Regime** (Thể chế thị trường) có cấu trúc mật độ cao, *không sử dụng biến mục tiêu (giá điện)* — đảm bảo zero data leakage.

**Script:** `src/models/regime_discovery.py`  
**Input:** `data/processed/electricity_dataset.csv`  
**Output:** `data/processed/electricity_dataset_with_regimes.csv` (thêm cột `Physical_Cluster`)

### Pipeline 5 bước:

```
[1] Isolation Forest
    → Đánh dấu 5% extreme outliers: Physical_Cluster = -2 (Anomaly)
    → contamination=0.05, n_jobs=1 (reproducibility)

[2] Stratified Sampling
    → Lấy 10% dữ liệu bình thường (loại -2)
    → Stratified theo TTF_Gas_Price QUARTILE (không phải price deciles)
    → Lý do: HDBSCAN hoạt động trong không gian 3D [TTF, Storage, RL],
       không phải không gian giá điện. Stratify theo TTF đảm bảo phân phối
       đồng đều trong không gian clustering, không phải trong không gian target.

[3] UMAP Projection
    → 3D feature space → 2D embedding
    → n_components=2, n_neighbors=30, min_dist=0.0, metric='euclidean',
       random_state=42, n_jobs=1
    → Chứ ý: n_neighbors=30 (rộng hơn, bắt cấu trúc toàn cục), min_dist=0.0
       (cho phép cụm chặt hơn) — tối ưu cho HDBSCAN density estimation

[4] HDBSCAN Clustering
    → Density-based clustering trên 2D UMAP embedding
    → Grid search: min_cluster_size ∈ {50,100,200,400,500}
                   min_samples ∈ {5,10,20,50}
    → Chọn config tối ưu theo Silhouette Score (đo trong UMAP space)
    → Labels: -1 = Noise, 0..K = Normal regimes

[5] KNN Label Propagation --- TRAIN TRÊN KHÔNG GIAN 3D SCALED
    → KNN (k=5) được huấn luyện trên không gian 3D StandardScaler
       (KHÔNG phải UMAP 2D embedding)
    → Lý do: Inference production chỉ cần scaler.pkl + knn_regime.pkl
       Không cần UMAP reducer (≈ 5.7 MB/nước)
    → umap_reducer.pkl được lưu riêng PHỤC VỤ VISUALIZATION trong notebook
    → Physical_Cluster = -2 (Anomaly), -1 (Noise), 0..K (regimes)
```

---

## 2. Lựa chọn Feature Set cho Clustering

### 2.1 Quyết định cuối cùng

**Set A (CHỌN):** `Residual_Load`, `TTF_Gas_Price`, `EU_Gas_Storage_Anomaly` — **3 features**

**Lý do lý thuyết:** 3 biến này là *State Variables* của thị trường điện — trả lời đúng 3 câu hỏi định nghĩa Market Regime:

| Câu hỏi | Biến | Ý nghĩa kinh tế |
|---|---|---|
| Hệ thống có căng không? | `Residual_Load` | MW cần từ nhà máy nhiên liệu |
| Nhiên liệu cận biên đắt không? | `TTF_Gas_Price` | Chi phí của người đặt giá cuối |
| Có nguy cơ thiếu hụt dài hạn không? | `EU_Gas_Storage_Anomaly` | Áp lực nguồn cung trung hạn |

### 2.2 Bằng chứng thực nghiệm

**Thí nghiệm so sánh** Set A (3D, dùng Residual_Load tổng hợp) vs Set B (11D, dùng toàn bộ thành phần cấu tạo của Residual_Load):

```
Set B = [Wind_Onshore_MW, Wind_Offshore_MW, Solar_MW, Biomass_MW, 
         Geothermal_MW, Hydro_RoR_MW, Hydro_Reservoir_MW, Nuclear_MW, 
         Load, TTF_Gas_Price, EU_Gas_Storage_Anomaly]
```

**Kết quả Silhouette (đo trong không gian feature gốc):**

| Country | Set A (3D) | Set B (11D) | Delta | Winner |
|---|---|---|---|---|
| DE | 0.1853 | 0.1193 | -0.066 | **A** |
| DK | 0.1859 | 0.1920 | +0.006 | B (biên) |
| ES | 0.2151 | 0.1611 | -0.054 | **A** |
| FR | 0.2121 | 0.1595 | -0.053 | **A** |
| IT | 0.2087 | 0.1119 | -0.097 | **A** |
| PL | 0.2154 | 0.0897 | -0.126 | **A** |

**Verdict: Set A thắng 5/6 nước.** Set B bị *curse of dimensionality*: noise tăng (FR 15%, IT 19.5%, PL 19.1%), số clusters giảm (chủ yếu 2 thay vì 3–4).

**Lý giải:** `Residual_Load` là *sufficient statistic* cho chiều "system gap" — nó cộng tổng 8 nguồn thành 1 scalar, loại bỏ noise riêng của từng nguồn (Geothermal gần hằng số, Biomass ổn định theo mùa). UMAP giảm chiều từ 3D hiệu quả hơn nhiều so với 11D.

### 2.3 Lưu ý quan trọng: VIF không áp dụng cho HDBSCAN

`Residual_Load` bị loại khỏi OLS vì VIF = ∞ (tổ hợp tuyến tính chính xác → ma trận X'X singular, không thể invert). **Đây là vấn đề của OLS, không phải HDBSCAN.** HDBSCAN tính khoảng cách Euclidean, không cần ma trận nghịch đảo — multicollinearity hoàn toàn không phải vấn đề. Hai thuật toán khác nhau về bản chất toán học.

---

## 3. Cấu hình tối ưu và Kết quả per Country

### 3.1 Lưu ý về Silhouette Measurement Space

> ⚠️ **Quan trọng cho bài báo:** Silhouette scores trong mục này đo trong **không gian UMAP 2D** (embedding space), không phải không gian feature gốc 3D. Silhouette UMAP cao hơn (0.544–0.637) vì UMAP đã nén dữ liệu làm clusters trông tách biệt hơn. Silhouette trong feature space gốc là 0.18–0.22 (xem Section 2.2). Khi báo cáo trong bài báo cần ghi rõ: *"Silhouette coefficient computed in the 2-dimensional UMAP embedding space."*

### 3.2 Germany (DE)

**Best Config:** `min_cluster_size=50, min_samples=50`  
**Silhouette (UMAP space):** 0.596  
**Regimes phát hiện:** 4 regimes + Anomaly + Noise

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,507 | **264.32** | 35,398 | **160.60** | **67.84** |
| Noise (-1) | 17 | 101.62 | 27,999 | 75.20 | 22.55 |
| **Regime 0** 🟢 | 8,120 | 159.25 | 33,986 | 103.03 | 33.67 |
| **Regime 1** 🔵 | 16,517 | **30.76** | 33,760 | **11.70** | 14.05 |
| **Regime 2** 🟡 | 18,840 | 72.31 | 29,196 | 39.27 | 14.16 |
| **Regime 3** 🟣 | 23,127 | 53.38 | 34,821 | 27.18 | 12.95 |

**Diễn giải:**
- Regime 1: Gas price thấp (11.7 EUR) → *Pre-renewable era / Low-cost period* — giá điện thấp nhất
- Regime 2–3: Gas trung bình (27–39 EUR) → *Normal market* — chiếm ~60% thời gian
- Regime 0: Gas cao (103 EUR) → *Gas stress / Near-crisis*
- Anomaly: Gas 160 EUR, OLS error 68 EUR → *2022 Crisis* — model tuyến tính sụp đổ hoàn toàn

---

### 3.3 Denmark (DK)

**Best Config:** `min_cluster_size=400, min_samples=10`  
**Silhouette (UMAP space):** 0.544  
**Regimes phát hiện:** 6 regimes + Anomaly + Noise (nhiều nhất — do wind complexity)

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,507 | **238.76** | 1,488 | **158.50** | **80.79** |
| Noise (-1) | 4,196 | 48.65 | 2,264 | 22.23 | 14.92 |
| **Regime 0** 🟢 | 8,184 | 151.11 | 1,629 | 103.58 | 45.78 |
| **Regime 1** 🔵 | 16,241 | 65.83 | 1,420 | 37.90 | 21.80 |
| **Regime 2** 🟡 | 5,626 | **21.65** | 1,652 | 7.78 | 14.57 |
| **Regime 3** 🟣 | 10,580 | 35.15 | 1,983 | 13.47 | 13.15 |
| **Regime 4** | 10,443 | 64.12 | 1,420 | 36.63 | 23.48 |
| **Regime 5** | 11,351 | 52.87 | 2,296 | 24.82 | 18.10 |

**Diễn giải:**
- Nhiều regimes hơn DE do DK có offshore wind rất lớn → nhiều trạng thái "dư điện" khác nhau
- Regime 2: Gas rất thấp (7.78) + giá 21.65 → *Wind surplus / Near-negative price episodes*
- 4,196 Noise points (~5.8%) → vùng chuyển tiếp giữa các regime không rõ ràng ở DK

---

### 3.4 Spain (ES)

**Best Config:** `min_cluster_size=400, min_samples=10`  
**Silhouette (UMAP space):** 0.591  
**Regimes phát hiện:** 6 regimes + Anomaly + Noise

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,507 | **153.27** | 16,900 | **167.45** | **55.44** |
| Noise (-1) | 643 | 85.08 | 24,577 | 33.49 | 19.02 |
| **Regime 0** 🟢 | 10,571 | 63.43 | 19,755 | 24.99 | 16.06 |
| **Regime 1** 🔵 | 6,569 | **174.03** | 16,149 | 98.24 | **41.28** |
| **Regime 2** 🟡 | 10,829 | 42.05 | 19,040 | 13.23 | 12.18 |
| **Regime 3** 🟣 | 5,307 | **27.89** | 17,242 | 7.88 | 17.80 |
| **Regime 4** | 14,510 | 52.70 | 15,590 | 31.59 | 16.21 |
| **Regime 5** | 18,192 | 64.35 | 13,648 | 44.04 | 20.32 |

**Diễn giải:**
- ES có Iberian Exception (2022: ES-PT tách khỏi EU market mechanism) → Anomaly price thấp hơn DE/IT (153 vs 264–346 EUR) mặc dù gas cũng cao (167 EUR)
- Regime 1: Mean price 174 EUR nhưng OLS residual cao (41.28) → OLS hoàn toàn sai tại đây
- Regime 3: Gas rất thấp + giá thấp → *Solar surplus periods* (ES có solar lớn nhất châu Âu)

---

### 3.5 France (FR)

**Best Config:** `min_cluster_size=400, min_samples=10`  
**Silhouette (UMAP space):** 0.637  
**Regimes phát hiện:** 5 regimes + Anomaly + Noise

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,506 | **304.78** | 50,487 | **145.82** | **58.57** |
| Noise (-1) | 3,283 | 210.58 | 35,841 | 131.02 | **63.73** |
| **Regime 0** 🟢 | 7,579 | 155.44 | 40,333 | 77.39 | 23.32 |
| **Regime 1** 🔵 | 18,859 | 66.77 | 36,991 | 38.23 | 19.14 |
| **Regime 2** 🟡 | 13,411 | 43.43 | 34,467 | 28.23 | 13.67 |
| **Regime 3** 🟣 | 16,102 | **32.78** | 40,438 | **11.48** | 13.22 |
| **Regime 4** | 7,388 | 52.43 | **54,256** | 20.38 | 16.20 |

**Diễn giải:**
- FR có Noise points cao bất thường (3,283 ~ 4.7%) với mean OLS residual **63.73** — cao nhất tất cả
- → Nuclear intermittency: các giờ nhà máy hạt nhân shutdown bất ngờ tạo ra anomalous high-load + high-price không có trong pattern thường
- Regime 4: Residual_Load cao nhất (54,256 MW) nhưng gas thấp (20.38) → *Nuclear shortage compensated by gas* — đặc trưng riêng của Pháp
- Đây là lý do FR luôn có performance kém nhất trong XGBoost (nuclear unavailability là unobserved variable)

---

### 3.6 Italy (IT)

**Best Config:** `min_cluster_size=500, min_samples=10`  
**Silhouette (UMAP space):** 0.623  
**Regimes phát hiện:** 4 regimes + Anomaly + Noise

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,503 | **346.39** | 25,437 | **164.45** | **56.72** |
| Noise (-1) | 78 | 84.56 | 20,182 | 37.48 | 12.50 |
| **Regime 0** 🟢 | 16,264 | 101.34 | 21,924 | 38.05 | 12.15 |
| **Regime 1** 🔵 | 10,051 | **198.77** | 25,069 | 89.44 | **27.80** |
| **Regime 2** 🟡 | 19,841 | **46.32** | 23,874 | 13.51 | 8.51 |
| **Regime 3** 🟣 | 20,391 | 80.98 | 23,926 | 29.33 | 11.08 |

**Diễn giải:**
- IT có Anomaly price **cao nhất** (346.39 EUR) — Italy phụ thuộc gas nhất trong 6 nước
- Regime 2: OLS residual thấp nhất (8.51) → *Cheap gas + low load* — OLS giải thích tốt nhất tại đây
- Chỉ 4 regimes (ít nhất) — thị trường IT "đơn giản" hơn về cấu trúc (gas-dominated, ít renewables mix)

---

### 3.7 Poland (PL)

**Best Config:** `min_cluster_size=400, min_samples=10`  
**Silhouette (UMAP space):** (chung: 0.670)  
**Regimes phát hiện:** 5 regimes + Anomaly + Noise

| Regime | Count | Mean Price (EUR) | Mean Residual Load (MW) | Mean Gas Price (EUR) | Mean OLS Residual |
|---|---|---|---|---|---|
| Anomaly (-2) 🚨 | 3,507 | **147.24** | 16,756 | **157.16** | **47.89** |
| Noise (-1) | 3,150 | 83.13 | 15,901 | 46.63 | 13.79 |
| **Regime 0** 🟢 | 16,292 | **46.38** | 16,955 | **11.58** | 9.30 |
| **Regime 1** 🔵 | 15,833 | 72.89 | 14,187 | 37.91 | 14.33 |
| **Regime 2** 🟡 | 8,240 | 114.11 | 16,362 | 103.77 | 22.34 |
| **Regime 3** 🟣 | 10,325 | 55.15 | 17,647 | 24.65 | 8.58 |
| **Regime 4** | 12,781 | 59.66 | 15,063 | 28.66 | 13.85 |

**Diễn giải:**
- PL Anomaly price thấp nhất (147.24 EUR) — Poland phần nào bị cách ly khỏi crisis EU do coal baseload + hạn chế interconnection
- Regime 0: Gas thấp nhất (11.58 EUR) + giá thấp nhất (46.38 EUR) → *Coal-base pre-crisis era*
- Regime 2: Gas cao (103.77) nhưng giá chỉ 114.11 → Coal buffer làm giảm shock lan truyền từ gas
- Noise cao (3,150 ~ 4.7%) → vùng chuyển tiếp giữa coal-era và gas-era không rõ ràng

---

## 4. Cross-Validation: Alignment với OLS Residuals

**Kiểm tra tính nhất quán:** Nếu clustering đúng, Regime "bình thường" phải có OLS residual thấp (OLS giải thích tốt), còn Regime "stress" phải có OLS residual cao (OLS thất bại).

**Kết quả (tổng hợp 6 nước):**

| Loại Regime | Mean OLS |Abs Residual | Kết luận |
|---|---|---|---|
| Anomaly (-2) | **47–80 EUR/MWh** | OLS sai hoàn toàn — đây là crisis |
| Noise (-1) | 12–64 EUR/MWh | Vùng chuyển tiếp, không ổn định |
| Base regimes (0..K) | **8–23 EUR/MWh** | OLS giải thích tốt trong điều kiện bình thường |

→ Xác nhận: Clustering phát hiện đúng cấu trúc phi tuyến. Các regime có OLS residual cao tương ứng với giai đoạn giá khí cao, tải cao — đúng với lý thuyết Merit Order.

---

## 5. Sử dụng Physical_Cluster trong XGBoost

`Physical_Cluster` được đưa vào XGBoost C₂ (19-feature full set) như một **biến phân loại nguyên** (integer 0..K).

**Lý do có giá trị:** XGBoost dùng `Physical_Cluster` như "context switch" — mỗi nhánh cây có thể học quy luật riêng cho từng regime mà không cần train model riêng.

**Bằng chứng:** SHAP importance của `Physical_Cluster` xuất hiện trong top-5 features cho DK, ES, IT — các nước có nhiều regimes khác biệt rõ ràng (ΔR² lên đến +0.324 cho DK W6).

---

## 6. Tóm tắt Quyết định Methodological

| Quyết định | Lựa chọn | Bằng chứng |
|---|---|---|
| Feature set clustering | 3D (Residual_Load + TTF + Storage) | Silhouette 5/6 nước, empirical comparison |
| Chiều UMAP | 2D | Standard cho HDBSCAN stability |
| Loại outlier | Isolation Forest (5%) trước | Tránh outlier ảnh hưởng density estimation |
| Sampling | Stratified 10% | Tránh temporal imbalance |
| Label propagation | KNN k=5 | Computationally efficient, locally consistent |
| Exclude từ clustering | Fossil_MW, OLS_Residual, target | Anti-leakage |
| Silhouette measurement | UMAP 2D space | Cần ghi rõ trong bài báo |
| Grid search | mcs × ms, chọn max Silhouette | Documented per country (Section 3) |

---

## 7. References

- Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. *PAKDD*, LNCS 7819, 160–172.
- Huisman, R., & Mahieu, R. (2003). Regime jumps in electricity prices. *Energy Economics*, 25(5), 425–434.
- Janczura, J., & Weron, R. (2010). An empirical comparison of alternate regime-switching models. *Energy Economics*, 32(5), 1059–1073.
- Karakatsani, N. V., & Bunn, D. W. (2008). Intra-day and regime-switching dynamics. *Energy Economics*, 30(4), 1776–1797.
- Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation Forest. *IEEE ICDM*, 413–422.
- McInnes, L., Healy, J., & Melville, J. (2018). UMAP. *arXiv:1802.03426*.
- Weron, R. (2014). Electricity price forecasting: A review. *Int. Journal of Forecasting*, 30(4), 1030–1081.
