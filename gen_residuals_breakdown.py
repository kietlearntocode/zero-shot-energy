"""
gen_residuals_breakdown.py
===========================
Tái tạo biểu đồ OLS Residuals vs Actual Price — Breakdown by Price Region
- Layout: 2 cột x 3 hàng
- Trục X và Y THỐNG NHẤT (shared) cho cả 6 quốc gia
- Màu chuẩn:
    High (>P90) → đỏ    #e74c3c
    Low  (<P10) → xanh dương   #3498db
    Mid         → xanh lá  #2ecc71
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# ── Đường dẫn ──────────────────────────────────────────────────────────────────
ROOT     = r"d:\Projects\data\ember"
DATA_CSV = os.path.join(ROOT, 'data', 'processed', 'electricity_dataset.csv')
OUT_DIR  = os.path.join(ROOT, 'reports', 'figures', 'scratch')
os.makedirs(OUT_DIR, exist_ok=True)

# Thêm src vào path để dùng SAFE_FEATURES từ baseline.py
sys.path.insert(0, os.path.join(ROOT, 'src'))
try:
    from models.baseline import SAFE_FEATURES, TARGET
except ImportError:
    # Fallback nếu không import được
    TARGET = "Real_Wholesale_Price_EUR"
    SAFE_FEATURES = [
        "Load", "Residual_Load", "Net_Import",
        "TTF_Gas_Price", "Coal_Price", "EU_ETS_Price",
        "Brent_Oil_Price", "EU_Gas_Storage_Anomaly",
        "Wind_Onshore_MW", "Wind_Offshore_MW", "Solar_MW",
        "Biomass_MW", "Geothermal_MW", "Hydro_RoR_MW", "Hydro_Reservoir_MW",
        "Nuclear_MW",
        "Hour_Sin", "Hour_Cos",
    ]

COUNTRIES = ['DE', 'DK', 'ES', 'FR', 'IT', 'PL']

PALETTE = {
    'High (>P90)': '#e74c3c',   # Đỏ
    'Low (<P10)':  '#3498db',   # Xanh dương
    'Mid':         '#2ecc71',   # Xanh lá
}

LABEL_ORDER = ['High (>P90)', 'Low (<P10)', 'Mid']


def fit_ols(df, features):
    avail = [f for f in features if f in df.columns and f != 'Residual_Load' and not df[f].isnull().all()]
    sub = df[avail + [TARGET]].dropna()
    X = sub[avail]
    y = sub[TARGET]
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    residuals = pd.Series(y.values - y_pred, index=sub.index, name="OLS_Residual")
    r2 = float(r2_score(y, y_pred))
    return model, residuals, r2


def main():
    print(f"Loading {DATA_CSV}...")
    df = pd.read_csv(DATA_CSV, low_memory=True)
    print(f"Loaded {len(df):,} rows, {len(df.columns)} cols")

    # ── Fit OLS và thu thập tất cả residuals để tính global axis limits ─────────
    all_actuals   = []
    all_residuals = []
    data_per_country = {}

    for country in COUNTRIES:
        df_c = df[df['Country'] == country].copy()
        if df_c.empty:
            print(f"  [WARN] No data for {country}")
            continue

        _, residuals, r2 = fit_ols(df_c, SAFE_FEATURES)
        # Gán residuals theo index (sau khi dropna, rows có NaN đã bị loại bỏ)
        df_c['Residual'] = residuals
        df_c = df_c.loc[residuals.index]   # chỉ giữ các hàng có đủ features

        p10 = df_c[TARGET].quantile(0.10)
        p90 = df_c[TARGET].quantile(0.90)

        def cat(p):
            if p < p10:   return 'Low (<P10)'
            elif p > p90: return 'High (>P90)'
            else:          return 'Mid'

        df_c['PriceRegion'] = df_c[TARGET].apply(cat)

        all_actuals.append(df_c[TARGET])
        all_residuals.append(df_c['Residual'])
        data_per_country[country] = (df_c, r2)

    # ── Tính global limits (bỏ qua 1% outlier cực đoan) ────────────────────────
    # Khóa cứng các mốc giới hạn để tránh bị nhiễu bởi các điểm outlier cực đoan (như 2800 ở Pháp)
    x_min = -150
    x_max = 1000
    y_min = -300
    y_max = 1000

    print(f"Global X: [{x_min:.0f}, {x_max:.0f}]  |  Global Y: [{y_min:.0f}, {y_max:.0f}]")

    from matplotlib.ticker import MultipleLocator

    # ── Vẽ biểu đồ ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    axes_flat = axes.flatten()

    for idx, country in enumerate(COUNTRIES):
        if country not in data_per_country:
            axes_flat[idx].set_visible(False)
            continue

        df_c, r2 = data_per_country[country]
        ax = axes_flat[idx]

        for region in LABEL_ORDER:
            grp = df_c[df_c['PriceRegion'] == region]
            ax.scatter(
                grp[TARGET], grp['Residual'],
                alpha=0.15, s=4,
                label=region,
                color=PALETTE[region],
                rasterized=True,
            )

        ax.axhline(0, color='black', lw=0.9, ls='--')
        ax.set_title(f'{country}   $R^2$={r2:.3f}', fontsize=13, fontweight='bold')
        ax.set_xlabel('Actual Price (EUR/MWh)', fontsize=10)
        ax.set_ylabel('OLS Residual (EUR/MWh)', fontsize=10)

        # Áp dụng global limits
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        
        # Thiết lập mốc chia lưới
        ax.xaxis.set_major_locator(MultipleLocator(150))
        ax.yaxis.set_major_locator(MultipleLocator(150))

        ax.legend(
            handles=[
                matplotlib.patches.Patch(color=PALETTE[r], label=r)
                for r in LABEL_ORDER
            ],
            markerscale=4, fontsize=9, loc='upper left'
        )
        ax.grid(True, alpha=0.3)

    plt.suptitle(
        'OLS Residuals vs Actual Price — Breakdown by Price Region',
        fontsize=15, fontweight='bold', y=1.01
    )
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, 'residuals_breakdown_fixed.png')
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    print(f"\n[OK] Saved → {out_path}")
    plt.close()


if __name__ == '__main__':
    main()
