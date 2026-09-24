# ==============================================================================
# Kịch bản PowerShell thiết lập biến môi trường Ollama trên Windows (Hồ sơ gpu8)
#
# BỐI CẢNH BẢO MẬT:
# Máy chủ Ollama KHÔNG có cơ chế xác thực.
# TUYỆT ĐỐI KHÔNG ĐẶT BIẾN OLLAMA_HOST tại đây để giữ mặc định 127.0.0.1 (loopback).
# Docker Desktop trên Windows sẽ tự động chuyển tiếp từ container qua host.docker.internal
# vào loopback của máy một cách an toàn mà không làm phơi lộ cổng 11434 ra mạng LAN.
# ==============================================================================

Write-Host "--- Cấu hình biến môi trường Ollama cho người dùng hiện tại (gpu8) ---" -ForegroundColor Cyan

# 1. OLLAMA_KEEP_ALIVE: Thời gian giữ mô hình trong VRAM sau lượt gọi (30 phút)
# Khớp cấu hình local_chung.keep_alive trong config/models.yaml
setx OLLAMA_KEEP_ALIVE "30m"
Write-Host "[x] Đã đặt OLLAMA_KEEP_ALIVE = 30m" -ForegroundColor Green

# 2. OLLAMA_NUM_PARALLEL: Số luồng suy luận đồng thời trên mỗi model (1 luồng cho GPU 8 GB)
setx OLLAMA_NUM_PARALLEL "1"
Write-Host "[x] Đã đặt OLLAMA_NUM_PARALLEL = 1" -ForegroundColor Green

# 3. OLLAMA_MAX_LOADED_MODELS: Số mô hình tối đa nạp vào VRAM/RAM cùng lúc.
# Từ Giai đoạn 6, OLLAMA_MAX_LOADED_MODELS = so_model_nap_cung_luc + 1 (gpu8: 1 chat + 1 nhúng = 2)
setx OLLAMA_MAX_LOADED_MODELS "2"
Write-Host "[x] Đã đặt OLLAMA_MAX_LOADED_MODELS = 2" -ForegroundColor Green

# 4. OLLAMA_FLASH_ATTENTION: Bật Flash Attention giảm tiêu thụ VRAM và tăng tốc sinh token
setx OLLAMA_FLASH_ATTENTION "1"
Write-Host "[x] Đã đặt OLLAMA_FLASH_ATTENTION = 1" -ForegroundColor Green

# 5. OLLAMA_KV_CACHE_TYPE: Lượng tử hóa bộ nhớ đệm KV sang q8_0 để phục vụ cửa sổ ngữ cảnh 16k
setx OLLAMA_KV_CACHE_TYPE "q8_0"
Write-Host "[x] Đã đặt OLLAMA_KV_CACHE_TYPE = q8_0" -ForegroundColor Green

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host "LƯU Ý QUAN TRỌNG ĐỂ BIẾN MÔI TRƯỜNG CÓ HIỆU LỰC:" -ForegroundColor Yellow
Write-Host "1. Chuột phải vào biểu tượng Ollama ở Khay hệ thống (System Tray)." -ForegroundColor White
Write-Host "2. Chọn 'Quit Ollama' (hoặc 'Exit') để dừng hoàn toàn tiến trình cũ." -ForegroundColor White
Write-Host "3. Mở lại ứng dụng Ollama từ Start Menu." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Yellow
