import re

# 1. Read files
with open("paper/sections/results.tex", "r", encoding="utf-8") as f:
    res = f.read()
with open("paper/sections/appendix.tex", "r", encoding="utf-8") as f:
    app = f.read()

# 2. Extract tab:hdbscan_results
table_pattern = r'\\begin\{table\}\[bp\].*?\\caption\{Cấu hình HDBSCAN tối ưu và chỉ số đánh giá theo quốc gia\}.*?\\end\{table\}'
table_match = re.search(table_pattern, res, flags=re.DOTALL)
if table_match:
    table_block = table_match.group(0)
    # Remove it from results.tex
    res = res.replace(table_block, "")
    
    # Add it to appendix.tex under \section{Kết quả thực nghiệm bổ sung (Sáu quốc gia)}
    app_target = "\\section{Kết quả thực nghiệm bổ sung (Sáu quốc gia)}\n\\label{app:ml_results}\n"
    app = app.replace(app_target, app_target + "\n" + table_block + "\n")
else:
    print("Could not find tab:hdbscan_results in results.tex!")

# 3. Add DE_r2_evolution.png after tab:wf_results_full
# The Walk-Forward table ends with:
# \vspace{0.3em}
# \parbox{\textwidth}{\small\textit{Ghi chú:} CÁC GIÁ TRỊ R^2... năm 2022.}
# \end{strip}
wf_end_pattern = r'(cuộc khủng hoảng năng lượng châu Âu năm 2022\.\}\\n\\end\{strip\})'
# Let's just find \end{strip} after \label{tab:wf_results_full}
start_wf = res.find(r"\label{tab:wf_results_full}")
if start_wf != -1:
    end_strip = res.find(r"\end{strip}", start_wf) + len(r"\end{strip}")
    
    # Prepare the R2 block
    r2_block = """

  \\Needspace*{0.4\\textheight}
  \\begin{strip}
    \\centering
    \\begin{adjustbox}{max width=\\textwidth}
      \\includegraphics{figures/results/DE_r2_evolution.png}
    \\end{adjustbox}
    \\captionof{figure}{Tiến hóa của chỉ số $R^2$ qua sáu cửa sổ walk-forward tại thị trường đại diện Đức (DE). Đường đỏ biểu diễn mô hình $C_1$ (nhân quả), đường xanh biểu diễn mô hình $C_2$ (kết hợp nhãn thể chế vật lý). Vùng nền cam đánh dấu giai đoạn nổ ra khủng hoảng.}
    \\label{fig:r2_evolution}
  \\end{strip}

Các kết quả trên mang lại bốn phát hiện thực nghiệm quan trọng:
"""
    # Insert it
    res = res[:end_strip] + r2_block + res[end_strip:]
else:
    print("Could not find tab:wf_results_full in results.tex!")

# Write back
with open("paper/sections/results.tex", "w", encoding="utf-8") as f:
    f.write(res)
with open("paper/sections/appendix.tex", "w", encoding="utf-8") as f:
    f.write(app)

print("Table moved and R2 evolution image added!")
