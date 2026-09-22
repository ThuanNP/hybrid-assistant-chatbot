# Nhật ký thay đổi (Changelog)

Mọi thay đổi đáng chú ý của dự án sẽ được ghi lại trong tệp này.
Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/)
và tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [Chưa phát hành]

### Thêm

- Bộ chạy local `backend/app/llm/bo_chay_local.py`: giao diện `BoChay` cho Ollama và
  LM Studio, hạ cấp bậc chinh sang bậc nho, hâm nóng bậc 1, đọc ngữ cảnh thực tế.
- `backend/app/main.py` tối giản: `/health` trả `phien_ban`, lifespan chạy nền
  hâm nóng bậc 1 và cảnh báo khi ngữ cảnh thực tế nhỏ hơn `num_ctx` cấu hình.
- Kiểm thử cho `LOAI_BO_CHAY` lạ, thông báo thẻ model sai, tệp `.env` được truyền vào
  và điểm nhập FastAPI.
- Hướng dẫn PowerShell trong `README.md` mục "Chuẩn bị môi trường phát triển".

### Thay đổi

- `config.py` kiểm tra `HO_SO_GPU` theo các khoá khai báo trong `config/models.yaml`,
  không còn danh sách ghi cứng; kiểm tra thêm `LOAI_BO_CHAY` (`ollama` hoặc `lmstudio`).
- Thông báo lỗi thẻ model nêu rõ hồ sơ, bậc và thẻ sai, không chứa tên model mẫu.
- Bộ chạy Ollama gọi `/api/chat` (NDJSON) thay cho `/v1/chat/completions`: giao diện tương
  thích OpenAI của Ollama bỏ qua `keep_alive` và `options.num_ctx`, model bị nạp với ngữ cảnh
  mặc định 131072 thay vì 16384. LM Studio vẫn dùng `/v1` (SSE).
- Khoá `suy_luan: false` trong `local_chung` của `config/models.yaml` tắt chế độ suy nghĩ
  của model local để câu trả lời không bị phần suy luận chiếm hết giới hạn token ra.
- `scripts/kiem_tra_bo_chay.py` gọi thử model bậc chinh với đúng `num_ctx` và `keep_alive`.
- Chỉ quá hạn, lỗi kết nối và lỗi 5xx kích hoạt hạ cấp bậc local; lỗi khác nổi lên.
- `cua_so_ngu_canh` bắt buộc cho mọi tầng đám mây (bổ sung cho tầng 2-4) để tính ngân sách
  token theo cửa sổ nhỏ nhất của chuỗi.
- `SO_LUONG_DONG_THOI` để trống thì lấy `num_parallel` của hồ sơ GPU; `DO_DAI_HANG_DOI_TOI_DA`
  mặc định 20; biến để trống trong `.env` coi như chưa khai báo.
- `AGENTS.md` quy tắc tuyệt đối 1 ghi rõ httpx tới bộ chạy chỉ ở `bo_chay_local.py`, litellm chỉ
  ở `nha_cung_cap_dam_may.py`, `router.py` gọi qua hai mô-đun đó.
- Ghim `python-dotenv` trong `backend/requirements.txt` (vốn là phụ thuộc bắt buộc
  của `pydantic-settings`, nay được `config.py` dùng trực tiếp).

### Sửa lỗi

- Bỏ giá trị mặc định chứa bí mật: `APP_SECRET`, `DATABASE_URL` trong `config.py` và
  mật khẩu PostgreSQL trong `docker-compose.yml`.
- `nap_cau_hinh(duong_dan_env=...)` đọc đúng tệp `.env` được truyền vào cho mọi biến.
- `.env.example` ghi đúng giá trị `lmstudio` và đủ năm hồ sơ GPU.

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
