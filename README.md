# Trợ lý AI Nội bộ (Hybrid Assistant Chatbot)

Hệ thống trợ lý AI nội bộ dành riêng cho cán bộ, công nhân viên của doanh nghiệp
kinh doanh điện năng. Hệ thống sử dụng kiến trúc định tuyến lai thông minh:
ưu tiên chuỗi mô hình cục bộ (Ollama / LM Studio) cho dữ liệu nhạy cảm nội bộ,
và tự động chuyển tiếp tới các nhà cung cấp đám mây (Gemini, OpenRouter, Claude, OpenAI)
khi cần năng lực xử lý chuyên sâu.

## 1. Đối tượng người dùng

- Cán bộ, công nhân viên ngành điện lực cần tra cứu quy trình, quy định nội bộ.
- Kỹ sư, chuyên viên nghiệp vụ phân tích và soạn thảo văn bản kỹ thuật.

## 2. Yêu cầu phần cứng tóm tắt

- **CPU**: Tối thiểu 4 nhân (khuyến nghị 8 nhân trở lên).
- **RAM**: Tối thiểu 16 GB (khuyến nghị 32 GB nếu chạy đồng thời mô hình cục bộ).
- **GPU**: Khuyến nghị GPU chuyên dụng (VRAM từ 8 GB trở lên, ví dụ hồ sơ `gpu8`, `gpu16`).
- **Ổ cứng**: Tối thiểu 50 GB dung lượng trống để lưu trữ container và trọng số mô hình.

## 3. Khởi chạy nhanh bằng Docker

Sao chép tệp biến môi trường mẫu và khởi chạy toàn bộ dịch vụ:

```bash
cp .env.example .env && docker compose up -d --build
```

PowerShell:

```powershell
Copy-Item .env.example .env; docker compose up -d --build
```

Điền giá trị thật cho `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`
và `APP_SECRET` trong `.env` trước khi khởi chạy.

Sau khi khởi chạy thành công:

- **Backend API**: <http://localhost:8000/docs>
- **Frontend Web**: <http://localhost:8080>

## 4. Chuẩn bị môi trường phát triển

Để phát triển mã nguồn backend và chạy kiểm thử trực tiếp trên máy, tạo môi trường ảo
`backend/.venv` rồi cài thư viện. `PYTHONUTF8=1` giúp Python in tiếng Việt không lỗi mã hoá.

Git Bash trên Windows (terminal mặc định cho mọi lệnh tự đánh giá):

```bash
export PYTHONUTF8=1                 # thêm dòng này vào ~/.bashrc để giữ lâu dài
python -m venv backend/.venv
source backend/.venv/Scripts/activate
pip install -r backend/requirements.txt
```

PowerShell trên Windows:

```powershell
$env:PYTHONUTF8 = "1"               # chỉ có hiệu lực trong phiên hiện tại
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")   # giữ lâu dài
python -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Nếu PowerShell chặn `Activate.ps1` vì chính sách thực thi, cho phép kịch bản cục bộ
cho riêng tài khoản hiện tại rồi kích hoạt lại:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Linux hoặc macOS:

```bash
export PYTHONUTF8=1
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

## 5. Kiểm tra trước khi chạy

Trước khi khởi động hệ thống, thực hiện kiểm tra chẩn đoán bộ chạy mô hình cục bộ
và các nhà cung cấp đám mây (lệnh giống nhau trên Git Bash và PowerShell,
sau khi đã kích hoạt môi trường ảo):

```bash
# Kiểm tra bộ chạy mô hình cục bộ (Ollama / LM Studio)
python scripts/kiem_tra_bo_chay.py

# Kiểm tra kết nối tới các nhà cung cấp đám mây qua LiteLLM
python scripts/kiem_tra_nha_cung_cap.py
```
