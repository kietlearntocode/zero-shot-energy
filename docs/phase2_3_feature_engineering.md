# Phase 2 & 3: Feature Engineering & Integrity Reference

Tài liệu này đặc tả quy trình làm sạch (Data Cleansing) và kỹ thuật sinh biến (Feature Generation) trên tệp dữ liệu Master (1.18 triệu dòng) trước khi nạp vào các mô hình Học máy.

## 1. Triết lý Xử lý Missing Values (Domain-Specific NaN Handling)
Dữ liệu năng lượng không giống các dataset Machine Learning thông thường. Dữ liệu bị khuyết (`NaN`) thường mang ý nghĩa vật lý thực tế. Việc sử dụng preprocessing mặc định (như `dropna()`) sẽ gây sai lệch khoa học nghiêm trọng. Do đó, quy trình được chia làm hai loại khác biệt:

### 1.1. Structural Missing (Khuyết cấu trúc vật lý)
* **Bản chất:** Ví dụ Na Uy không có nhà máy điện hạt nhân (`Nuclear_MW = NaN`), hoặc Ba Lan không có điện gió ngoài khơi (`Forecast_Wind Offshore = NaN`). Lúc này, `NaN` không có nghĩa là "lỗi thu thập", mà mang semantics: `NaN = 0 capacity/production`.
* **Xử lý:** Bắt buộc áp dụng `fillna(0)` cho toàn bộ các cột năng lượng mang tính cấu trúc. Tuyệt đối không được dùng lệnh `dropna()` để xóa đi các quốc gia thiếu hụt nguồn năng lượng đặc thù.

### 1.2. Accidental Missing (Khuyết do lỗi API/Thu thập)
* **Bản chất:** Ví dụ Nhiệt độ (`Temperature = NaN`) hoặc Phụ tải (`Load = NaN`) do đứt gãy luồng dữ liệu tại thời điểm $t$.
* **Xử lý:**
  * Mô hình **XGBoost** có cơ chế **Native Missing Handling**: tự động học hướng rẽ khi gặp `NaN` tại các node phân nhánh. Nhờ đó, ta giữ lại toàn bộ `NaN` cho thuật toán tự xử lý thay vì phá hỏng dữ liệu bằng Interpolation.
  * Với các biến trễ (Lags) tự sinh ra `NaN` ở giai đoạn khởi động (warm-up) - ví dụ 168 giờ đầu tiên của mỗi quốc gia, hệ thống chỉ cắt đúng 168 dòng đầu tiên của từng quốc gia (`df.groupby('Country').apply(lambda x: x.iloc[168:])`) chứ không gộp chung vào lệnh `dropna()` toàn cục.

## 2. Kỹ thuật Lọc Biến Nhân Quả (Causal Feature Selection)
Trong tệp `master_dataset_hourly.csv`, các cột sau đây bị cấm (Drop vĩnh viễn) để ngăn ngừa Data Leakage:
1. `Dominant_Source`: Bị drop vì là hàm suy dẫn trực tiếp (Deterministic function) từ các cột sản lượng vật lý thực tế.
2. `Cross_Border_Spread_vs_EU`: Bị drop do công thức tính toán chứa giá trị Target (`Wholesale_Price_EUR`) bên trong.
3. *Forecast Errors (ví dụ: Load_Error)*: Không được tính bằng giá trị thực tế trừ dự báo tại thời điểm $t$, vì tại thời điểm $t$, giá trị thực tế là ẩn số. Phải dùng giá trị $t-24$.

## 3. Sinh biến Thời gian Trễ (Lag Mechanisms)
Thuật toán dự báo và giải thích cần nắm bắt quán tính hệ động lực. Class `EmberDataLoader` sinh ra các biến trễ thông qua hàm `pandas.DataFrame.shift()`:

* **Scope Constraint:** Hàm `.shift()` BẮT BUỘC phải thực hiện sau lệnh `.groupby('Country')`. Nếu không, dòng cuối cùng của Germany (DE) sẽ trượt (leak) sang dòng đầu tiên của Spain (ES).

**Các Lags Kỹ thuật:**
* `_lag1`: `df.groupby('Country')[col].shift(1)` $\rightarrow$ Độ trễ 1 giờ (Quán tính nhiệt/điện ngắn hạn).
* `_lag24`: `df.groupby('Country')[col].shift(24)` $\rightarrow$ Độ trễ 24 giờ (Hành vi tiêu dùng theo chu kỳ Ngày).
* `_lag168`: `df.groupby('Country')[col].shift(168)` $\rightarrow$ Độ trễ 168 giờ (Chu kỳ Tuần).

*Lưu ý xử lý NaN sinh ra do hàm shift:* Các dòng `NaN` ở đầu mỗi nhóm quốc gia (168 dòng đầu do `shift(168)`) bị `dropna()` hoàn toàn để duy trì tính toàn vẹn.

## 4. Cơ chế 3-Mode Ablation
Dữ liệu đầu ra của `EmberDataLoader.get_ablation_dataset(mode)` được thiết lập thành 3 tensor khác biệt:
1. **`STRICT_CORE`**:
   * Cấu trúc: `[Datetime_Features, Weather_Forecast, TTF_Price, Target]`
   * Đặc tính: 100% dữ liệu sạch theo phương diện thời gian thực (Real-time). Không có dữ liệu vật lý (Load/Generation) thực tế của thời điểm $t$.
2. **`CORE_PLUS_LAG`**:
   * Cấu trúc: `STRICT_CORE` + `[Load_lag24, Gen_lag24, Price_lag24...]`
   * Đặc tính: Cung cấp quán tính vật lý hợp pháp cho mô hình.
3. **`FULL_ABLATION`**:
   * Cấu trúc: `CORE_PLUS_LAG` + `[Ratios (Tỷ trọng Renewables), Climate Drift Indexes]`
   * Đặc tính: Tối đa hóa chiều biểu diễn. Dùng làm môi trường Benchmark cho XGboost.
