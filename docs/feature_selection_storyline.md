# CÂU CHUYỆN KHAI KHOÁNG: TRIẾT LÝ LỰA CHỌN VÀ TÍCH HỢP DỮ LIỆU
*(The Data Selection & Integration Storyline)*

Để thuyết trình trước hội đồng về lý do tại sao chúng ta lại xây dựng một mạng lưới dữ liệu khổng lồ (46 cột) xoay quanh lõi giá điện Ember, chúng ta cần một triết lý xuyên suốt. Triết lý đó là:

> **"Giá điện (Ember) chỉ là Triệu chứng (Symptom) ở bề nổi. Để khám phá ra quy luật vận hành, ta phải thu thập toàn bộ các Căn nguyên (Root Causes) tạo nên Hệ sinh thái năng lượng đó."**

Dưới đây là 4 câu chuyện (4 lăng kính) giải thích lý do tại sao từng nhóm thuộc tính lại được kéo về và hợp nhất (merge) vào Master Dataset.

---

## Lăng Kính 1: Bức Tranh Tự Nhiên (The Canvas of Nature)
*Dữ liệu hợp nhất: Weather (Open-Meteo) & Climate Drift (ERA5)*

**Tại sao chúng ta cần Thời tiết và Khí hậu?**
Khách hàng không trực tiếp tiêu thụ điện, họ tiêu thụ "sự thoải mái". Khi thời tiết khắc nghiệt, họ bật sưởi (HDD) hoặc điều hòa (CDD). Thời tiết là biến ngoại sinh tuyệt đối độc lập — nó không quan tâm đến thị trường, nhưng lại tạo ra **"Áp lực phụ tải nguyên thủy nhất"** lên lưới điện.

* **Câu chuyện Thời tiết (Ngắn hạn):** Thay vì đưa nhiệt độ thô, việc sử dụng Độ ngày Sưởi/Làm mát (HDD/CDD) giúp lượng hóa chính xác áp lực tiêu thụ. 
* **Câu chuyện Khí hậu (Dài hạn - `Climate_Drift_10Y`):** Tại sao phải nhìn về 10 năm trước? Bởi vì nền khí hậu đang dịch chuyển (Slow Distribution Shift). Biến số này giúp mô hình giải thích được tại sao cấu trúc đỉnh tải của Châu Âu đang dịch chuyển dần từ các cơn bão tuyết mùa đông sang những đợt nắng nóng cực đoan mùa hè. Không có biến này, mô hình AI sẽ bị lạc hậu trong kỷ nguyên biến đổi khí hậu.

---

## Lăng Kính 2: Nhịp Đập Cơ Học (The Physical Engine)
*Dữ liệu hợp nhất: Năng lượng & Lưới điện (ENTSO-E, Energy-Charts)*

**Tại sao phải mang cả lưới điện vật lý vào mô hình toán học?**
Bởi vì điện năng là thứ hàng hóa kỳ lạ nhất thế giới: Nó không thể lưu trữ quy mô lớn và bắt buộc Sản xuất - Tiêu thụ phải cân bằng tại mọi mili-giây. 

* **Sự đỏng đảnh của Tái tạo:** Năng lượng tái tạo (`Renewables_MW`) có chi phí sản xuất bằng 0. Khi gió thổi mạnh, giá điện có thể rớt xuống mức âm. Nhưng khi gió ngừng thổi, hệ thống rơi vào trạng thái sốc.
* **Sai số là kẻ thù (`Lag_Forecast_Error`):** Những sai lệch giữa Dự báo (`Forecasted Load`) và Thực tế buộc nhà điều hành lưới điện phải khởi động khẩn cấp các nhà máy dự phòng đắt đỏ, trực tiếp tạo ra các cú sốc giá vọt đỉnh (Price Spikes).
* **Hiệu ứng lây nhiễm (`Net_Import`):** Lưới điện Châu Âu liên kết chặt chẽ. Việc đưa biến Xuất/Nhập khẩu vào là bằng chứng toán học chứng minh: Khi nước Pháp cạn kiệt điện hạt nhân do hạn hán, giá điện đắt đỏ của Pháp sẽ ngay lập tức "lây nhiễm" sang Đức thông qua các đường cáp ngầm biên giới.

---

## Lăng Kính 3: Chốt Chặn Tiền Tệ (The Financial Anchor)
*Dữ liệu hợp nhất: Giá Khí đốt TTF, Tín chỉ Carbon ETS, Lạm phát (FRED/Yahoo)*

**Nếu tự nhiên tạo ra Tải, Lưới điện cung cấp Lượng, thì cái gì quyết định Giá?**
Theo cơ chế thị trường Châu Âu (Merit Order), năng lượng tái tạo định đoạt "Giá Sàn", nhưng Nhiên liệu hóa thạch mới là kẻ định đoạt **"Giá Trần"**.

* **Kẻ thao túng TTF:** Giá khí đốt tự nhiên Hà Lan (`TTF_Gas_Price`) chính là chốt chặn chi phí biên. Khi nguồn cung khí đứt gãy, các nhà máy điện khí buộc phải chào giá cắt cổ để duy trì lưới điện, kéo toàn bộ mặt bằng giá điện của mọi quốc gia lên đỉnh. 
* **Bàn tay hữu hình ETS:** Tín chỉ Carbon (`EU_ETS_Price`) là công cụ chính trị ép giá năng lượng bẩn. Nó làm biến dạng cấu trúc chi phí và bẻ cong vĩnh viễn mức giá sàn của nhiệt điện than.
* **Lăng kính Lạm phát (`HICP/CPI`):** Đưa lạm phát vào để loại bỏ ảo giác đồng tiền. Nó giúp thuật toán trả lời câu hỏi: Giá điện tăng vọt là do thị trường thực sự đang thiếu hụt điện (Cung - Cầu), hay chỉ đơn giản là do đồng tiền Châu Âu đang mất giá nghiêm trọng?

---

## Lăng Kính 4: Kỷ Nguyên Đứt Gãy (The Black Swans)
*Dữ liệu hợp nhất: Cờ Địa Chính Trị (Logic & Feature Engineering)*

**Tại sao các biến logic (1/0) lại quan trọng ngang với dữ liệu số thực?**
Các thuật toán Học máy cơ bản thường ngây thơ tin rằng: "Quy luật của ngày hôm qua sẽ lặp lại vào ngày mai". Nhưng địa chính trị thì không. Sự kiện địa chính trị bẻ gãy mọi không-thời gian.

* **Biến cờ Khủng hoảng (`Regime_Crisis`):** Không phải là một con số, nó là chiếc "công tắc chuyển pha". Đưa cờ này vào để báo hiệu cho mô hình: Từ sau 2021, luật chơi của Châu Âu đã bị viết lại bởi chiến tranh và vũ khí hóa năng lượng. Mô hình không được phép dùng chung một phương trình của kỷ nguyên hòa bình (2019) để áp cho kỷ nguyên đứt gãy (2022).

---

### TỔNG KẾT: SỰ GIAO THOA CỦA 4 LĂNG KÍNH
Quyết định tích hợp 4 luồng dữ liệu khổng lồ này vào một file Master CSV duy nhất không phải là việc nhặt nhạnh bừa bãi (Data Dump). Đó là hành trình tái tạo lại một **Hệ Động Lực (Dynamical System)** hoàn chỉnh trên máy tính: Nơi Tự nhiên (Thời tiết) tạo ra nhu cầu, Vật lý (Lưới điện) đáp ứng sản lượng, Tài chính (Khí đốt/Carbon) định giá chi phí, và Địa chính trị vẽ lại luật chơi. 

Chỉ với một hệ sinh thái trọn vẹn như vậy, mô hình AI (ở Phase 4 & 5) mới đủ sức để vươn tới mục tiêu tối thượng: Khám Phá Quy Luật (Knowledge Discovery).
