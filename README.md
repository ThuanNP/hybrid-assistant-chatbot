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

Sau khi khởi chạy thành công:

- **Backend API**: <http://localhost:8000/docs>
- **Frontend Web**: <http://localhost:8080>

## 4. Chuẩn bị máy phát triển

Để phát triển mã nguồn backend và chạy kiểm thử trực tiếp trên máy chủ cục bộ:

```bash
export PYTHONUTF8=1
python -m venv backend/.venv
# Kích hoạt môi trường ảo:
# Trên Windows (Git Bash):
source backend/.venv/Scripts/activate
# Trên Linux/macOS:
# source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```
