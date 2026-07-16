import re
import os

files_to_adjust = [
    "paper/sections/methodology.tex",
    "paper/sections/results.tex",
    "paper/sections/appendix.tex"
]

for filepath in files_to_adjust:
    if not os.path.exists(filepath): continue
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove the extra STL section in appendix
    if "appendix.tex" in filepath:
        # Pattern to match the whole section: from \section{Biểu đồ phân rã chuỗi thời gian STL chi tiết...} up to \section{Kết quả thực nghiệm bổ sung
        pattern_stl = r'\\section\{Biểu đồ phân rã chuỗi thời gian STL chi tiết \(Sáu quốc gia\)\}.*?(?=\\section\{Kết quả thực nghiệm bổ sung)'
        content = re.sub(pattern_stl, "", content, flags=re.DOTALL)

    # 2. Add max height to adjustbox for images so they don't bloat the paper
    # Change max width=\textwidth to max width=\textwidth, max height=0.45\textheight, keepaspectratio
    # But only for images. The tikzpicture in methodology.tex is already wrapped in max width=\textwidth, we can add max height to it too, it's fine.
    # Or just replace exactly:
    content = content.replace(
        r"\begin{adjustbox}{max width=\textwidth}",
        r"\begin{adjustbox}{max width=\textwidth, max height=0.45\textheight, keepaspectratio}"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Removed extra STL images and added max height to adjustboxes!")
