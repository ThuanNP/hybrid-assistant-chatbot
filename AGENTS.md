# Quy định hoạt động của AI Agent (AGENTS.md)

## Dự án

Trợ lý AI NỘI BỘ cho cán bộ, công nhân viên của Doanh nghiệp kinh doanh điện năng;
backend FastAPI (`backend/`), frontend Angular (`frontend/`); chuỗi lai tầng 0 local
(Ollama/LM Studio, bậc 1 "chinh", bậc 2 "nho") rồi Gemini -> OpenRouter/auto -> Claude
-> OpenAI theo chính sách định tuyến.

## Rule bắt buộc - đọc trước mọi việc

| Tệp | Áp dụng khi |
| :--- | :--- |
| `.agents/rules/naming.md` | Đặt tên tệp, thư mục, hàm, biến, lớp, bảng CSDL và tài liệu |
| `.agents/rules/clean_code.md` | Viết mã nguồn, tổ chức hàm, luồng xử lý và viết chú thích |
| `.agents/rules/type_safety.md` | Khai báo kiểu, xử lý giá trị Optional/None và kiểm thử kiểu |
| `.agents/rules/markdown.md` | Tạo hoặc chỉnh sửa bất kỳ tệp tài liệu Markdown nào |
| `.agents/rules/versioning.md` | Đánh số phiên bản, nâng số, gắn thẻ phát hành hoặc sửa đổi API |

Khi AGENTS.md và rule mâu thuẫn, quy tắc tuyệt đối trong AGENTS.md thắng;
muốn đổi rule phải hỏi trước.

## Quy tắc tuyệt đối

1. Mọi lời gọi model trong ứng dụng đi qua ĐÚNG MỘT cửa: `goi_mo_hinh()`,
   `goi_mo_hinh_theo_dong()` (sau này thêm `goi_nhung()`) trong `backend/app/llm/router.py`.
   Phía sau cửa này, httpx tới bộ chạy chỉ nằm trong `backend/app/llm/bo_chay_local.py`,
   litellm chỉ nằm trong `backend/app/llm/nha_cung_cap_dam_may.py`; `router.py` gọi qua
   hai mô-đun đó. Cấm gọi httpx tới bộ chạy hoặc litellm ở mọi nơi khác (Ngoại lệ duy nhất:
   `scripts/kiem_tra_bo_chay.py` và `scripts/kiem_tra_nha_cung_cap.py` được phép gọi thẳng
   bộ chạy và litellm, vì chúng là công cụ chẩn đoán chạy tay, không nằm trong ứng dụng).
2. Dữ liệu nhãn `NHAY_CAM` (mã khách hàng, số điện thoại, số và chỉ số công tơ, số CCCD)
   hoặc thuộc phòng ban cấu hình `chi_local` KHÔNG BAO GIỜ được gửi ra đám mây, kể cả khi
   model local hỏng; hết chuỗi local thì trả lời có kiểm soát, không im lặng.
3. Ollama/LM Studio chỉ nghe ở địa chỉ vòng lặp hoặc mạng nội bộ Docker; mọi truy cập
   đi qua ứng dụng.
4. Không ghi khoá API, mật khẩu, chuỗi kết nối vào mã; không ghi nội dung tin nhắn
   vào nhật ký; kiểm tra rò rỉ bí mật theo kỹ năng `.agents/skills/secrets-gitleaks/`.

## Quy tắc kỹ thuật của dự án

1. Tên model, thứ tự chuỗi, hồ sơ GPU, `num_ctx`, `keep_alive`, giá và ngưỡng chỉ khai báo
   trong `config/*.yaml`.
2. Ghim thẻ model đầy đủ kèm mức lượng tử hoá, ví dụ `qwen3.5:9b-q4_K_M`.
3. Mọi lượt gọi model ghi: nguồn, tầng, bậc, model, token vào/ra, chi phí, độ trễ,
   thời gian nạp, tok/s.
4. Chat phát theo dòng (SSE); POST `/chat` không phát theo dòng chỉ cho tích hợp
   máy với máy.
5. Mọi lời gọi ra ngoài có timeout tường minh và số lần thử lại rõ ràng.
6. `ma_yeu_cau` truyền xuyên suốt, có trong mọi dòng nhật ký và mọi phản hồi lỗi.
7. Mọi phép đếm token dùng `dem_token()`; mọi con số nghiệp vụ do công cụ tính,
    không do model.
8. Trần tự chủ L2: chỉ tra cứu, diễn giải, soạn thảo; không có trường `hop_le`
    hay `duoc_duyet`.

## Phạm vi làm việc

Chỉ sửa đổi các thư mục và tệp sau:

- Thư mục: `.agents/`, `.github/`, `backend/`, `frontend/`, `config/`, `prompts/`, `eval/`,
  `scripts/`, `deploy/`, `docs/`, `data/mau/`.
- Tệp gốc: `AGENTS.md`, `README.md`, `CHANGELOG.md`, `SECURITY.md`, `docker-compose.yml`,
  `.env.example`, `.gitignore`, `.gitattributes`, `.gitleaks.toml`, `.markdownlint.json`,
  `.markdownlint-cli2.jsonc`.

## Phải hỏi trước khi làm

Bắt buộc phải hỏi người dùng và nhận được phê duyệt trước khi thực hiện:

- Thêm thư viện mới.
- Đổi lược đồ cơ sở dữ liệu (CSDL).
- Thêm dịch vụ vào `docker-compose.yml`.
- Xoá bất kỳ tệp nào trong dự án.
- Đổi thứ tự chuỗi định tuyến mô hình.
- Sửa bất kỳ tệp nào trong `.agents/rules/`.

## Không làm ở giai đoạn hiện tại

Các hạng mục sau được tạm hoãn có chủ đích trong giai đoạn hiện tại:

- RAG và cơ sở dữ liệu vector (Giai đoạn 6).
- Gọi công cụ / Function calling (Giai đoạn 7).
- Đăng nhập một lần doanh nghiệp / SSO (Giai đoạn 8).
- Redis và cổng AI riêng (Giai đoạn 9).
- Kubernetes, vLLM, nhiều GPU (Giai đoạn 10).
- Tinh chỉnh mô hình / Fine-tuning (Giai đoạn 11).

Đây là quyết định phân định phạm vi có chủ đích; cập nhật lại vào cuối mỗi giai đoạn.

## Cách làm việc

- Trước khi viết mã: nêu rõ tệp sẽ tạo hoặc sửa và rule nào được áp dụng.
- Kiểm tra tài liệu thiết kế: chỉ kiểm tra bằng lệnh
  `npx -p @google/design.md designmd lint DESIGN.md` khi và chỉ khi tập tin `DESIGN.md`
  có thay đổi (tạo mới hoặc chỉnh sửa).
- Sau mỗi prompt: tự chạy TỰ ĐÁNH GIÁ và trả về bảng kết quả.
- Quy trình phát hành: tuân thủ theo quy định tại `.agents/rules/versioning.md`.
