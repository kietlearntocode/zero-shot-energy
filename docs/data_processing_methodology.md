# Tài Liệu Kỹ Thuật: Phương Pháp Xử Lý Dữ Liệu (Data Processing Methodology)

Tài liệu này quy định các phương pháp chuẩn hóa dữ liệu (Data Normalization & Alignment) được áp dụng trong dự án. Mục tiêu là đảm bảo tính toàn vẹn vật lý và kinh tế của dữ liệu, phục vụ mục đích tối thượng là **Khai khoáng Dữ liệu (Data Mining) và Khám phá Tri thức (Knowledge Discovery)** thay vì chỉ dự báo đơn thuần.

---

## 1. Đồng Bộ Hóa Trục Thời Gian (Time-Series Alignment)

Dữ liệu Giá Bán Buôn Điện (Ember Wholesale Price) được giao dịch và thanh toán theo khung **1 Giờ (1-Hour Resolution)**. Do đó, tất cả các tập dữ liệu vệ tinh (Năng lượng, Vĩ mô, Thời tiết, Khí đốt) phải được tái lấy mẫu (Resampling) về cùng độ phân giải 1 Giờ để đảm bảo tính đồng nhất của Không gian Biểu diễn (Representation Space).

---

## 2. Phương Pháp Tái Lấy Mẫu (Resampling Methods)

Tùy thuộc vào bản chất của từng loại dữ liệu, các hàm Resampling khác nhau sẽ được sử dụng để tránh sai lệch thông tin.

### 2.1. Dữ Liệu Năng Lượng (Energy Generation)
* **Đặc điểm:** Dữ liệu gốc từ API Energy-Charts có độ phân giải không đồng nhất (15 phút, 30 phút, 60 phút tùy quốc gia) và thể hiện **Công suất tức thời (Power - tính bằng Megawatt, MW)**.
* **Phương pháp áp dụng:** Tính trung bình `mean()`.
* **Lý do Kỹ thuật / Vật lý:**
  Thị trường điện giao dịch **Khối lượng Năng lượng (Energy - MWh)** chứ không phải Công suất. Việc lấy trung bình các mốc công suất nhỏ (ví dụ: 15 phút) trong một giờ sẽ phản ánh chính xác 100% tổng năng lượng (MWh) được bơm vào lưới trong giờ đó. 
  Điều này cung cấp các ground truth tĩnh (Static Ground Truth) bắt buộc để Self-Supervised Learning Model có thể nén và học các Energy Regimes.

### 2.2. Dữ Liệu Kinh Tế Vĩ Mô (Macroeconomics - CPI)
* **Đặc điểm:** Dữ liệu Lạm phát (CPI/HICP) được công bố theo chu kỳ **1 Tháng / Lần**.
* **Phương pháp áp dụng:** Kéo giãn tịnh tiến `ffill()` (Forward-Fill).
* **Lý do Kỹ thuật / Kinh tế:**
  Tuyệt đối không sử dụng phương pháp Nội suy tuyến tính (Linear Interpolation) giữa các tháng vì điều này sẽ gây ra **Rò rỉ dữ liệu tương lai (Data Leakage)**. Kéo giãn tịnh tiến (`ffill`) giữ nguyên giá trị CPI từ ngày công bố cho đến kỳ báo cáo tiếp theo, phản ánh chính xác trạng thái thông tin (Information State).

---

## 3. Chống Rò Rỉ Biểu Diễn Ẩn (Latent Leakage Prevention)

Trong quá trình Khai khoáng dữ liệu (Data Mining), hệ thống tuyệt đối **cắt bỏ (Drop)** các thuộc tính toán học nội suy cấp 1 như `Forecast_Error` hay `Cross_Border_Spread`.
* **Lý do:** Các mạng Self-Supervised Temporal Encoder (như Mamba/Transformer) có nguy cơ vướng vào hiệu ứng **Shortcut Learning (Học lười biếng)**. Nếu ta mớm các biến nội suy có sẵn, mô hình sẽ dùng toán cộng trừ cơ bản để vượt qua hàm Loss thay vì phải xây dựng một Không gian ẩn (Latent Space) sâu sắc để hiểu quy luật vật lý của thị trường điện.

---

## 4. Xử Lý Dữ Liệu Khuyết (Cơ Chế "Unbalanced Panel" & NaN Handling)

Dự án sử dụng mô hình **Unbalanced Panel** (Bảng dữ liệu không cân đối) để tối đa hóa lượng thông tin.

**Quy tắc xử lý NaN (Missing Data):**
1. **Tôn trọng bản chất "Không có thông tin":** Khi một quốc gia (ví dụ Ireland) thiếu dữ liệu giá điện trong 9 tháng đầu năm 2018, hệ thống sẽ **giữ nguyên giá trị NaN**. Tuyệt đối không gán `0` (gây nhiễu sai lệch) và không dùng nội suy (tránh Data Leakage).
2. **Không Drop Quốc gia, Không Drop Thời gian:** Giữ trọn vẹn 17 quốc gia (EU17) và mốc thời gian bắt đầu từ `01/01/2018` để SSL Temporal Encoder học được các biến cố Thiên Nga Đen (như đợt lạnh "Beast from the East" đầu 2018).
3. **Chiến lược xử lý phân tách:** Việc xử lý NaN sẽ được giao cho thuật toán Masking của lớp Data Loader tại Phase 4, thay vì làm bẩn dữ liệu gốc ở tầng Data Engineering.
