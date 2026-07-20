@echo off
echo ===================================================
echo Khởi động Hệ thống Dự báo Giá điện (Ember)
echo ===================================================
echo.

echo [1/2] Đang bật Backend (FastAPI) trong cửa sổ mới...
start "Backend - FastAPI" cmd /k ".\venv\Scripts\activate && cd web_app\api_server && uvicorn main:app --reload --port 8000"

echo [2/2] Đang bật Frontend (Vue) trong cửa sổ mới...
start "Frontend - Vue/Vite" cmd /k "cd web_app\ui_client && npm run dev"

echo.
echo Hoàn tất! Vui lòng chờ vài giây để 2 server chạy xong.
echo Sau đó hãy mở trình duyệt và truy cập: http://localhost:5173
echo.
pause
