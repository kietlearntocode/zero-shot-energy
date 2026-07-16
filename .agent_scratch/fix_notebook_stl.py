import json
import re

notebook_path = "notebooks/01_ts_decomposition.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell["cell_type"] == "code":
        source = "".join(cell["source"])
        
        # Sửa biểu đồ Seasonal
        seasonal_old = """    ax.fill_between(seasonal.index, seasonal.values, 0,
                    where=(seasonal.index < CRISIS_START) | (seasonal.index > CRISIS_END),
                    color='lightgray', alpha=0.5)
    ax.fill_between(seasonal.index, seasonal.values, 0,
                    where=((seasonal.index >= CRISIS_START) & (seasonal.index <= CRISIS_END)),
                    color=COLORS_GRID[country], alpha=0.8)"""
        
        seasonal_new = """    ax.fill_between(seasonal.index, seasonal.values, 0,
                    color=COLORS_GRID[country], alpha=0.8)"""
        
        if seasonal_old in source:
            source = source.replace(seasonal_old, seasonal_new)
            
        # Sửa biểu đồ Residual
        residual_old = """    ax.fill_between(residual.index, resid_pos.values, 0,
                    where=((residual.index >= CRISIS_START) & (residual.index <= CRISIS_END)),
                    color=COLORS_GRID[country], alpha=0.8)
    ax.fill_between(residual.index, resid_pos.values, 0,
                    where=(residual.index < CRISIS_START) | (residual.index > CRISIS_END),
                    color='lightgray', alpha=0.4)
    ax.fill_between(residual.index, resid_neg.values, 0,
                    color='lightgray', alpha=0.4)"""
                    
        residual_new = """    ax.fill_between(residual.index, residual.values, 0,
                    color=COLORS_GRID[country], alpha=0.8)"""
                    
        if residual_old in source:
            source = source.replace(residual_old, residual_new)

        # Chuyển string thành list các dòng để lưu lại chuẩn Jupyter JSON format
        lines = source.splitlines(True)
        cell["source"] = lines

with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    # Thêm newline ở cuối file để chuẩn định dạng JSON của Jupyter
    f.write("\n")

print("Notebook 01 updated successfully.")
