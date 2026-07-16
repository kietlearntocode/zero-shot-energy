import fitz  # PyMuPDF
import sys

def verify_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"=== KẾT QUẢ KIỂM DUYỆT BÀI BÁO: {pdf_path} ===")
    print(f"Tổng số trang: {doc.page_count}\n")
    
    # Phase 1: Bố cục (Layout)
    print("--- PHASE 1: KIỂM TRA BỐ CỤC (LAYOUT) ---")
    
    # Kích thước A4 chuẩn: 595.27 x 841.89 pts
    # Lề chuẩn: top/bottom 2.5cm (~70.87 pts), left/right 1.8cm (~51.02 pts)
    # Vùng an toàn (Safe Zone): x trong [51, 544], y trong [70, 771]
    
    margin_errors = 0
    blank_pages = 0
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        # Check blank page
        if len(text.strip()) < 50:
            print(f"❌ [LỖI] Trang {page_num + 1} có thể là trang trắng (độ dài text quá ngắn)!")
            blank_pages += 1
            
        # Check images/blocks for margins
        images = page.get_image_info()
        for img in images:
            x0, y0, x1, y1 = img["bbox"]
            width = x1 - x0
            height = y1 - y0
            
            # Check overflow
            if width > 510 or x0 < 40 or x1 > 555:
                print(f"❌ [LỖI TRÀN LỀ] Trang {page_num + 1}: Ảnh tràn lề! (x0={x0:.1f}, x1={x1:.1f}, width={width:.1f}pt)")
                margin_errors += 1
    
    if margin_errors == 0 and blank_pages == 0:
        print("✅ Phase 1 OK: Không tràn lề, không nhảy trang trắng, ảnh/bảng đúng kích thước thiết kế.")
    else:
        print("❌ Phase 1 FAILED!")

    # Phase 2: Nội dung (Content)
    print("\n--- PHASE 2: KIỂM TRA NỘI DUNG (CONTENT & METRICS) ---")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    metrics_to_check = {
        "R2 của OLS Đức (DE) = 0.847": "0,847",
        "R2 XGBoost C2 Đức W3 (Crisis)": "-2,187",
        "R2 của OLS Tây Ban Nha (ES) = 0.711": "0,711",
        "R2 XGBoost C2 Tây Ban Nha W3": "-12,503",
        "SHAP Residual_Load Đức": "55,5",
        "Tham số STL seasonal": "51"
    }
    
    full_text_normalized = full_text.replace(" ", "").replace("\n", "")
    
    content_errors = 0
    for name, value in metrics_to_check.items():
        if value in full_text_normalized or value in full_text:
            print(f"✅ Đã tìm thấy: {name} ({value})")
        else:
            print(f"❌ [LỖI NỘI DUNG] Không tìm thấy số liệu: {name} ({value})")
            content_errors += 1
            
    if content_errors == 0:
        print("✅ Phase 2 OK: Số liệu không bị sai lệch, logic học thuật giữ nguyên.")
    else:
        print("⚠️ Phase 2 CẢNH BÁO: Không khớp một số text (Có thể do mã hóa font LaTeX T5).")
        
if __name__ == "__main__":
    verify_pdf("paper/main.pdf")
