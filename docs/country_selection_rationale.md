# Lựa Chọn Quốc Gia Nghiên Cứu: Tiêu Chí và Lý Do

## 1. Bối Cảnh

Bộ dữ liệu gốc bao gồm 17 quốc gia thuộc khu vực Châu Âu: AT, BE, CH, CZ, DE, DK, ES, FI, FR, HU, IE, IT, NL, NO, PL, SE, SK. Tổng cộng 1.185.602 quan trắc theo giờ, phủ kín giai đoạn 2018–2025.

Việc giữ nguyên toàn bộ 17 quốc gia trong mô hình phân tích đặt ra ba vấn đề phương pháp luận:

- **Khác biệt cơ chế sinh dữ liệu (Data Generating Process):** Một quốc gia có 90% thủy điện (Na Uy) và một quốc gia có 70% than (Ba Lan) vận hành theo cơ chế định giá khác nhau hoàn toàn. Gộp chúng vào cùng một mô hình hồi quy vi phạm giả thiết về tính đồng nhất của DGP.
- **Dữ liệu khuyết có hệ thống:** Một số biến trạng thái (Hydro_Reservoir_Level, Nuclear_MW) chỉ tồn tại ở một nhóm quốc gia. Giữ 17 nước buộc phải điền khuyết (impute) trên quy mô lớn, làm giảm độ tin cậy thống kê.
- **Nhiễu từ thị trường phụ thuộc:** Các quốc gia có thị trường nhỏ (BE, SK, HU) có giá điện bị chi phối bởi dòng điện nhập khẩu từ láng giềng, không phản ánh cơ chế Merit Order nội tại.

Nghiên cứu này lựa chọn 6 quốc gia theo tiêu chí tối đa hóa **tính đại diện** trên nhiều chiều đồng thời, đảm bảo chuỗi nhân quả Merit Order có thể được quan sát và kiểm chứng ở cả hai cực: giá bùng nổ và giá âm.

---

## 2. Tiêu Chí Lựa Chọn

Mỗi quốc gia được đánh giá theo 5 chiều:

1. **Cơ cấu năng lượng:** Đại diện cho ít nhất một loại nguồn phát chính (gió, mặt trời, hạt nhân, than, khí đốt).
2. **Vị trí trên phổ Merit Order:** Từ Residual_Load âm (dư thừa tái tạo, giá âm) đến Residual_Load cực cao (thiếu hụt nguồn cung, giá bùng nổ).
3. **Vị trí địa lý:** Phủ các vùng khí hậu khác nhau (Bắc Âu, Trung Âu, Tây Âu, Đông Âu, Nam Âu).
4. **Mức độ độc lập thị trường:** Ưu tiên các thị trường có giá phản ánh cơ chế nội tại thay vì bị kéo bởi dòng điện liên kết xuyên biên giới.
5. **Khả năng kiểm chứng chuỗi nhân quả:** Mỗi quốc gia phải thể hiện rõ ít nhất một mắt xích trong chuỗi `Thời tiết → Tái tạo → Residual_Load → Chi phí nhiên liệu biên → Giá điện`.

---

## 3. Danh Sách 6 Quốc Gia Được Chọn

### DE — Đức
- **Cơ cấu:** Gió cao (onshore), than đang giảm, khí đốt trung bình, mặt trời đang tăng.
- **Vai trò trong nghiên cứu:** Thị trường chuyển đổi năng lượng lớn nhất Châu Âu. Sự cạnh tranh giữa điện gió và điện than tạo ra biến thiên giá rõ rệt theo giờ. Sự kiện Nord Stream (2022) cung cấp dữ liệu về phản ứng hệ thống khi nguồn cung khí đốt bị cắt.
- **Vùng trên phổ Merit Order:** Trung tâm — Residual_Load dao động rộng tùy theo gió và nhu cầu.

### ES — Tây Ban Nha
- **Cơ cấu:** Mặt trời cao, gió trung bình, khí đốt bổ sung, một số hạt nhân.
- **Vai trò trong nghiên cứu:** Đại diện cho thị trường chiếu xạ mặt trời cao. Bán đảo Iberia có kết nối xuyên biên giới hạn chế (chỉ qua Pháp), tạo ra sự cô lập tương đối giúp chuỗi Merit Order nội tại rõ ràng hơn. Hạn hán mùa hè ảnh hưởng đến cả thủy điện bổ sung lẫn nhu cầu làm mát.
- **Vùng trên phổ Merit Order:** Trung tâm đến thấp — Residual_Load giảm mạnh vào ban ngày nhờ mặt trời.

### FR — Pháp
- **Cơ cấu:** Hạt nhân chi phối (~70%), thủy điện bổ sung, gió và mặt trời đang tăng.
- **Vai trò trong nghiên cứu:** Trường hợp biên (Edge case) quan trọng. Khi toàn bộ hạm đội hạt nhân hoạt động bình thường, Residual_Load cấu trúc rất thấp và giá ổn định. Nhưng sự cố ăn mòn ống dẫn (Corrosion Crisis, 2022) buộc ~50% lò phản ứng dừng hoạt động, đẩy Residual_Load tăng vọt. Đây là dữ liệu tự nhiên (Natural Experiment) hiếm có về tác động của việc mất nguồn baseload.
- **Vùng trên phổ Merit Order:** Thấp cấu trúc, nhưng dịch chuyển sang cao khi hạt nhân gặp sự cố.

### PL — Ba Lan
- **Cơ cấu:** Than chi phối (~70%), tái tạo rất thấp, không có hạt nhân.
- **Vai trò trong nghiên cứu:** Merit Order thuần khiết nhất trong danh sách. Gần như toàn bộ sản lượng là nhiên liệu hóa thạch, nên giá điện phản ánh trực tiếp chi phí nhiên liệu biên mà không bị can nhiễu bởi tái tạo. Chịu tác động mạnh từ EU ETS (giá carbon) vì cường độ phát thải cao nhất khu vực.
- **Vùng trên phổ Merit Order:** Cao cấu trúc — Residual_Load luôn cao vì ít tái tạo.

### DK — Đan Mạch
- **Cơ cấu:** Gió cực cao (~50%), không có hạt nhân, kết nối mạnh với hệ thống Nordic.
- **Vai trò trong nghiên cứu:** Phép thử ngược (Counter-test) cho chuỗi Merit Order. Khi sản lượng gió vượt quá phụ tải, Residual_Load trở nên âm và giá điện rơi xuống vùng âm. Nếu mô hình giải thích được giá âm ở DK đồng thời với giá bùng nổ ở IT, đó là bằng chứng chuỗi Merit Order hoạt động trên toàn phổ, không chỉ ở vùng giá dương.
- **Vùng trên phổ Merit Order:** Cực âm — Residual_Load thường xuyên âm.

### IT — Ý
- **Cơ cấu:** Khí đốt chi phối (~40%), mặt trời đang tăng, một số thủy điện.
- **Vai trò trong nghiên cứu:** Quốc gia phụ thuộc khí đốt nhất trong EU, nơi mối quan hệ TTF_Gas_Price → Giá điện truyền dẫn mạnh nhất và trực tiếp nhất. Cung cấp dữ liệu để kiểm chứng vai trò khuếch đại của Gas_Storage_Anomaly: khi tồn kho khí đốt cạn kiệt + Residual_Load cao, Ý là nơi giá phản ứng dữ dội nhất.
- **Vùng trên phổ Merit Order:** Cao đến cực cao — Residual_Load phụ thuộc nặng vào giá khí đốt.

---

## 4. Danh Sách 11 Quốc Gia Không Được Chọn

### Nhóm A: Loại vì cơ chế sinh dữ liệu khác biệt hoàn toàn (Thủy điện chi phối)

Các quốc gia sau có tỷ trọng thủy điện dispatchable (có thể điều phối) vượt quá 50%. Trong hệ thống thủy điện, nhà vận hành chủ động tăng/giảm công suất turbine nước để đáp ứng nhu cầu. Khái niệm Residual_Load — khoảng trống mà nhiên liệu hóa thạch phải lấp đầy — không áp dụng được vì thủy điện tự lấp đầy khoảng trống đó với chi phí biên gần bằng không.

| Quốc gia | Tỷ trọng thủy điện | Lý do loại cụ thể |
|----------|-------------------|-------------------|
| **NO** (Na Uy) | ~90% | Thủy điện dispatchable gần như tuyệt đối. Giá điện phụ thuộc vào lượng nước trong hồ chứa (Water Value), không phải Merit Order hóa thạch. |
| **SE** (Thụy Điển) | ~45% thủy + ~30% hạt nhân | Giá bị chi phối bởi hệ thống Nordic chung (NordPool). Khó tách biệt cơ chế nội tại khỏi ảnh hưởng của Na Uy và Phần Lan. |
| **AT** (Áo) | ~60% | Thị trường nhỏ, thủy điện Alpine. Từng ghép chung vùng giá với Đức đến 2018, giá vẫn bị kéo theo Đức sau khi tách. |
| **CH** (Thụy Sĩ) | ~60% | Không phải thành viên EU, vận hành như "pin dự trữ" cho Châu Âu qua pumped storage. Cấu trúc thị trường khác biệt hoàn toàn. |

### Nhóm B: Loại vì thị trường quá nhỏ hoặc không đủ độc lập

Giá điện tại các quốc gia sau bị chi phối chủ yếu bởi dòng điện nhập khẩu qua đường dây kết nối xuyên biên giới (interconnectors), không phản ánh cơ chế Merit Order nội tại.

| Quốc gia | Lý do loại cụ thể |
|----------|-------------------|
| **BE** (Bỉ) | Thị trường nhỏ, kết nối chặt với Pháp và Hà Lan. Giá phần lớn được xác định bởi dòng điện nhập khẩu, không phải bởi sản lượng nội địa. Đang trong quá trình tháo dỡ hạt nhân (chưa hoàn thành). |
| **NL** (Hà Lan) | Phụ thuộc khí đốt giống Ý, nhưng Hà Lan là nơi đặt sàn giao dịch TTF — tạo ra rủi ro nội sinh (giá điện NL có thể ảnh hưởng ngược đến giá TTF). Ý sạch hơn về mặt nhân quả vì Ý là bên nhận giá (price taker) trên sàn TTF, không phải bên tạo giá (price maker). |
| **IE** (Ireland) | Thị trường đảo, vận hành theo hệ thống SEM riêng (Single Electricity Market chung với Bắc Ireland). Cô lập khỏi lục địa Châu Âu, không chia sẻ cơ chế liên kết giá với các nước còn lại. |

### Nhóm C: Loại vì trùng lặp vai trò đại diện

Các quốc gia sau có cơ cấu năng lượng hoặc đặc điểm thị trường đã được đại diện tốt hơn bởi một quốc gia khác trong danh sách 6 nước được chọn.

| Quốc gia | Trùng với | Lý do loại cụ thể |
|----------|----------|-------------------|
| **CZ** (Séc) | PL | Than + Hạt nhân, Đông Âu. Ba Lan đại diện tốt hơn cho trường hợp than chi phối vì quy mô lớn hơn và tỷ trọng than cao hơn. |
| **SK** (Slovakia) | FR | Hạt nhân chi phối (Mochovce, Bohunice). Pháp đại diện tốt hơn cho trường hợp hạt nhân với lượng dữ liệu lớn hơn và sự cố Corrosion 2022 cung cấp tình huống nghiên cứu tự nhiên. |
| **HU** (Hungary) | — | Thị trường nhỏ, phụ thuộc nhập khẩu nặng, thị trường bán buôn bị quản lý giá. Tỷ trọng tái tạo quá thấp để quan sát Merit Order dynamics. Hạt nhân (Paks) và khí đốt bổ sung nhưng không đủ lớn để phân biệt với các nước khác. |
| **FI** (Phần Lan) | SE | Nằm trong hệ thống Nordic, phụ thuộc nhập khẩu từ Thụy Điển và Na Uy. Lò phản ứng Olkiluoto 3 mới đi vào hoạt động (2023), chưa đủ dữ liệu vận hành ổn định trong khung thời gian nghiên cứu. |

---

## 5. Tổng Hợp

Từ 17 quốc gia ban đầu, 11 quốc gia bị loại theo 3 nhóm lý do:

| Nhóm lý do | Quốc gia bị loại | Số lượng |
|------------|------------------|----------|
| Cơ chế sinh dữ liệu khác (Thủy điện) | NO, SE, AT, CH | 4 |
| Thị trường không đủ độc lập | BE, NL, IE | 3 |
| Trùng lặp vai trò đại diện | CZ, SK, HU, FI | 4 |

6 quốc gia được chọn (DE, ES, FR, PL, DK, IT) phủ kín:
- 5 vùng địa lý Châu Âu (Bắc, Trung, Tây, Đông, Nam).
- 5 loại nguồn phát chính (Gió, Mặt trời, Hạt nhân, Than, Khí đốt).
- Toàn bộ phổ Merit Order từ giá âm (DK) đến giá bùng nổ (IT).
- Cả hai loại phản ứng thị trường: chủ động (xuất khẩu: DE, FR, DK) và bị động (nhập khẩu: PL, IT, ES).
