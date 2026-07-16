# TÀI LIỆU KỸ THUẬT: KIẾN TRÚC DỮ LIỆU & FEATURE ENGINEERING
## Dự án: Khai Phá Quy Luật Thị Trường Điện Châu Âu (Energy Knowledge Discovery Framework)

---

## 1. Tổng Quan Kiến Trúc & Chiến Lược "Xoay Trục Mỹ" (US Pivot Strategy)
Tài liệu này định hình thiết kế kiến trúc dữ liệu "mạng nhện" phục vụ việc mô hình hóa và khai phá quy luật, trạng thái vận hành của thị trường điện tại Châu Âu. Hệ thống lấy tập dữ liệu giá điện bán buôn Ember làm lõi (Core Data), sau đó kéo và tích hợp các nguồn dữ liệu vệ tinh đa chiều (Khí hậu, Vận hành, Vĩ mô, Địa chính trị) để giải thích các chế độ vận hành (Energy Regimes). 

Mục tiêu cuối cùng là tạo ra Không gian Biểu diễn (Representation Space) chất lượng cao. Tại Phase 4, ma trận này sẽ được đưa vào các kỹ thuật Học máy (Machine Learning) kinh điển trước để thiết lập mốc tiêu chuẩn (Baselines) và giải mã độ quan trọng của các biến (Feature Importance). Sau đó, ở Phase 5, hệ thống sẽ tiến tới các thuật toán Self-Supervised Learning (SSL) như Mamba/Transformer để khai khoáng Không gian Ẩn (Latent Space).

**Chiến Lược Đặc Biệt: Xoay trục máy chủ Mỹ (US Data Pivot Strategy)**
Các cổng thông tin Châu Âu (Eurostat, ENTSO-E) thường bị phân mảnh chính trị (như Brexit) hoặc chặn API (Rate limits, Geo-blocks). Do đó, toàn bộ kiến trúc này áp dụng quy tắc "Xoay Trục": 
* Ưu tiên khai thác dữ liệu Châu Âu thông qua các trạm trung chuyển hoặc cơ sở dữ liệu khổng lồ của Mỹ (FRED, NOAA, Yahoo Finance).
* Tuyệt đối không dùng nội suy (Interpolation) để lấp liếm lỗi API. Nếu trạm Châu Âu sập, hệ thống tự động chuyển trục sang trạm Mỹ để đảm bảo "Single Source of Truth".

## 2. Kế Hoạch Dự Phòng Cho Từng Thuộc Tính (Attribute Fallback Plan)
| Nhóm Thuộc Tính | Nguồn Chính (Primary) | Trục Dự Phòng Mỹ (US Fallback / Anchor) | Hành Động Khi Bị Chặn/Lỗi |
| :--- | :--- | :--- | :--- |
| **Vĩ Mô (Lạm Phát)** | Eurostat (EU) | **FRED API (Mỹ)** | Hủy Eurostat. Dùng FRED 100% làm nguồn gốc. |
| **Giá Khí Đốt (TTF)** | TTF Hà Lan | **Yahoo Finance (Mỹ - TTF=F)** | Dùng Yahoo Finance làm nguồn gốc liên tục. |
| **Thời Tiết (HDD/CDD)** | Copernicus ERA5 (EU) | **NOAA / Open-Meteo (Mỹ/Đức)** | Dùng Open-Meteo (kéo từ NOAA GFS) thay thế. |
| **Sản Lượng Năng Lượng**| ENTSO-E (EU) | **Ember / Energy-Charts** | Áp dụng Fail-fast. Báo lỗi nếu thiếu > 5% số dòng. |

---

## 3. Lý Thuyết Tiền Xử Lý: Causal Feature Selection & Leakage Prevention
Trước khi đưa dữ liệu vào Phase 4, Master Dataset (hiện chứa 46 cột hợp lệ) phải đi qua cơ chế sàng lọc thông tin nhân quả nhằm tạo tiền đề cho quá trình Representation Learning ở Phase 5. Việc drop hay giữ feature được tuân theo nguyên tắc: **Raw Data $\rightarrow$ Clean Causal Input $\rightarrow$ Model**.

1. **Nhóm Drop Vĩnh Viễn (Tránh học vẹt và Gian lận):**
   - `Dominant_Source`: Là biến Categorical sinh ra bằng quy tắc cứng $argmax(Solar, Wind, Nuclear)$. Mạng lưới có thể tự học đường biên (boundary) này. Giữ lại làm mô hình lười biếng.
   - `Cross_Border_Spread_vs_EU`: Lấy target ($Y$) trừ đi giá trung bình. Dùng Target biến hình để đi đoán Target là Leakage tối kỵ.
   - `Load_Forecast_Error(t)` và `Renewable_Forecast_Error(t)`: Chỉ được biết SAU KHI sự việc kết thúc. Việc dùng error của thời điểm $t$ để đoán thời điểm $t$ là gian lận tương lai (Future-dependent Leakage).

2. **Cơ chế 3-Mode Ablation Test trong Data Loader:**
   Không drop cực đoan các biến tiềm năng. Data Loader sẽ điều phối luồng vào thông qua 3 chế độ để kiểm chứng giả thuyết:
   - **`STRICT_CORE`**: Chỉ dùng lõi tĩnh (Forecast hợp pháp tại $t$, Temperature, TTF, Hour/Sin Cos).
   - **`CORE_PLUS_LAG`**: Bổ sung động lực học (Vật lý lịch sử tại $t-k$, Error lịch sử tại $t-k$).
   - **`FULL_ABLATION`**: Thử nghiệm thêm các biến Tỷ trọng (`%_Ratio`) hoặc dịch chuyển phân phối chậm (`Climate_Drift_10Y`). Nếu mạng tự học được, ta drop; nếu mô hình tốt lên, ta giữ.

---

## 4. Phase 4: Khai Phá Học Máy Cơ Bản (Machine Learning Mining)
Mục tiêu của Phase 4 KHÔNG PHẢI là chốt hạ kiến trúc. Phase 4 đóng vai trò là **"Sanity Check" (Kiểm chứng sự tỉnh táo)** và **"Baseline Mining" (Khai khoáng nền tảng)**.

**Chiến lược cốt lõi: Global Mining + Representative Storytelling**
Để cân bằng giữa tính toàn vẹn khoa học và nghệ thuật thuyết trình, dự án áp dụng chiến lược lai:
* **Tầng Học & Khám phá (Global Mining):** Toàn bộ 17 quốc gia Châu Âu được đưa vào huấn luyện mô hình để đảm bảo không gian biểu diễn (Feature Space) không bị thiên lệch và không bỏ sót các chế độ vận hành (Regimes) nhỏ lẻ.
* **Tầng Trực quan & Giải thích (Representative Storytelling):** Chỉ chọn 5 quốc gia đại diện (DE, FR, ES, PL, NO) với các đặc thù năng lượng trái ngược (Nuclear, Renewable, Coal, Solar, Hydro) để phân tích SHAP và vẽ biểu đồ.

Quá trình khai khoáng này được chia làm 4 giai đoạn (tương ứng với 4 Notebooks):

### 4.1. Baseline Relationship Mining (Hồi quy Tuyến tính)
* **Câu chuyện: "Thước Đo Tuyến Tính" (The Linear Benchmark)**
* **Thuật toán:** Ridge / Lasso / ElasticNet (scikit-learn).
* **Mục đích:** Để chứng minh sự phức tạp của thị trường điện, ta dùng mô hình tuyến tính làm "bia đỡ đạn". Sai số cực lớn của mô hình này chứng minh tính phi tuyến của hệ thống. Đồng thời, các hệ số góc (Coefficients) cho ta thấy bức tranh quan hệ cơ sở trước khi bước vào không gian phi tuyến.

### 4.2. Global XGBoost + SHAP (Feature Influence Discovery)
* **Câu chuyện: "Chiếc Kính Lúp Nhân Quả" (The Non-linear Inspector)**
* **Thuật toán:** XGBoost (Global 17 quốc gia) + SHAP (Lấy mẫu Stratified).
* **Mục đích:** Đo lường động lực học. Mô hình XGBoost sẽ học tương tác toàn lục địa. SHAP sẽ bóc tách chi tiết: *"Biến $X$ tương tác với biến $Y$ ở ngưỡng nào thì tạo ra cú sốc giá?"*. Kết quả được trực quan hóa trên 5 quốc gia để tìm ra quy luật đặc thù từng vùng.

### 4.3. Feature Space State Discovery (UMAP + HDBSCAN)
* **Câu chuyện: "Người Khám Phá Trạng Thái & Kẻ Săn Dị Thường"**
* **Thuật toán:** Nén UMAP (46D $\rightarrow$ 10D) + HDBSCAN + Trực quan UMAP (2D/3D).
* **Mục đích:** Khám phá cấu trúc ẩn của không gian vật lý thô.
  * **HDBSCAN** được dùng để phát hiện các khu vực mật độ thấp (Low density regions / Rare states). 
  * **Logic xác minh Thiên Nga Đen (Black Swan):** HDBSCAN không trực tiếp tìm Black Swan. Nó tìm ra các `Noise Points` (Trạng thái hiếm). Các điểm hiếm này cộng hưởng với các biến số cực đoan (Giá/Thời tiết) có ý nghĩa $\rightarrow$ Tạo thành các Ứng viên Thiên Nga Đen (Candidate Black Swans).

### 4.4. Regime Transition Mining (State Evolution)
* **Câu chuyện: "Dòng Chảy Khủng Hoảng"**
* **Thuật toán:** Transition Matrix + SHAP by Cluster.
* **Mục đích:** Khám phá sự tiến hóa của các trạng thái thị trường. Phân tích xác suất chuyển đổi giữa các Regimes (Ví dụ: Từ Normal $\rightarrow$ Stress). Kết hợp SHAP theo từng Cụm (Cluster) để giải thích xem động lực nào ép hệ thống phải chuyển pha. Mảng này biến việc Clustering tĩnh thành "Khám phá quy luật hệ động lực".

---

## 5. Phase 5: Knowledge Discovery Framework (Tối hậu)
Chỉ sau khi 4 thuật toán trên rà soát toàn bộ không gian vật lý thô (Raw Feature Space), hệ thống mới bước vào Phase 5. Tại đây, **Mamba/Transformer** (Học tự giám sát - SSL) sẽ tiếp quản để nén dữ liệu thành Không Gian Ẩn (Latent Space). Khung kiến trúc và động lực học của Phase 5 (bao gồm Transition Mining và KAN) đã được đặc tả riêng trong tài liệu: **[latent_world_model_architecture.md](latent_world_model_architecture.md)**.
