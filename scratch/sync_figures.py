import os
import shutil
import glob

def clean_dir(d):
    for f in glob.glob(os.path.join(d, "*.png")):
        os.remove(f)

# Thư mục đích
PAPER_METH = "paper/figures/methodology"
PAPER_RES = "paper/figures/results"

# Xóa ảnh cũ
clean_dir(PAPER_METH)
clean_dir(PAPER_RES)
print("Đã xóa sạch ảnh cũ trong paper/figures/")

# Thư mục nguồn
REP_METH = "reports/figures/00_ts_decomposition"
REP_OLS = "reports/figures/01_ols_baseline"
REP_UMAP = "reports/figures/02_regimes"
REP_XGB = "reports/figures/03_xgboost"

# 1. STL (reports/figures/00_ts_decomposition/DE_stl.png -> paper/figures/methodology/DE_stl_annual.png)
shutil.copy(os.path.join(REP_METH, "DE_stl.png"), os.path.join(PAPER_METH, "DE_stl_annual.png"))
shutil.copy(os.path.join(REP_METH, "all_countries_seasonal.png"), os.path.join(PAPER_METH, "all_countries_seasonal.png"))
shutil.copy(os.path.join(REP_METH, "all_countries_residual_crisis.png"), os.path.join(PAPER_METH, "all_countries_residual_crisis.png"))

trend_png = os.path.join(REP_METH, "all_countries_trend.png")
if os.path.exists(trend_png):
    shutil.copy(trend_png, os.path.join(PAPER_METH, "all_countries_trend_comparison.png"))

# 2. OLS
ols_png = os.path.join(REP_OLS, "residuals_breakdown.png")
if os.path.exists(ols_png):
    shutil.copy(ols_png, os.path.join(PAPER_METH, "residuals_breakdown.png"))

# 3. UMAP
umap_png = os.path.join(REP_UMAP, "umap_clusters.png")
if os.path.exists(umap_png):
    shutil.copy(umap_png, os.path.join(PAPER_RES, "umap_hdbscan_regime_clusters.png"))
else:
    print(f"Warning: {umap_png} không tồn tại!")

regime_price = os.path.join(REP_UMAP, "regime_price_distribution.png")
if os.path.exists(regime_price):
    shutil.copy(regime_price, os.path.join(PAPER_RES, "regime_price_distribution.png"))

# 4. XGBoost
xgb_files = glob.glob(os.path.join(REP_XGB, "*.png"))
for f in xgb_files:
    basename = os.path.basename(f)
    shutil.copy(f, os.path.join(PAPER_RES, basename))

print("Đồng bộ ảnh hoàn tất!")
