# Time Series Decomposition Report (STL)

## Method
Seasonal-Trend decomposition using LOESS (STL) with:
- **Period = 8760 hours** (annual seasonality)
- **Robust = True** (resistant to outliers/spikes)
- Applied to `Real_Wholesale_Price_EUR` for each of 6 countries, 2018-2025

## Key Statistics

| Country | Mean Price | Std Dev | Max Residual | Max Residual Date | Crisis Residual % |
|---|---|---|---|---|---|
| DE | 76.0 | 71.1 | -639.7 | 2025-12-12 | 381.0% |
| DK | 72.9 | 70.2 | 530.7 | 2022-08-26 | 368.6% |
| ES | 70.5 | 51.4 | 402.9 | 2022-03-08 | 317.2% |
| FR | 81.2 | 85.2 | 540.4 | 2022-08-29 | 410.8% |
| IT | 106.0 | 86.1 | 530.3 | 2022-08-29 | 455.8% |
| PL | 70.7 | 35.7 | 229.1 | 2021-12-22 | 301.2% |

## Key Finding: Residual Explosion in 2022
The STL decomposition reveals that while Trend and Seasonal components remained structurally intact during 2021-2022, the **Residual component spiked dramatically** — reaching 200-400 EUR/MWh above the seasonal baseline. This demonstrates that standard time series structure (trend + seasonality) cannot explain the crisis: **exogenous variables are required**.

This finding directly motivates the feature engineering approach in Section 3: TTF Gas Price, EU Gas Storage Anomaly, and Residual Load as key explanatory variables.

## Figures

![DE_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/DE_stl_annual.png)

![DK_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/DK_stl_annual.png)

![ES_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/ES_stl_annual.png)

![FR_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/FR_stl_annual.png)

![IT_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/IT_stl_annual.png)

![PL_stl_annual.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/PL_stl_annual.png)

![all_countries_trend_comparison.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/all_countries_trend_comparison.png)

![all_countries_residual_crisis.png](file:///D:/Projects/data/ember/reports/figures/00_ts_decomposition/all_countries_residual_crisis.png)
