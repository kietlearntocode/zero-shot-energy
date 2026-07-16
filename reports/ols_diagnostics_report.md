# OLS Diagnostics Report

Kiểm tra các giả định của mô hình Hồi quy tuyến tính Cổ điển (OLS).

Lưu ý: Biến `Residual_Load` được loại bỏ khỏi danh sách kiểm tra VIF vì nó là tổ hợp tuyến tính chính xác của `Load`, `Wind`, `Solar` và `Hydro_RoR` (sẽ gây VIF = vô cực).


## Quốc gia: DE

### Thống kê chung
- **Durbin-Watson**: 0.12 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 8.1255e-20 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 9.72 | 🟡 Cao |
| TTF_Gas_Price | 6.51 | 🟡 Cao |
| Brent_Oil_Price | 3.75 | 🟢 Tốt |
| Hour_Cos | 3.53 | 🟢 Tốt |
| Solar_MW | 3.39 | 🟢 Tốt |
| Biomass_MW | 3.32 | 🟢 Tốt |
| Load | 2.53 | 🟢 Tốt |
| Nuclear_MW | 2.18 | 🟢 Tốt |
| Geothermal_MW | 2.09 | 🟢 Tốt |
| Wind_Onshore_MW | 1.88 | 🟢 Tốt |
| Wind_Offshore_MW | 1.73 | 🟢 Tốt |
| Hydro_Reservoir_MW | 1.56 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.54 | 🟢 Tốt |
| EU_ETS_Price | 1.50 | 🟢 Tốt |
| Hydro_RoR_MW | 1.41 | 🟢 Tốt |
| Hour_Sin | 1.14 | 🟢 Tốt |

---

## Quốc gia: DK

### Thống kê chung
- **Durbin-Watson**: 0.13 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 6.6459e-12 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 9.71 | 🟡 Cao |
| TTF_Gas_Price | 6.38 | 🟡 Cao |
| Brent_Oil_Price | 3.33 | 🟢 Tốt |
| Load | 2.94 | 🟢 Tốt |
| Wind_Offshore_MW | 2.87 | 🟢 Tốt |
| Hour_Cos | 2.69 | 🟢 Tốt |
| Wind_Onshore_MW | 2.67 | 🟢 Tốt |
| Solar_MW | 1.66 | 🟢 Tốt |
| Biomass_MW | 1.65 | 🟢 Tốt |
| EU_ETS_Price | 1.34 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.27 | 🟢 Tốt |
| Hour_Sin | 1.03 | 🟢 Tốt |
| Geothermal_MW | nan | 🟢 Tốt |
| Hydro_RoR_MW | nan | 🟢 Tốt |
| Hydro_Reservoir_MW | nan | 🟢 Tốt |
| Nuclear_MW | nan | 🟢 Tốt |

---

## Quốc gia: ES

### Thống kê chung
- **Durbin-Watson**: 0.07 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 6.6267e-06 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 9.70 | 🟡 Cao |
| TTF_Gas_Price | 6.34 | 🟡 Cao |
| Brent_Oil_Price | 3.46 | 🟢 Tốt |
| Hydro_Reservoir_MW | 2.92 | 🟢 Tốt |
| Hour_Cos | 2.88 | 🟢 Tốt |
| Solar_MW | 2.63 | 🟢 Tốt |
| Hydro_RoR_MW | 2.46 | 🟢 Tốt |
| Load | 2.37 | 🟢 Tốt |
| EU_ETS_Price | 1.96 | 🟢 Tốt |
| Biomass_MW | 1.73 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.39 | 🟢 Tốt |
| Wind_Onshore_MW | 1.30 | 🟢 Tốt |
| Nuclear_MW | 1.21 | 🟢 Tốt |
| Hour_Sin | 1.18 | 🟢 Tốt |
| Wind_Offshore_MW | nan | 🟢 Tốt |
| Geothermal_MW | nan | 🟢 Tốt |

---

## Quốc gia: FR

### Thống kê chung
- **Durbin-Watson**: 0.23 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 1.3135e-11 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 10.37 | 🔴 Nguy hiểm |
| TTF_Gas_Price | 6.90 | 🟡 Cao |
| Load | 4.06 | 🟢 Tốt |
| Nuclear_MW | 3.92 | 🟢 Tốt |
| Brent_Oil_Price | 3.34 | 🟢 Tốt |
| Solar_MW | 2.83 | 🟢 Tốt |
| Hydro_Reservoir_MW | 2.81 | 🟢 Tốt |
| Hour_Cos | 2.62 | 🟢 Tốt |
| Hydro_RoR_MW | 1.92 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.55 | 🟢 Tốt |
| Wind_Onshore_MW | 1.54 | 🟢 Tốt |
| EU_ETS_Price | 1.49 | 🟢 Tốt |
| Wind_Offshore_MW | 1.47 | 🟢 Tốt |
| Biomass_MW | 1.17 | 🟢 Tốt |
| Hour_Sin | 1.05 | 🟢 Tốt |
| Geothermal_MW | nan | 🟢 Tốt |

---

## Quốc gia: IT

### Thống kê chung
- **Durbin-Watson**: 0.15 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 1.8185e-18 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 9.65 | 🟡 Cao |
| TTF_Gas_Price | 6.67 | 🟡 Cao |
| Hydro_Reservoir_MW | 4.73 | 🟢 Tốt |
| Brent_Oil_Price | 3.62 | 🟢 Tốt |
| Hour_Cos | 3.35 | 🟢 Tốt |
| Hydro_RoR_MW | 3.16 | 🟢 Tốt |
| Solar_MW | 3.03 | 🟢 Tốt |
| Load | 2.55 | 🟢 Tốt |
| EU_ETS_Price | 1.68 | 🟢 Tốt |
| Biomass_MW | 1.50 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.48 | 🟢 Tốt |
| Geothermal_MW | 1.48 | 🟢 Tốt |
| Wind_Offshore_MW | 1.36 | 🟢 Tốt |
| Wind_Onshore_MW | 1.28 | 🟢 Tốt |
| Hour_Sin | 1.23 | 🟢 Tốt |
| Nuclear_MW | nan | 🟢 Tốt |

---

## Quốc gia: PL

### Thống kê chung
- **Durbin-Watson**: 0.24 *(Kỳ vọng: ~2.0. Dưới 2: Tự tương quan thuận)*
- **ADF Test (Residuals)**: p-value = 3.8896e-18 *(Kỳ vọng: < 0.05 để chuỗi dừng)*
- **Kết luận ADF**: Phần dư DỪNG (Stationary). Các biến có hiện tượng đồng liên kết (Cointegration), mô hình tuyến tính có ý nghĩa không bị hồi quy giả mạo (Spurious Regression).

### Kiểm tra Đa cộng tuyến (VIF)
| Biến | VIF | Đánh giá (Threshold = 10) |
|---|---|---|
| Coal_Price | 9.62 | 🟡 Cao |
| TTF_Gas_Price | 6.78 | 🟡 Cao |
| Brent_Oil_Price | 3.55 | 🟢 Tốt |
| Hour_Cos | 2.17 | 🟢 Tốt |
| Load | 1.88 | 🟢 Tốt |
| Solar_MW | 1.59 | 🟢 Tốt |
| Hydro_RoR_MW | 1.48 | 🟢 Tốt |
| EU_ETS_Price | 1.44 | 🟢 Tốt |
| Biomass_MW | 1.33 | 🟢 Tốt |
| EU_Gas_Storage_Anomaly | 1.32 | 🟢 Tốt |
| Hydro_Reservoir_MW | 1.21 | 🟢 Tốt |
| Hour_Sin | 1.12 | 🟢 Tốt |
| Wind_Onshore_MW | 1.07 | 🟢 Tốt |
| Wind_Offshore_MW | nan | 🟢 Tốt |
| Geothermal_MW | nan | 🟢 Tốt |
| Nuclear_MW | nan | 🟢 Tốt |

---
