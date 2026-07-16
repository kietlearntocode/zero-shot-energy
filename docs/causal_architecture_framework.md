# Khung Phân tích (Analytical Framework): Knowledge Discovery & Causal Architecture

Tài liệu này xác định các nguyên tắc thiết kế dữ liệu và quy trình Machine Learning cho dự án mô hình hóa giá điện Châu Âu, tập trung vào khai phá tri thức (Knowledge Discovery) thay vì tối ưu sai số dự báo (Predictive Modeling).

---

## 1. Nguyên tắc Phân tích (Analytical Principles)

* **Phân biệt Root Cause và Context:** Các biến bối cảnh (`Month`, `Country`) không được xem là nguyên nhân gốc rễ (Root Causes) cấu thành giá điện. Chúng đóng vai trò là nhãn (Labels/Context) đại diện cho một tập hợp các yếu tố vật lý và cấu trúc phức tạp.
* **Mục tiêu của Knowledge Discovery:** Giải thích cơ chế đằng sau các hiện tượng giá (ví dụ: price spikes) bằng cách liên kết chúng với các trạng thái vật lý cụ thể (ví dụ: thiếu hụt khí đốt, tốc độ gió thấp), thay vì chỉ ghi nhận mối tương quan theo thời gian.

---

## 2. Cấu trúc Nhân quả 4 Tầng (4-Layer Causal Structure)

Kiến trúc luồng dữ liệu (Data Flow) được chia thành 4 tầng nhân quả. Các biến ở các tầng khác nhau không được kết hợp trong cùng một mô hình để đánh giá mức độ quan trọng (Feature Importance) nhằm tránh nhầm lẫn giữa biến trung gian (Mediator) và nguyên nhân gốc.

1. **Tầng 1 — Exogenous (Ngoại sinh thuần):** Đã được loại bỏ trong thực hành vì dữ liệu thời tiết (Gió, Mây, Nhiệt độ) gây nhiễu và bị bắt bài hoàn toàn bởi dữ liệu Tải Dư.
2. **Tầng 1.5 — External Market Forces (Ngoại sinh tương đối):** Các lực lượng thị trường bên ngoài tác động trực tiếp vào chi phí biên (Giá Khí đốt, Giá Than, EU ETS, Tỷ giá, Dầu Brent). Lưu ý: Các biến này mang tính chất *quasi-exogenous* vì trong các đợt khủng hoảng, chúng có thể chịu feedback loop từ chính giá điện.
3. **Tầng 2 — State / Stock (Trạng thái/Gánh nặng Vĩ mô):** Bao gồm mức độ khủng hoảng an ninh năng lượng và gánh nặng vật lý vĩ mô của hệ thống. Gồm 2 biến chính: `EU_Gas_Storage_Anomaly` (An ninh) và `Residual_Load` (Gánh nặng tải dư do thời tiết).
4. **Tầng 3 — Flow (Dòng chảy Vận hành cơ sở):** Bao gồm công suất phát nguyên tử của từng nguồn (Gió, Mặt trời, Hạt nhân, Than, Khí...).
5. **Tầng 4 — Price (Giá cả):** Giá thanh toán bù trừ trên thị trường bán buôn (Wholesale spot price) đã loại bỏ lạm phát.

*(Quy tắc nội hàm: Tầng 1.5 và 2 thiết lập môi trường cho Tầng 3. Tầng 3 giải thích Tầng 4).*

---

## 3. Danh sách Biến Bổ sung (Feature Acquisition)

Để hoàn thiện Tầng 1 và Tầng 2, dữ liệu sẽ được thu thập bổ sung theo thứ tự ưu tiên sau:

### Nguồn 1: ERA5 & ERA5-Land (Khí tượng & Thủy văn)
* `Wind_Speed`, `Wind_Speed_Anomaly` (Nguyên nhân gốc của Forecast_Wind, tính bằng `Wind_Speed` trừ đi trung bình lịch sử `Historical Climatological Mean`).
* `Solar_Irradiance`, `Cloud_Cover` (Nguyên nhân gốc của Forecast_Solar).
* `Temperature_Anomaly` (Tính bằng `Temperature` trừ đi trung bình lịch sử cùng ngày/tuần các năm trước để loại bỏ tính mùa vụ).
* `Precipitation_7d`, `Precipitation_30d`, `Snow_Water_Equivalent`, `Snowmelt_Rate`.

### Nguồn 2: ICE / World Bank (Hàng hóa & Môi trường - Tầng 1.5)
* `Coal_Price` (Nhiên liệu biên quan trọng đối với thị trường Đức, Ba Lan, Séc).
* `EU_ETS_Volatility` (Bổ sung cho EU_ETS_Price).

### Nguồn 3: ENTSO-E (Trạng thái Năng lượng)
* `Hydro_Reservoir_Level` (Dữ liệu cốt lõi cho các quốc gia phụ thuộc thủy điện: NO, SE, AT, FR, ES).
* Đổi `Gas_Storage_Level` thành `Gas_Storage_Anomaly` (So với trung bình 5 năm).

### Nguồn 4: Eurostat (Cấu trúc vĩ mô)
* `Industrial_Production_Index` (Chỉ số sản xuất công nghiệp, đại diện cho phụ tải cấu trúc).

---

## 4. Quy tắc Tiền xử lý Dữ liệu (Data Engineering Rules)

1. **Alignment & Forward-Fill:** Dữ liệu vĩ mô (Monthly) như `HICP`, và dữ liệu tồn kho (Daily) như `Gas_Storage`, `EU_ETS` phải được áp dụng phương pháp Forward-Fill (`ffill`) khi nội suy xuống tần suất Hourly. Không sử dụng hàm nội suy tương lai (Interpolate/Look-ahead).
2. **Real Price Calculation:** Giá bán buôn (`Wholesale_Price_EUR`) phải được chia cho `HICP_excluding_energy` thay vì HICP tổng hợp nhằm tránh lỗi giảm phát vòng lặp (circular deflation).
3. **Redundancy Elimination:** Chọn lọc các biến bị trùng lặp thông tin (ví dụ: chọn `Renewables_MW` và loại bỏ `%_Renewables`).
4. **Net Import Splitting:** Trong tương lai, biến `Net_Import` cần được bóc tách theo corridor (ví dụ: Import từ Thủy điện vs Import từ Điện than).

---

## 5. Kiến trúc Pipeline Khai phá (Phase 4 Workflow)

Pipeline của Phase 4 được thiết kế lại để tuân thủ luồng nhân quả:

1. **Characterization (Đặc tả):** Khảo sát thống kê phân bố của các biến Tầng 1, 2, 3 độc lập. Không sử dụng mô hình học máy.
2. **Latent Regime Discovery (Khai phá Thể chế):** Áp dụng UMAP và HDBSCAN lên dữ liệu **Tầng 1 và Tầng 2** để phân cụm và xác định các "Trạng thái Năng lượng Tiềm ẩn" (Latent Energy States).
3. **Price Explanation per Regime (Giải thích Giá theo Thể chế):** Áp dụng thuật toán giải thích (XGBoost + SHAP) sử dụng dữ liệu **Tầng 3** để phân tích sự hình thành giá ở **Tầng 4**, tiến hành độc lập trên từng Regime tìm được ở Bước 2. Mục đích là trích xuất hệ số tương tác, không nhằm tối ưu RMSE.
