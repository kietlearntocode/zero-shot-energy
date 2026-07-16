import json
import os
import re

# 1. Update Notebook 01
notebook_path = "notebooks/01_ts_decomposition.ipynb"
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        if "plt.subplots(3, 2, figsize=(14, 12)" in source:
            source = source.replace("plt.subplots(3, 2, figsize=(14, 12)", "plt.subplots(2, 3, figsize=(18, 8)")
            cell["source"] = source.splitlines(True)

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")

# 2. Extract SHAP from results.tex
results_path = "paper/sections/results.tex"
with open(results_path, "r", encoding="utf-8") as f:
    results_text = f.read()

# Find the SHAP block \begin{strip} ... \end{strip}
shap_block_pattern = re.compile(r"\\begin\{strip\}.*?\\label\{tab:shap_c1\}.*?\\end\{strip\}", re.DOTALL)
shap_match = shap_block_pattern.search(results_text)
shap_block_appendix = ""
if shap_match:
    shap_block = shap_match.group(0)
    # Remove it from results.tex
    results_text = results_text.replace(shap_block, "")
    # Change \begin{strip} to \begin{table*}[h] and \end{strip} to \end{table*}
    shap_block_appendix = shap_block.replace(r"\begin{strip}", r"\begin{table*}[h]").replace(r"\end{strip}", r"\end{table*}")
    # Also change \captionof{table} to \caption
    shap_block_appendix = shap_block_appendix.replace(r"\captionof{table}", r"\caption")

# Find the UMAP and R2 Evolution strips and replace with figure*
def fix_figure_strip(text, label):
    pattern = re.compile(r"\\Needspace.*?\n\\begin\{strip\}.*?\\label\{" + label + r"\}.*?\\end\{strip\}", re.DOTALL)
    match = pattern.search(text)
    if not match:
        pattern = re.compile(r"\\begin\{strip\}.*?\\label\{" + label + r"\}.*?\\end\{strip\}", re.DOTALL)
        match = pattern.search(text)
        
    if match:
        orig = match.group(0)
        inner = re.search(r"\\begin\{strip\}(.*?)\\end\{strip\}", orig, re.DOTALL).group(1)
        inner = inner.replace(r"\captionof{figure}", r"\caption")
        new_block = r"\begin{figure*}[h]" + inner + r"\end{figure*}"
        return text.replace(orig, new_block)
    return text

results_text = fix_figure_strip(results_text, "fig:umap_clusters")
results_text = fix_figure_strip(results_text, "fig:price_dist")
results_text = fix_figure_strip(results_text, "fig:r2_evolution")
results_text = fix_figure_strip(results_text, "fig:crisis_boundary_all")

# Fix Walk-Forward Table Strip
wf_pattern = re.compile(r"\\begin\{strip\}(.*?\\label\{tab:wf_results_full\}.*?)\\end\{strip\}", re.DOTALL)
wf_match = wf_pattern.search(results_text)
if wf_match:
    inner = wf_match.group(1).replace(r"\captionof{table}", r"\caption")
    new_block = r"\begin{table*}[h]" + inner + r"\end{table*}"
    results_text = results_text.replace(wf_match.group(0), new_block)

# Remove any remaining \Needspace
results_text = re.sub(r"\\Needspace.*?\n", "", results_text)

# 3. Read appendix.tex to extract HDBSCAN table
appendix_path = "paper/sections/appendix.tex"
with open(appendix_path, "r", encoding="utf-8") as f:
    appendix_text = f.read()

# Extract hdbscan table
hdbscan_pattern = re.compile(r"\\begin\{table\}\[bp\].*?\\label\{tab:hdbscan_results\}.*?\\end\{table\}\n*", re.DOTALL)
hdbscan_match = hdbscan_pattern.search(appendix_text)
hdbscan_table = ""
if hdbscan_match:
    hdbscan_table = hdbscan_match.group(0)
    appendix_text = appendix_text.replace(hdbscan_table, "")
    # Remove adjustbox
    hdbscan_table = re.sub(r"\\begin\{adjustbox\}\{.*?\}\n", "", hdbscan_table)
    hdbscan_table = hdbscan_table.replace(r"\end{adjustbox}" + "\n", "")
    hdbscan_table = hdbscan_table.replace("[bp]", "[h]")

# Insert HDBSCAN into results.tex exactly after the paragraph mentioning it
insert_marker = "phản ánh các mức tải và giá khí đốt khác nhau.\n"
if insert_marker in results_text and hdbscan_table:
    results_text = results_text.replace(insert_marker, insert_marker + "\n" + hdbscan_table.strip() + "\n\n")

with open(results_path, "w", encoding="utf-8") as f:
    f.write(results_text)

# 4. Modify appendix.tex
# Remove the 3 cluttered images
clutter_labels = ["fig:app_regime_timeline", "fig:app_r2_evolution", "fig:app_crisis_boundary"]
for label in clutter_labels:
    pattern = re.compile(r"\\begin\{figure\*\}.*?\\label\{" + label + r"\}.*?\\end\{figure\*\}(\n*)", re.DOTALL)
    appendix_text = re.sub(pattern, "", appendix_text)

# Fix STL images to use [h] instead of [bp]
appendix_text = appendix_text.replace(r"\begin{figure*}[bp]", r"\begin{figure*}[h]")

# Add SHAP tables at the end
if shap_block_appendix:
    appendix_text += "\n\\section{Bảng số liệu đóng góp đặc trưng (SHAP) chi tiết}\n\\label{app:shap_tables}\n\n"
    appendix_text += "Bảng~\\ref{tab:shap_c1} và Bảng~\\ref{tab:shap_c2} trình bày chi tiết giá trị đóng góp SHAP trung bình tuyệt đối cho từng đặc trưng tại sáu quốc gia.\n\n"
    appendix_text += shap_block_appendix + "\n"

with open(appendix_path, "w", encoding="utf-8") as f:
    f.write(appendix_text)

print("Migration script completed successfully!")
