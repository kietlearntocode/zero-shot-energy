# Phase 1: Data Ingestion Reference

Tài liệu này đặc tả các API, thư viện, và phương thức kỹ thuật được sử dụng để thu thập dữ liệu thô (Raw Data) từ năm 2018 đến 2025 cho 17 quốc gia Châu Âu.

## 1. Môi trường Mạng & Cấu hình Kỹ thuật
* **Timezone chuẩn:** Toàn bộ dữ liệu được ép (tz_localize/tz_convert) về **UTC** ngay khi tải xuống để đồng bộ hóa.
* **Cơ chế Retry/Cache:** 
  * Sử dụng thư viện `requests-cache` tạo file `.cache.sqlite` để tránh request trùng lặp.
  * Sử dụng thư viện `retry-requests` với cấu hình: `retries=5`, `backoff_factor=0.2` để xử lý Rate Limits từ API Châu Âu.

## 2. Các Nguồn Dữ Liệu & API Endpoints

### 2.1. Năng Lượng & Phụ Tải (ENTSO-E Transparency Platform)
* **Thư viện:** `entsoe-py` (`EntsoePandasClient`)
* **Xác thực:** API Token (cấu hình trong file `.env`)
* **Endpoints sử dụng:**
  * `query_generation(country_code, start, end, psr_type=None)`: Lấy sản lượng điện theo từng loại nhiên liệu (Nuclear, Wind, Solar, Fossil Gas, Fossil Hard coal, v.v...).
  * `query_load(country_code, start, end)`: Lấy phụ tải thực tế (Actual Total Load).
  * `query_wind_and_solar_forecast(country_code, start, end)`: Dự báo Tái tạo.
  * `query_day_ahead_prices(country_code, start, end)`: Giá điện bán buôn.
* **Xử lý đặc thù:** Dữ liệu ENTSO-E thường trả về độ phân giải 15 phút (đối với Đức/Hà Lan) hoặc 60 phút (Pháp/Tây Ban Nha). Tất cả được **resample('1H').mean()** để đồng bộ về mốc 1 giờ.

### 2.2. Khí hậu & Thời tiết (Open-Meteo & Copernicus ERA5)
* **Thư viện:** `openmeteo-requests`
* **API Endpoints:** `https://archive-api.open-meteo.com/v1/archive` (Dữ liệu quá khứ)
* **Parameters (Tham số):** 
  * `latitude`, `longitude` (Tọa độ thủ đô hoặc trung tâm tải của từng quốc gia).
  * Tọa độ tham chiếu (Ví dụ: Berlin `52.5200, 13.4050`, Paris `48.8566, 2.3522`).
  * Biến số: `temperature_2m`, `wind_speed_10m`, `shortwave_radiation` (Bức xạ mặt trời).
* **Độ phân giải:** Hourly.

### 2.3. Vĩ mô (Lạm phát - Cục Dự trữ Liên bang Mỹ FRED)
* **Thư viện:** `pandas_datareader` hoặc request HTTP trực tiếp.
* **Mã dữ liệu (Series ID):** `CPALTT01EZM659N` (Consumer Price Index for Euro Area).
* **Xử lý:** Dữ liệu lạm phát là dữ liệu Tháng (Monthly). Để đồng bộ với tập Hourly, sử dụng phép `ffill()` (Forward Fill) vào ngày đầu tiên của mỗi tháng, điền cho toàn bộ các giờ trong tháng đó.

### 2.4. Giá Khí đốt & Carbon (Yahoo Finance)
* **Thư viện:** `yfinance`
* **Tickers:**
  * `TTF=F` (Dutch TTF Natural Gas Futures - Chỉ báo giá khí đốt tiêu chuẩn Châu Âu).
  * Biến Carbon (EU ETS) có thể được mock hoặc kéo từ `KEUA` tuỳ tình trạng API.
* **Xử lý:** Đây là dữ liệu giao dịch Ngày (Daily). Áp dụng Forward Fill (`ffill()`) cho các ngày cuối tuần (Thứ 7, CN không giao dịch) và trải đều cho 24 giờ trong ngày.

## 3. Quản lý Lỗi (Failure Handling)
* **Fail-fast Threshold:** Khi merge các nguồn lại cho một quốc gia (ví dụ `energy_DE.csv`), nếu biến `Wholesale_Price` hoặc `Load` bị thiếu (NaN) lớn hơn **5%** tổng số hàng của kỳ (2018-2025), script `fetch_energy.py` sẽ raise `ValueError` và loại bỏ quốc gia đó khỏi Pipeline thay vì thực hiện nội suy (Interpolation) rủi ro cao.
