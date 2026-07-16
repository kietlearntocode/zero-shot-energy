# Nguyên Tắc Làm Việc (Agent Rules)

Dự án: **European Wholesale Electricity Price Modeling (Ember)**

Tài liệu này tổng hợp các nguyên tắc bắt buộc mà Agent (AI) phải tuân thủ khi làm việc trên dự án này, được đúc kết từ các yêu cầu và phản hồi của người dùng.

## 1. Thái độ & Tương tác
- No Yes-Man: Phản biện trên cơ sở logic, toán học và bằng chứng.
- Answer and Execute: Trả lời trực tiếp, tuyệt đối phải trao đổi xong thì mới execute. CHỈ THỊ TUYỆT ĐỐI: Khi đề xuất một bản kế hoạch hoặc phương án sửa lỗi, AI **PHẢI DỪNG MỌI TOOL CALLS NGAY LẬP TỨC** và trả quyền điều khiển cho người dùng. KHÔNG ĐƯỢC PHÉP gộp chung việc "nộp kế hoạch" và "chạy code/sửa file" vào trong cùng một lượt phản hồi. Chỉ khi người dùng nói rõ "Đồng ý", "Chạy đi", AI mới được phép bắt đầu thi hành.
- No Empty Words: Ưu tiên thuật ngữ có nội hàm kỹ thuật rõ ràng.

## 2. Kiến trúc & Tài liệu
- Atomic Structure: Mỗi thuật toán là một đơn vị độc lập.
- Strict Split:
  `docs/algorithms/` -> toán học, giả định, tham số.
  `reports/` -> diễn giải nghiệp vụ, biểu đồ, kết luận.
- Math First: Thuật toán phải được mô tả bằng công thức trước khi triển khai.
- Docs Before Code.

## 3. Mã nguồn
- Lean Code: Chỉ giữ các thành phần phục vụ mục tiêu hiện tại. Tuy nhiên, KHÔNG cực đoan (Ví dụ: Không được loại bỏ hoàn toàn các metric đánh giá cơ bản như RMSE/MAE vì chúng là bức tranh tổng thể đảm bảo mô hình đang hoạt động hợp lý dù mục tiêu chính là giải thích hệ số).
- Reproducible Research: Bảo toàn khả năng tái lập. Không xóa các script thử nghiệm nháp ngay lập tức mà hãy lưu trữ vào Git history hoặc thư mục `archive/` để phục vụ truy vết.

## 4. Reality Validation
- Mọi hiện tượng bất thường phải được kiểm chứng bằng dữ liệu hoặc nguồn bên ngoài.
- Báo cáo phải đính kèm nguồn tham khảo khi đưa ra nhận định thực nghiệm.

## 5. Workflow
- Interleaved Workflow:
  Theory → Code → Validation → Report.
- Mỗi vòng lặp phải tạo ra kết quả có thể kiểm chứng độc lập.

## 6. Quy Tắc Kế Thừa (Dữ liệu & Cấu trúc Cũ)
- Tuân thủ nguyên tắc `NaN Handling` (Không dùng `fillna(0)` mù quáng), Tôn trọng `Panel Data` không cân bằng, và kiểm duyệt Data Leakage nghiêm ngặt ở các Phase trước.
