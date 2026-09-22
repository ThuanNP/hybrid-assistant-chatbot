# Nhật ký thay đổi (Changelog)

Mọi thay đổi đáng chú ý của dự án sẽ được ghi lại trong tệp này.
Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/)
và tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [0.1.0] - 2026-09-22

### Thêm

- Khung dự án Trợ lý AI Nội bộ với FastAPI backend, Docker Compose và hệ thống quy tắc agent.
- Bộ năm tệp quy tắc chuẩn trong `.agents/rules/`: đặt tên, mã sạch, an toàn kiểu, Markdown, phiên bản.
- Hồ sơ GPU máy chủ (5 cấu hình phần cứng) và chuỗi mô hình đám mây 4 tầng trong `config/models.yaml`.
- Mô-đun nạp và xác thực cấu hình hệ thống `backend/app/config.py` kèm 10 bài kiểm thử đơn vị tự động.
- Kịch bản chẩn đoán bộ chạy mô hình cục bộ `scripts/kiem_tra_bo_chay.py` (Ollama và LM Studio).
- Kịch bản chẩn đoán kết nối nhà cung cấp đám mây `scripts/kiem_tra_nha_cung_cap.py` qua LiteLLM.

### Thay đổi

- Cập nhật quy định hoạt động trong `AGENTS.md`, bổ sung ngoại lệ chẩn đoán cho hai kịch bản chạy tay.
- Bổ sung hướng dẫn kiểm tra chẩn đoán hệ thống trước khi khởi động vào `README.md`.
- Tự động điều chỉnh `host.docker.internal` và máy chủ CSDL về localhost khi chạy ngoài container.

### Sửa lỗi

- Khắc phục phân giải DNS cho `host.docker.internal` trên Windows khi có Docker Desktop.
