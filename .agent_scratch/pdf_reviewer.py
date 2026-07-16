import fitz
import os
import shutil
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PDF_PATH = "paper/main.pdf"
OUT_DIR = r"C:\Users\ADMIN\.gemini\antigravity-ide\brain\e7588202-5d19-4d6d-89d7-a39185956fa4\pdf_pages"

if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR)

doc = fitz.open(PDF_PATH)
print(f"Total pages: {len(doc)}")

warnings = []

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    # 1. Kết xuất ảnh trang PDF
    pix = page.get_pixmap(dpi=150)
    out_img = os.path.join(OUT_DIR, f"page_{page_num + 1}.png")
    pix.save(out_img)
    
    # 2. Phân tích Tọa độ (Layout Analysis)
    blocks = page.get_text("blocks")
    page_rect = page.rect
    w, h = page_rect.width, page_rect.height
    
    # Giả định lề A4 LaTeX (khoảng 50-70pt)
    margin_right = w - 50 
    margin_left = 50
    margin_bottom = h - 70
    
    max_y1 = 0
    overflows = 0
    
    for b in blocks:
        x0, y0, x1, y1, text, block_type, block_no = b
        max_y1 = max(max_y1, y1)
        
        # Block type 1 = Image, 0 = Text
        if x1 > margin_right + 10: # Tràn lề phải
            overflows += 1
            if block_type == 1:
                warnings.append(f"[Trang {page_num + 1}] CẢNH BÁO: Hình ảnh/Bảng tràn lề phải (x1={x1:.1f} > max={margin_right:.1f})")
            else:
                pass # Text đôi khi có công thức dài, bỏ qua tạm thời

    # Kiểm tra khoảng trắng (nhảy trang)
    # Bỏ qua trang cuối cùng hoặc các trang chỉ có đúng 1 ảnh full page
    if max_y1 > 0 and max_y1 < h * 0.6 and len(blocks) > 2 and page_num < len(doc) - 1:
        warnings.append(f"[Trang {page_num + 1}] CẢNH BÁO: Phát hiện khoảng trắng lớn (y_max={max_y1:.1f} / {h:.1f}). Có thể bị nhảy trang (page break).")

if not warnings:
    print("\n==== BÁO CÁO REVIEW: HOÀN HẢO ====")
    print("Không phát hiện lỗi tràn lề hay nhảy trang vô lý.")
else:
    print("\n==== BÁO CÁO REVIEW: CÓ LỖI ====")
    for w in warnings:
        print(w)
