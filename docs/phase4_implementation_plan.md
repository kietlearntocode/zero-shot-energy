# Phase 4: Implementation Plan

## Tên Đề Tài

**Merit Order and Electricity Price Drivers: Evidence from Six European Markets**

*Tiếng Việt: Cơ chế Merit Order và các Tác nhân Định giá Điện: Bằng chứng từ Sáu Thị trường Châu Âu*

## Câu Hỏi Nghiên Cứu

> *Chuỗi nhân quả Merit Order (Thời tiết → Tái tạo → Khoảng trống Phụ tải → Chi phí Nhiên liệu → Giá điện) vận hành như thế nào trong điều kiện bình thường, và cơ chế nào khiến chuỗi đó khuếch đại thành khủng hoảng giá?*

**Phạm vi:** 6 quốc gia (DE, ES, FR, PL, DK, IT) · 8 năm (2018–2025) · Tần suất giờ.
Xem [country_selection_rationale.md](file:///d:/Projects/data/ember/docs/country_selection_rationale.md) cho lý do chọn/loại quốc gia.

---

## Chuỗi Nhân Quả (Causal DAG)

```
[Exogenous Shocks]
  Wind_Speed_Anomaly ──→ Renewables_MW ──┐
  Cloud_Cover ───────────────────────────┤
                                         ↓
[System Gap]              Residual_Load = Load - Renewables - Nuclear
                                │
[Market Surprises]              │
  Load_Forecast_Error ──────────┤
                                │
[Boundary Conditions]           │
  TTF_Gas_Price ────────────────┤
  Coal_Price ───────────────────┤
  EU_ETS_Price ─────────────────┤
  EU_Gas_Storage_Anomaly ───────┤
                                │
[Cross-border]                  │
  Net_Import ───────────────────┤
                                │
[Cyclical Control]              │
  Hour_Sin, Hour_Cos ───────────┤
                                ↓
[Outcome]          Real_Wholesale_Price_EUR
```

Residual_Load = Load − Renewables_MW − Nuclear_MW.
Nuclear được trừ vì đây là baseload chạy 24/7 với chi phí biên gần bằng 0, không phản ứng theo tín hiệu giá.

---

## Dữ Liệu

**1 file duy nhất:** `data/processed/phase4_dataset.csv` — 420,624 dòng × 17 cột.
Mỗi thuật toán tự chọn cột cần thiết từ file này.

### Metadata (không phải feature — dùng để lọc, chia dữ liệu, trình bày)

| Cột | Mục đích |
|-----|---------|
| `Country` | Lọc per-country, groupby cho presentation |
| `Datetime` | TimeSeriesSplit, Granger lag |

### 12 Safe Features (an toàn cho mọi model)

| # | Nhóm | Biến | Vai trò |
|---|------|------|---------| 
| 1 | Exogenous | `Wind_Speed_Anomaly` | Cú sốc gió |
| 2 | Exogenous | `Cloud_Cover` | Cú sốc mặt trời |
| 3 | System | `Renewables_MW` | Sản lượng tái tạo (actual ≈ forecast) |
| 4 | System | `Nuclear_MW` | Baseload cố định |
| 5 | System | `Load` | Nhu cầu tiêu thụ (actual ≈ forecast) |
| 6 | Engineered | **`Residual_Load`** | = Load − RE − Nuclear |
| 7 | Boundary | `TTF_Gas_Price` | Chi phí nhiên liệu gas |
| 8 | Boundary | `Coal_Price` | Chi phí nhiên liệu than |
| 9 | Boundary | `EU_ETS_Price` | Chi phí phát thải carbon |
| 10 | Boundary | `EU_Gas_Storage_Anomaly` | Van khuếch đại (moderator) |
| 11 | Cyclical | `Hour_Sin` | Chu kỳ ngày (sin) |
| 12 | Cyclical | `Hour_Cos` | Chu kỳ ngày (cos) |

### 1 Endogenous Feature (chỉ dùng trong C₂ Full)

| # | Nhóm | Biến | Vai trò | Lý do cảnh báo |
|---|------|------|---------|----|
| 13 | Endogenous | `Net_Import` | Dòng điện xuyên biên giới | Market coupling đồng thời với giá |

### Target + Mediator

| Cột | Vai trò |
|-----|---------|
| `Real_Wholesale_Price_EUR` | Target — giá điện thực |
| `Fossil_MW` | Mediator — chỉ dùng trong Model 1 (validate cơ chế) |

### Anti-Leakage Log

| Biến bị loại | Lý do |
|-------------|-------|
| `Load_Forecast_Error` | **Leakage** — cần actual Load mới tính được, nhưng actual Load chỉ biết sau khi giờ đó xảy ra |
| `Renewable_Forecast_Error` | **Leakage** + 3/6 nước (ES, PL, IT) không có dữ liệu (100% NaN) |
| Lagged Price | **Chôn vùi causal drivers** — XGBoost sẽ gán 80% importance cho lag thay vì cơ chế Merit Order |

---

## 4 Bước Thực Thi

### Bước 0: Granger Causality — Kiểm chứng kiến trúc

**Mã nguồn:** `src/models/step0_granger_validation.py`

**Câu hỏi:** Chúng ta đã thiết kế trên giấy một chuỗi: gió thổi → điện tái tạo tăng → khoảng trống phụ tải giảm → giá điện giảm. Nhưng liệu chuỗi đó có thực sự xảy ra theo đúng trình tự thời gian trong dữ liệu không? Hay thực tế giá điện thay đổi trước khi gió thổi — tức là chúng ta đã vẽ sai chiều mũi tên? Bước này kiểm tra xem mỗi mũi tên trong sơ đồ nhân quả có đúng hướng hay không trước khi xây bất kỳ mô hình nào.

**Phương pháp:**
- Kiểm định ADF (Augmented Dickey-Fuller) cho từng biến. Nếu phi dừng → sai phân bậc 1 hoặc Toda-Yamamoto.
- Granger Causality Test theo 3 cặp:
  - `Wind_Speed_Anomaly → Renewables_MW` (Gió có thực sự đi trước sản lượng tái tạo không?)
  - `Residual_Load → Fossil_MW` (Khoảng trống có thực sự kéo hóa thạch vào vận hành không?)
  - `Residual_Load + TTF → Price` (Khoảng trống cùng với giá nhiên liệu có thực sự đi trước giá điện không?)
- Partial Correlation (phản chứng): `Wind_Speed_Anomaly → Price | Residual_Load`. Nếu p > 0.05 → Thời tiết không tác động trực tiếp vào giá khi đã có Residual_Load → Kiến trúc đúng.

**Tham số:**

| Cặp kiểm tra | `maxlag` | Lý do |
|--------------|----------|-------|
| Wind → Renewables | 24 giờ | Tác động khí tượng xảy ra trong 1 chu kỳ ngày đêm |
| Residual_Load → Fossil_MW | 6 giờ | Huy động hóa thạch phản ứng trong vài giờ |
| Residual_Load + TTF → Price | 6 giờ | Giá day-ahead phản ứng gần như cùng giờ |
| Ngưỡng chung | p < 0.05 | Chuẩn thống kê |

**Điều kiện dừng:** Granger bác bỏ hướng nhân quả → Dừng, xem lại DAG.

---

### Bước A: Linear Regression — Tìm điểm gãy

**Mã nguồn:** `src/models/step1_linear_baseline.py`

**Câu hỏi:** Giả sử thị trường điện vận hành đơn giản: khi khoảng trống phụ tải tăng thêm 1 MW thì giá tăng đều đặn một khoản cố định, khi giá gas tăng 1 EUR thì giá điện cũng tăng đều đặn. Mô hình tuyến tính này giải thích được bao nhiêu phần trăm sự biến động giá thực tế? Và quan trọng hơn: nó sai ở đâu — sai khi giá thấp bình thường, hay sai khi giá vọt lên hàng trăm EUR? Nếu nó chỉ sai ở vùng khủng hoảng, thì vùng đó chính là nơi mà cơ chế phi tuyến phát huy tác dụng.

**Hai mô hình:**

| Model | Input → Output | Mục đích |
|-------|---------------|----------|
| **Model 1** | `Residual_Load → Fossil_MW` | Khoảng trống có thực sự kéo hóa thạch vào vận hành không? |
| **Model 2** | 14 features → Price | Baseline tuyến tính đầy đủ. Phân tích residual theo vùng giá. |

**Tham số:** OLS, không có hyperparameter.

**Ngưỡng:**

| Model | $R^2$ tối thiểu | Ý nghĩa nếu không đạt |
|-------|-----------------|----------------------|
| Model 1 | ≥ 0.60 | DAG sai — Residual_Load không drive Fossil_MW |
| Model 2 | ≥ 0.40 | Features chưa đủ hoặc dữ liệu quá nhiễu |

**Output bắt buộc:** Scatter plot Residual vs Actual Price, tô màu theo vùng giá (thấp/trung/cao) → Chỉ ra "vùng gãy".

**Stability:** `TimeSeriesSplit(n_splits=5)`. Std($R^2$) < 0.05.

---

### Bước B: HDBSCAN — Market Regime Discovery

**Mã nguồn:** `src/models/step2_regime_discovery.py`

**Câu hỏi:** Dựa trên các điều kiện bên ngoài mà không ai kiểm soát được — tốc độ gió, độ mây, giá gas, tồn kho khí đốt — thị trường điện Châu Âu có luôn ở trong cùng một trạng thái, hay nó tự nhiên phân tách thành nhiều chế độ vận hành khác nhau? Nếu có nhiều chế độ, thì liệu những chế độ mà thuật toán tìm ra có trùng khớp với những vùng mà mô hình tuyến tính ở Bước A đã sai không? Nếu trùng, đó là bằng chứng kép rằng các chế độ này tồn tại thật chứ không phải do thuật toán tự bịa ra.

**Pipeline:**

```
1. Isolation Forest → Tag anomaly
2. UMAP            → Giảm chiều (không dùng PCA — PCA nén crisis regime)
3. Stratified Sampling → 10% theo Price Quantile
4. HDBSCAN         → Phân cụm trên UMAP space
5. approximate_predict() → Gán nhãn 90% còn lại
```

**Biến đầu vào:** `Wind_Speed_Anomaly`, `Cloud_Cover`, `EU_Gas_Storage_Anomaly`, `TTF_Gas_Price`.

**Fallback:** Nếu 4 biến không tạo density structure → thêm `Residual_Load`.

**Tham số:**

| Thuật toán | Tham số | Giá trị | Chiến lược |
|------------|---------|---------|-----------|
| Isolation Forest | `contamination` | 0.05–0.10 | Kiểm tra chéo với tỷ lệ spike giá thực tế |
| UMAP | `n_neighbors` | 15 | Cân bằng local/global |
| UMAP | `min_dist` | 0.1 | Cho phép cụm nén chặt |
| UMAP | `n_components` | 5–10 | Grid search, DBCV score |
| HDBSCAN | `min_cluster_size` | [50, 100, 200, 500] | Grid search, DBCV + Checkpoint kinh tế |
| HDBSCAN | `min_samples` | [10, 25, 50] | Kiểm soát noise |

**Noise ratio check:** `(labels == -1).mean() > 0.30` → tăng sample lên 15–20%.

**[CHECKPOINT] Validate ý nghĩa kinh tế:** `groupby('Regime').agg(['median','std'])`. Regime median phải khác biệt có ý nghĩa.

**[CHECKPOINT] Cross-validate với Bước A:** Chồng regime labels lên scatter plot residual của Linear → Nếu regime "khủng hoảng" trùng với vùng residual cao → Bằng chứng kép.

---

### Bước C: XGBoost + SHAP — Price Explanation

**Mã nguồn:** `src/models/step3_xgboost_shap.py`

**Hai mô hình, hai câu hỏi:**

#### C₁: XGBoost Causal (3 features)

**Features:** `Residual_Load`, `TTF_Gas_Price`, `EU_Gas_Storage_Anomaly`

**Câu hỏi:** Nếu chỉ biết ba thông tin — khoảng trống phụ tải lớn hay nhỏ, giá gas đắt hay rẻ, tồn kho khí đốt đầy hay cạn — thì có thể giải thích được giá điện không? Và tại mức khoảng trống bao nhiêu, tại mức giá gas bao nhiêu thì hệ thống chuyển từ "giá tăng bình thường" sang "giá bùng nổ"? Điểm chuyển tiếp đó chính là câu trả lời cho câu hỏi nghiên cứu.

#### C₂: XGBoost Full (13 features)

**Features:** 12 Safe + 1 Endogenous (Net_Import)

**Câu hỏi:** Khi mở rộng tầm nhìn ra tất cả 13 yếu tố — gió, mây, sản lượng tái tạo, hạt nhân, phụ tải, dòng nhập khẩu, giá gas, giá than, giá carbon, tồn kho, giờ — thì bức tranh có thay đổi không? Cụ thể: việc nén 5 biến thành 1 (Residual_Load) ở mô hình C₁ có làm mất thông tin quan trọng không? Nếu C₂ tốt hơn rõ rệt, thì nguyên nhân gốc rễ (gió yếu hay hạt nhân sập) quan trọng hơn chúng ta tưởng.

**Cùng thuật toán, cùng cấu hình, chỉ khác features:**

| | C₁ Causal | C₂ Full |
|---|---|---|
| Features | 3 | 13 |
| Target | Price | Price |
| Output | SHAP Summary + Dependence | SHAP Summary + Dependence |

**Tham số:**

| Tham số | Mặc định | Grid Search | Lý do |
|---------|----------|------------|-------|
| `max_depth` | 4 | [3, 4, 5, 6] | Depth > 6 → interaction noise phá SHAP |
| `n_estimators` | 500 | `early_stopping_rounds=50` | Tự dừng khi val loss không giảm |
| `learning_rate` | 0.05 | [0.01, 0.05, 0.1] | Thấp = ổn định |
| `subsample` | 0.8 | Cố định | Chống overfit |
| `colsample_bytree` | 0.8 | Cố định | Giảm tương quan giữa cây |

**Chia dữ liệu:** `TimeSeriesSplit(n_splits=5)`. KHÔNG random K-Fold.

**Ngưỡng:**

| Model | Metric | Ngưỡng |
|-------|--------|--------|
| C₁ Causal | $R^2$ | ≥ 0.60 |
| C₂ Full | $R^2$ | ≥ 0.65 |
| C₂ – C₁ | Δ$R^2$ | Nếu > 0.10 → nén mất thông tin |

---

## Output

**Notebook:** `notebooks/Phase4_Report.ipynb` — CHỈ load và trực quan hóa.

| Slide | Nội dung |
|-------|---------|
| 1 | Granger p-values (bảng) |
| 2 | Linear R² + scatter residual (tô màu vùng giá → chỉ ra "điểm gãy") |
| 3 | UMAP tô màu Regime, chồng lên vùng residual cao |
| 4 | SHAP: C₁ (3 features) vs C₂ (14 features) cạnh nhau |
| 5 | **Cao trào:** Scatter `Residual_Load × TTF_Gas_Price` tô màu Regime — ranh giới khủng hoảng |

---

## Verification Plan

| Loại | Kiểm tra | Điều kiện dừng |
|------|---------|---------------|
| Thống kê | ADF test trước Granger | Chuỗi phải dừng hoặc Toda-Yamamoto |
| Causal | Partial Correlation phản chứng | Wind → Price mất ý nghĩa khi kiểm soát Residual_Load |
| Accuracy | $R^2$ Linear ≥ 0.40 | Dưới → xem lại features |
| Accuracy | $R^2$ XGBoost C₁ ≥ 0.60 | Dưới → 3 features không đủ |
| Accuracy | $R^2$ XGBoost C₂ ≥ 0.65 | Dưới → model không đủ tin cậy cho SHAP |
| Stability | Std($R^2$) qua 5 fold < 0.05 | Vượt → model không ổn định |
| Economic | Regime median khác biệt rõ | Không khác biệt → HDBSCAN thất bại |
| Noise | noise_ratio < 0.30 | Vượt → tăng sample 15–20% |
| Cross-check | Regime crisis trùng Linear residual cao | Không trùng → Regime không có ý nghĩa |
| Compression | Δ$R^2$ (C₂ – C₁) | > 0.10 → Residual_Load mất thông tin |
