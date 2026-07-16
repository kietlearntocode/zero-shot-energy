import os
import re

def fix_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex to find \begin{adjustbox}{...} \includegraphics{...} \end{adjustbox}
    # and replace with \includegraphics[width=\textwidth]{...}
    pattern = r'\\begin\{adjustbox\}\{[^\}]*\}\s*\\includegraphics\{([^}]+)\}\s*\\end\{adjustbox\}'
    
    # Replacement function
    def repl(m):
        img_path = m.group(1)
        return f'\\includegraphics[width=\\textwidth]{{{img_path}}}'

    new_content = re.sub(pattern, repl, content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Fixed {filepath}")

fix_file("paper/sections/results.tex")
fix_file("paper/sections/appendix.tex")

# Restore Appendix A completely
appendix_path = "paper/sections/appendix.tex"
with open(appendix_path, "r", encoding="utf-8") as f:
    app_content = f.read()

if r"\label{app:stl_decomposition}" not in app_content:
    stl_section = r"""
\section{Biểu đồ phân rã chuỗi thời gian STL chi tiết (Sáu quốc gia)}
\label{app:stl_decomposition}

\begin{figure*}[bp]
  \centering
  \includegraphics[width=\textwidth]{figures/methodology/all_countries_trend_comparison.png}
  \caption{So sánh xu hướng dài hạn ($T_t$) từ phân rã STL của sáu quốc gia (2018--2025). Vùng nền đỏ nhạt đánh dấu giai đoạn khủng hoảng năng lượng (7/2021--12/2022).}
  \label{fig:all_trend}
\end{figure*}

\begin{figure*}[bp]
  \centering
  \includegraphics[width=\textwidth]{figures/methodology/all_countries_seasonal.png}
  \caption{Thành phần mùa vụ ($S_t$) từ phân rã STL. Chu kỳ hàng năm được thể hiện rõ ràng, nhưng biên độ nhỏ và hoàn toàn không giải thích được các cú sốc giá.}
  \label{fig:all_seasonal}
\end{figure*}

\begin{figure*}[bp]
  \centering
  \includegraphics[width=\textwidth]{figures/methodology/all_countries_residual_crisis.png}
  \caption{Thành phần phần dư ($R_t$) từ phân rã STL. Phần dư bùng nổ cực đoan trong giai đoạn khủng hoảng, chứng minh thị trường bị chi phối bởi các yếu tố phi tuyến bên ngoài thay vì chu kỳ mùa vụ.}
  \label{fig:all_residual}
\end{figure*}

"""
    app_content = app_content.replace(r"\section{Kết quả thực nghiệm bổ sung", stl_section + r"\section{Kết quả thực nghiệm bổ sung")
    with open(appendix_path, "w", encoding="utf-8") as f:
        f.write(app_content)
    print("Restored STL section in appendix.tex")

