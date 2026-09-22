## Giai đoạn 1: Khung dự án và luật chơi

Mở Antigravity, tạo thư mục trống tên hybrid-assistant-chatbot, mở làm workspace, chọn Editor View. Trên Windows, đặt terminal mặc định của Antigravity là Git Bash (mọi lệnh tự đánh giá viết cho Git Bash), bật Docker Desktop, chạy Ollama với OLLAMA_MAX_LOADED_MODELS=1 cho GPU 8 GB, và thêm export PYTHONUTF8=1 vào ~/.bashrc để Python in tiếng Việt không lỗi mã hoá.

**Mục tiêu giai đoạn.** Đặt luật chơi cho agent trước dòng mã đầu tiên, dựng bộ xương dự án an toàn ngay từ commit đầu, và gom toàn bộ tên model của cả bậc local lẫn bốn tầng đám mây về đúng một tệp cấu hình có kiểm tra.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Năm tệp rule trong .agents/rules/ và AGENTS.md gọi tới chúng | Gọi model thật, định tuyến, hạ cấp → Giai đoạn 2 |
| Cây thư mục backend/, frontend/, config/, prompts/, eval/, scripts/, deploy/ | Endpoint SSE và lưu hội thoại → Giai đoạn 3 |
| .env.example, .gitignore, Dockerfile, docker-compose ba dịch vụ | Giao diện Angular thật → Giai đoạn 4 |
| config/models.yaml hợp nhất năm hồ sơ GPU và bốn tầng đám mây | Xác thực, hạn mức → Giai đoạn 5 |
| app/config.py kiểm tra thẻ model, num_ctx, chuỗi | RAG, cơ sở dữ liệu vector → Giai đoạn 6 |
| Hai kịch bản kiểm tra bộ chạy local và bốn nhà cung cấp | Kubernetes, vLLM → Giai đoạn 10 |

**Điều kiện hoàn thành**

- Có đủ năm tệp rule trong `.agents/rules/`; AGENTS.md gọi tới cả năm, có quy tắc tuyệt đối, phạm vi,
  phải hỏi trước, không làm; markdownlint 0 lỗi.
- `git ls-files | grep -c '^\.env$'` in 0; commit đầu tiên không chứa bí mật.
- `docker compose config` hợp lệ, đúng ba dịch vụ db, backend, frontend; backend có `extra_hosts` host-gateway.
- `pytest backend/tests/test_config.py` qua; khởi động thất bại rõ ràng khi thẻ model thiếu phiên bản.
- `python scripts/kiem_tra_bo_chay.py` in đúng lệnh kéo model còn thiếu; `python scripts/kiem_tra_nha_cung_cap.py` cho ít nhất tầng 1 và tầng 2 ĐẠT.
- Phát hành phiên bản `0.1.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml (frontend/package.json chỉ có từ PROMPT 14), ghi CHANGELOG.md, gắn thẻ `git tag v0.1.0` và `git tag giai-doan-1` trên cùng commit

### PROMPT 1. Đặt luật chơi: các tệp rule trong .agents/rules/ và AGENTS.md gọi tới chúng

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Viết luật chơi trước dòng mã đầu tiên, tách làm hai lớp:

- Các rule dùng chung (đặt tên, mã sạch, an toàn kiểu, Markdown, phiên bản) nằm trong từng tệp riêng ở
  `.agents/rules/`. Mỗi tệp một chủ đề, có ví dụ ĐÚNG và SAI, dùng lại được cho dự án khác.
- AGENTS.md chỉ chứa những gì riêng của dự án (bối cảnh, quy tắc tuyệt đối, phạm vi, việc chưa làm) và gọi
  tới các rule bằng đường dẫn, không chép lại nội dung.

Agent đọc AGENTS.md ở mọi lượt sau, nên luật viết ở prompt này chi phối mọi prompt còn lại.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: agent sẽ tạo đủ năm tệp rule cùng hai tệp cấu hình
markdownlint, và AGENTS.md không chứa đoạn nào chép lại nội dung rule.

```prompt
Tạo luật chơi cho workspace hybrid-assistant-chatbot. Viết bằng tiếng Việt có dấu. Làm theo đúng hai bước.

BƯỚC 1 - Tạo năm tệp rule trong .agents/rules/. Mỗi tệp một chủ đề, mở đầu bằng tiêu đề cấp 1 và một câu phạm
vi áp dụng; mỗi quy định có ví dụ ĐÚNG và SAI (CẤM) dạng khối mã; mục cuối là "Điều CẤM".
1. .agents/rules/naming.md - quy chuẩn đặt tên:
   - Python: snake_case tiếng Việt không dấu (nhat_ky.py, dung_ngu_canh); lớp PascalCase (KetQuaGoi); hằng
     VIET_HOA. TypeScript: tệp kebab-case (sse.service.ts), lớp PascalCase, biến camelCase.
   - Tệp Markdown kebab-case không dấu; tệp kiểm thử tiền tố test_; bảng CSDL snake_case số ít.
   - Một khái niệm dùng một từ duy nhất (hoi_thoai, không lẫn conversation); cấm ký tự có dấu trong mọi tên.
2. .agents/rules/clean_code.md - hàm làm một việc, tối đa khoảng 40 dòng; không lặp mã; trả sớm thay vì lồng if;
   không nuốt ngoại lệ; không để mã chết hay print gỡ lỗi; chú thích giải thích VÌ SAO, không lặp lại mã làm gì.
3. .agents/rules/type_safety.md - Python có type hint đầy đủ, kiểm bằng pyright; TypeScript strict, cấm any;
   giá trị Optional/None phải thu hẹp kiểu trước khi dùng (trong tests/ dùng assert x is not None; trong app/
   trả sớm hoặc ném HTTPException); không ép kiểu thừa.
4. .agents/rules/markdown.md - mọi tệp .md phải qua markdownlint-cli2 trước khi báo xong; văn xuôi tối đa 100
   ký tự mỗi dòng (bảng, khối mã, tiêu đề miễn trừ); khối mã phải có nhãn ngôn ngữ; cấm tắt rule bằng comment
   rải rác. Tạo kèm hai tệp cấu hình ở gốc:
   - .markdownlint.json: {"default": true, "MD013": {"line_length": 100, "code_blocks": false, "tables": false,
     "headings": false}, "MD024": {"siblings_only": true}, "MD041": false}
   - .markdownlint-cli2.jsonc: quét "**/*.md", loại trừ node_modules, .venv, frontend/dist.
5. .agents/rules/versioning.md - đánh số phiên bản theo SemVer (https://semver.org/):
   - MAJOR.MINOR.PATCH. MAJOR khi phá vỡ tương thích; MINOR khi thêm tính năng tương thích ngược; PATCH khi chỉ
     sửa lỗi, vá bảo mật nhỏ hoặc tối ưu. Tăng một số thì các số bên phải về 0.
   - Hậu tố thử nghiệm -alpha.N, -beta.N, -rc.N; siêu dữ liệu bản dựng +20260922 hoặc +sha.5114f85.
   - Giai đoạn phát triển dùng 0.y.z; phát hành 1.0.0 khi chạy chính thức cho người dùng thật.
   - Một số phiên bản chung cho backend/pyproject.toml và frontend/package.json; /health trả phien_ban.
   - API nghiệp vụ dưới /api/v1/, còn /health, /ready, /docs ở gốc. Thay đổi phá vỡ tương thích API thì mở
     /api/v2/ và giữ /api/v1/ song song ít nhất một giai đoạn.
   - Mỗi lần phát hành: nâng số ở hai tệp, ghi CHANGELOG.md (Thêm / Thay đổi / Sửa lỗi), gắn thẻ vX.Y.Z.
   - CẤM sửa hay gắn lại thẻ đã phát hành.

BƯỚC 2 - Tạo AGENTS.md ở gốc, CHỈ chứa phần riêng của dự án và GỌI TỚI rule, không chép lại nội dung rule:
- "Dự án": trợ lý AI NỘI BỘ cho cán bộ, công nhân viên của Doanh nghiệp kinh doanh điện năng; backend FastAPI
  (backend/), frontend Angular (frontend/); chuỗi lai tầng 0 local (Ollama/LM Studio, bậc 1 "chinh", bậc 2 "nho")
  rồi Gemini -> OpenRouter/auto -> Claude -> OpenAI theo chính sách định tuyến.
- "Rule bắt buộc - đọc trước mọi việc": bảng hai cột Tệp | Áp dụng khi, liệt kê đúng năm tệp ở bước 1. Thêm câu:
  "Khi AGENTS.md và rule mâu thuẫn, quy tắc tuyệt đối trong AGENTS.md thắng; muốn đổi rule phải hỏi trước."
- "Quy tắc tuyệt đối" - đúng bốn quy tắc, là thứ riêng của dự án nên viết đầy đủ ở đây:
  1. Mọi lời gọi model đi qua ĐÚNG MỘT nơi: goi_mo_hinh(), goi_mo_hinh_theo_dong() (sau này thêm goi_nhung())
     trong backend/app/llm/router.py. Cấm gọi httpx tới bộ chạy hoặc litellm ở nơi khác.
  2. Dữ liệu nhãn NHAY_CAM (mã khách hàng, số điện thoại, số và chỉ số công tơ, số CCCD) hoặc thuộc phòng ban cấu
     hình chi_local KHÔNG BAO GIỜ được gửi ra đám mây, kể cả khi model local hỏng; hết chuỗi local thì trả lời có
     kiểm soát, không im lặng.
  3. Ollama/LM Studio chỉ nghe ở địa chỉ vòng lặp hoặc mạng nội bộ Docker; mọi truy cập đi qua ứng dụng.
  4. Không ghi khoá API, mật khẩu, chuỗi kết nối vào mã; không ghi nội dung tin nhắn vào nhật ký.
- "Quy tắc kỹ thuật của dự án" - chỉ những điều rule chung không nói, đánh số tiếp theo đúng thứ tự:
  5. Tên model, thứ tự chuỗi, hồ sơ GPU, num_ctx, keep_alive, giá và ngưỡng chỉ khai báo trong config/*.yaml.
  6. Ghim thẻ model đầy đủ kèm mức lượng tử hoá, ví dụ qwen3.5:9b-q4_K_M.
  7. Mọi lượt gọi model ghi: nguồn, tầng, bậc, model, token vào/ra, chi phí, độ trễ, thời gian nạp, tok/s.
  8. Chat phát theo dòng (SSE); POST /chat không phát theo dòng chỉ cho tích hợp máy với máy.
  9. Mọi lời gọi ra ngoài có timeout tường minh và số lần thử lại rõ ràng.
  10. ma_yeu_cau truyền xuyên suốt, có trong mọi dòng nhật ký và mọi phản hồi lỗi.
  11. Mọi phép đếm token dùng dem_token(); mọi con số nghiệp vụ do công cụ tính, không do model.
  12. Trần tự chủ L2: chỉ tra cứu, diễn giải, soạn thảo; không có trường hop_le hay duoc_duyet.
- "Phạm vi làm việc": chỉ sửa .agents/, backend/, frontend/, config/, prompts/, eval/, scripts/, deploy/, docs/,
  data/mau/ và các tệp gốc AGENTS.md, README.md, CHANGELOG.md, docker-compose.yml, .env.example, .gitignore,
  .gitattributes, .markdownlint.json, .markdownlint-cli2.jsonc.
- "Phải hỏi trước khi làm": thêm thư viện, đổi lược đồ CSDL, thêm dịch vụ docker-compose, xoá tệp, đổi thứ tự chuỗi
  định tuyến, sửa bất kỳ tệp nào trong .agents/rules/.
- "Không làm ở giai đoạn hiện tại": RAG và cơ sở dữ liệu vector (Giai đoạn 6), gọi công cụ (Giai đoạn 7), đăng nhập
  một lần doanh nghiệp (Giai đoạn 8), Redis và cổng AI riêng (Giai đoạn 9), Kubernetes, vLLM, nhiều GPU (Giai đoạn
  10), tinh chỉnh mô hình (Giai đoạn 11). Ghi rõ đây là quyết định phạm vi có chủ đích; cập nhật cuối mỗi giai đoạn.
- "Cách làm việc": trước khi viết mã nêu tệp sẽ tạo hoặc sửa và rule nào áp dụng; sau mỗi prompt chạy TỰ ĐÁNH GIÁ
  và trả bảng; phát hành theo .agents/rules/versioning.md.

Không tạo tệp nào ngoài năm tệp rule, hai tệp cấu hình markdownlint và AGENTS.md.
Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. ls .agents/rules -> kỳ vọng: đúng 5 tệp clean_code.md, markdown.md, naming.md, type_safety.md, versioning.md
2. grep -c "\.agents/rules/" AGENTS.md -> kỳ vọng: ít nhất 5 (mỗi rule được gọi tới)
3. grep -n "semver.org" .agents/rules/versioning.md -> kỳ vọng: có; grep -c "semver" AGENTS.md -> kỳ vọng: 0
4. grep -n "goi_mo_hinh\|NHAY_CAM\|chi_local" AGENTS.md -> kỳ vọng: có đủ ba từ khoá
5. npx --yes markdownlint-cli2 "AGENTS.md" ".agents/rules/*.md" -> kỳ vọng: 0 lỗi
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Năm tệp rule trong `.agents/rules/`. Mỗi tệp có tiêu đề, phạm vi áp dụng, ví dụ ĐÚNG và SAI, và mục "Điều CẤM".
- Hai tệp cấu hình `.markdownlint.json` và `.markdownlint-cli2.jsonc` ở gốc.
- AGENTS.md khoảng 60-80 dòng, có bảng "Rule bắt buộc" gọi đủ năm tệp.
- AGENTS.md không chép lại nội dung rule: không có quy định đặt tên hay SemVer trong đó.
- Bốn quy tắc tuyệt đối (1-4) đứng trước tám quy tắc kỹ thuật riêng của dự án (5-12).
- Bảng tự đánh giá năm dòng đều ĐẠT, trong đó markdownlint báo 0 lỗi.

**Tự đánh giá**

```danhgia
ls .agents/rules                                      # kỳ vọng: 5 tệp rule
grep -c "\.agents/rules/" AGENTS.md                   # kỳ vọng: >= 5
grep -n "semver.org" .agents/rules/versioning.md      # kỳ vọng: có dòng khớp
grep -c "semver" AGENTS.md                            # kỳ vọng: 0 (AGENTS.md chỉ gọi tới rule)
grep -n "goi_mo_hinh\|NHAY_CAM\|chi_local" AGENTS.md  # kỳ vọng: có đủ ba từ khoá
npx --yes markdownlint-cli2 "AGENTS.md" ".agents/rules/*.md"   # kỳ vọng: 0 lỗi
```

```batbuoc
AGENTS.md chỉ GỌI TỚI rule, không chép lại. Chép nội dung rule vào AGENTS.md sẽ tạo ra hai nguồn sự thật: sau vài
lần sửa, hai bản lệch nhau và agent không biết theo bản nào. Muốn đổi quy định đặt tên hay phiên bản thì chỉ sửa
đúng một tệp trong .agents/rules/, và theo AGENTS.md, việc này phải hỏi trước.
```

```meo
Năm tệp rule không phụ thuộc dự án, nên có thể chép nguyên thư mục .agents/rules/ sang dự án khác. Trong
AGENTS.md, quy tắc tuyệt đối 1 và 2 là hai quy tắc dùng tới nhiều nhất về sau. Nhờ quy tắc 1, đổi nhà cung cấp
chỉ là sửa YAML. Quy tắc 2 là căn cứ để trả lời khi bộ phận pháp chế hỏi "dữ liệu khách hàng có ra nước ngoài
không".
```

### PROMPT 2. Khung thư mục, biến môi trường và Docker

**Chế độ:** Editor View · **Đọc Plan:** Không

**Mục tiêu.** Dựng bộ xương dự án và bảo vệ khoá API từ commit đầu tiên. Việc cần kiểm kỹ nhất là container backend gọi được Ollama đang chạy trên máy chủ.

```prompt
Đọc AGENTS.md trước. Tạo khung dự án theo cấu trúc sau. Tệp Python và TypeScript để rỗng, chỉ có docstring hoặc chú thích tiếng Việt và dòng TODO.

backend/app/__init__.py, main.py, config.py
backend/app/llm/__init__.py, router.py, bo_chay_local.py, nha_cung_cap_dam_may.py, chinh_sach.py, dem_token.py, chi_phi.py
backend/app/chat/__init__.py, hoi_thoai.py, ngu_canh.py, su_kien_sse.py
backend/app/hang_doi/__init__.py, dieu_phoi.py
backend/app/core/__init__.py, nhat_ky.py, han_muc.py, bao_mat.py, xac_thuc.py, loi.py, csdl.py
backend/app/giam_sat/__init__.py, suc_khoe.py, chi_so.py
backend/app/eval/__init__.py, runner.py, cham_diem.py
backend/tests/__init__.py, backend/tests/conftest.py
frontend/README.md (một dòng: workspace Angular sẽ tạo ở Giai đoạn 4)
config/models.yaml, prompts/he_thong.md, eval/.gitkeep, deploy/.gitkeep, docs/.gitkeep
scripts/kiem_tra_bo_chay.py, scripts/kiem_tra_nha_cung_cap.py

Viết đầy đủ ngay các tệp sau:

0. backend/pyproject.toml tối giản: [project] name = "hybrid-assistant-chatbot-backend", version = "0.1.0" (nguồn số phiên bản của backend theo .agents/rules/versioning.md); [tool.pytest.ini_options] asyncio_mode = "auto", testpaths = ["tests"]; [tool.pyright] cho thư mục app. Thư viện vẫn ghim trong requirements.txt.

1. backend/requirements.txt - ghim phiên bản cụ thể cho: fastapi, uvicorn[standard], httpx, litellm, sqlalchemy, alembic, psycopg[binary], pydantic-settings, pyyaml, tenacity, tiktoken, passlib[bcrypt], python-jose[cryptography], pytest, pytest-asyncio, respx. Không dòng nào thiếu phiên bản. KHÔNG thêm SDK openai, anthropic, google-generativeai - litellm đã chuẩn hoá bốn nhà cung cấp.

2. .gitignore - dòng ĐẦU TIÊN là .env. Thêm: __pycache__/, *.pyc, .venv/, .pytest_cache/, *.db, .DS_Store, node_modules/, frontend/dist/, frontend/.angular/, ket_qua_eval/.
   Thêm .gitattributes: "* text=auto eol=lf", "*.ps1 text eol=crlf", "*.woff2 binary". Lý do: Git trên Windows đổi xuống dòng thành CRLF, tệp .sh và entrypoint có CRLF sẽ hỏng khi chạy trong container Linux.

3. .env.example - đủ các biến, mỗi biến một dòng chú thích tiếng Việt, giá trị mẫu rõ ràng là giả (ví dụ "dan-khoa-that-vao-day"): MOI_TRUONG, CHE_DO_DINH_TUYEN, LOAI_BO_CHAY, DIA_CHI_BO_CHAY, HO_SO_GPU, GOOGLE_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, APP_SECRET, CORS_ORIGINS, NGAN_SACH_NGAY_USD, SO_LUONG_DONG_THOI, DO_DAI_HANG_DOI_TOI_DA, TIMEOUT_GIAY, GHI_NOI_DUNG, XAC_THUC_GIA.
   Giá trị mẫu: CHE_DO_DINH_TUYEN=local_truoc, LOAI_BO_CHAY=ollama, DIA_CHI_BO_CHAY=http://host.docker.internal:11434/v1, HO_SO_GPU=gpu8 (laptop GPU 8 GB), DATABASE_URL=postgresql+psycopg://<user>:<mat-khau>@db:5432/<ten-db>, XAC_THUC_GIA=true (chỉ dev), MOI_TRUONG=dev.
   Chú thích trong .env.example: địa chỉ host.docker.internal và db là địa chỉ nhìn từ TRONG container; khi chạy kịch bản hoặc pytest trực tiếp trên máy, app/config.py tự đổi thành localhost (PROMPT 3).

4. backend/Dockerfile - hai tầng, python:3.12-slim, tầng chạy dùng người dùng không phải root tên ungdung uid 10001, HEALTHCHECK gọi /health bằng python -c urllib (ảnh slim không có curl). Ngữ cảnh build là GỐC repo: chép backend/ vào /srv/backend, config/ vào /srv/config, prompts/ vào /srv/prompts, WORKDIR /srv/backend - giữ đúng bố cục thư mục như trên máy để app/config.py tìm config/ và prompts/ theo cùng một đường dẫn tương đối.

5. docker-compose.yml - đúng ba dịch vụ:
   - db: postgres:17, ổ đĩa có tên, healthcheck pg_isready, cổng "127.0.0.1:5432:5432" CHỈ ở dev để chạy alembic và pytest từ máy (chú thích: không bao giờ mở 0.0.0.0; nếu máy đã có PostgreSQL chiếm 5432 thì đổi cổng bên trái, ví dụ 127.0.0.1:55432).
   - backend: build với context: . và dockerfile: backend/Dockerfile, cổng 8000:8000, env_file .env, depends_on db điều kiện service_healthy, và:
       extra_hosts:
         - "host.docker.internal:host-gateway"
     kèm chú thích tiếng Việt: đây là cách container trên Docker Engine cho Linux gọi được Ollama chạy trên máy chủ; Docker Desktop cho Windows/macOS đã có sẵn tên này nên dòng này vô hại, giữ để chạy được cả trên máy chủ Linux.
   - frontend: tạm dùng nginx:alpine phục vụ một trang "đang xây dựng", cổng 8080:80. Sẽ thay bằng bản build Angular ở Giai đoạn 4.
   KHÔNG thêm Ollama vào compose - Ollama chạy trên máy chủ để dùng GPU trực tiếp.

6. README.md - mô tả ngắn, đối tượng người dùng, yêu cầu phần cứng tóm tắt, lệnh chạy: cp .env.example .env && docker compose up -d --build.

7. CHANGELOG.md - mục "[0.1.0] - chưa phát hành" rỗng.

8. Môi trường ảo cho backend trên máy: python -m venv backend/.venv, kích hoạt bằng source backend/.venv/Scripts/activate (Git Bash trên Windows; Linux/macOS dùng backend/.venv/bin/activate), rồi pip install -r backend/requirements.txt. Ghi hai lệnh này vào README.md mục "Chuẩn bị máy phát triển" kèm dòng export PYTHONUTF8=1.

Cuối cùng chạy git init, git add, và tạo commit đầu tiên. Trước khi commit, xác nhận .env không nằm trong danh sách tệp được theo dõi.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
0. test -f .env || cp .env.example .env -> kỳ vọng: có tệp .env (docker compose cần env_file)
1. head -1 .gitignore -> kỳ vọng: .env
2. git ls-files | grep -c '^\.env$' -> kỳ vọng: 0
3. docker compose config --services -> kỳ vọng: đúng ba dòng db, backend, frontend
4. grep -n "host-gateway" docker-compose.yml -> kỳ vọng: có một dòng, kèm chú thích ngay trên
5. grep -nE "^(openai|anthropic|google-generativeai)" backend/requirements.txt -> kỳ vọng: không có kết quả
6. grep -cvE "==|^#|^$" backend/requirements.txt -> kỳ vọng: 0 (mọi dòng đều ghim phiên bản)
7. docker compose build backend -> kỳ vọng: build thành công
8. backend/.venv/Scripts/python -c "import fastapi, litellm, psycopg; print('ok')" -> kỳ vọng: ok
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Cây thư mục đúng như liệt kê, không thừa tệp.
- Dòng đầu .gitignore là .env; commit đầu tiên đã tạo và không chứa .env.
- docker-compose đúng ba dịch vụ; backend build từ gốc repo, có extra_hosts host-gateway kèm chú thích; db chỉ mở 127.0.0.1:5432.
- backend/pyproject.toml có version 0.1.0; .gitattributes ép xuống dòng LF; backend/.venv cài đủ thư viện.
- requirements.txt ghim phiên bản mọi dòng, không có SDK riêng của nhà cung cấp.
- Bảng tự đánh giá chín dòng.

**Tự đánh giá**

```danhgia
test -f .env || cp .env.example .env                 # kỳ vọng: có .env
head -1 .gitignore                                   # kỳ vọng: .env
git ls-files | grep -c '^\.env$'                     # kỳ vọng: 0
docker compose config --services                     # kỳ vọng: db, backend, frontend
grep -n "host-gateway" docker-compose.yml            # kỳ vọng: 1 dòng
grep -nE "^(openai|anthropic|google-generativeai)" backend/requirements.txt   # kỳ vọng: rỗng
grep -cvE "==|^#|^$" backend/requirements.txt        # kỳ vọng: 0
docker compose build backend                         # kỳ vọng: thành công
backend/.venv/Scripts/python -c "import fastapi, litellm, psycopg; print('ok')"   # kỳ vọng: ok
```

```batbuoc
Nếu .env xuất hiện trong git status, dừng lại sửa .gitignore ngay. Khoá lọt vào lịch sử Git rất khó gỡ sạch; nếu kho mã từng được đẩy lên nơi công khai thì phải huỷ và tạo lại cả bốn khoá API.
```

```meo
Trên Docker Desktop cho Windows, host.docker.internal có sẵn nên thiếu extra_hosts vẫn chạy. Lỗi chỉ lộ ra khi triển khai lên máy chủ Linux, nên cần có dòng này ngay từ đầu.
```

### PROMPT 3. Danh mục model và chuỗi lai ở một chỗ duy nhất

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Tên model thay đổi rất nhanh ở cả hai phía local và đám mây. Đặt tất cả vào một tệp YAML có kiểm tra kiểu để mỗi quý rà lại chỉ mất năm phút, và để máy 6GB hay 24GB chỉ khác nhau một biến HO_SO_GPU.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: không có tên model nào nằm ngoài config/models.yaml, và hồ sơ GPU được chọn bằng biến môi trường chứ không phải sửa mã.

```prompt
Đọc AGENTS.md, quy tắc 4, 5, 6. Viết config/models.yaml và backend/app/config.py.

1. config/models.yaml, dòng đầu là chú thích "# Rà soát lần cuối: 22/09/2026 - kiểm tra lại mỗi quý". Cấu trúc:

bo_chay:
  loai: ${LOAI_BO_CHAY}          # ollama | lmstudio
  dia_chi: ${DIA_CHI_BO_CHAY}
  timeout_giay: 120
ho_so_gpu:                        # chọn bằng biến HO_SO_GPU
  gpu6:  { chinh: {model: qwen3.5:4b-q4_K_M, num_ctx: 8192},  nho: {model: qwen3.5:2b-q4_K_M, num_ctx: 4096},  num_parallel: 1, so_model_nap_cung_luc: 1 }
  gpu8:  { chinh: {model: qwen3.5:4b-q8_0,   num_ctx: 16384}, nho: {model: qwen3.5:2b-q8_0,   num_ctx: 8192},  num_parallel: 1, so_model_nap_cung_luc: 1 }
  gpu12: { chinh: {model: qwen3.5:9b-q4_K_M, num_ctx: 16384}, nho: {model: qwen3.5:4b-q4_K_M, num_ctx: 8192},  num_parallel: 1, so_model_nap_cung_luc: 2 }
  gpu16: { chinh: {model: qwen3.5:9b-q4_K_M, num_ctx: 32768}, nho: {model: qwen3.5:2b-q8_0,   num_ctx: 8192},  num_parallel: 2, so_model_nap_cung_luc: 2 }
  gpu24: { chinh: {model: qwen3.5:27b-q4_K_M, num_ctx: 16384}, nho: {model: qwen3.5:9b-q4_K_M, num_ctx: 16384}, num_parallel: 1, so_model_nap_cung_luc: 1 }
# so_model_nap_cung_luc phải KHỚP OLLAMA_MAX_LOADED_MODELS. Bằng 1 nghĩa là bậc chinh và bậc nho không cùng nằm trong VRAM.
local_chung: { keep_alive: 30m, nhiet_do: 0.3, nguong_hang_doi_ha_cap: 3 }
chuoi_dam_may:                    # thứ tự này là thứ tự thử
  - {tang: 1, ten: gemini, model: gemini/gemini-3.5-flash-lite, api_key_env: GOOGLE_API_KEY, gia_vao_usd_moi_trieu: 0.30, gia_ra_usd_moi_trieu: 2.50, timeout_giay: 60, cua_so_ngu_canh: 1000000}
  - {tang: 2, ten: openrouter_auto, model: openrouter/auto, api_key_env: OPENROUTER_API_KEY, tham_so_them: {cost_tier: low}, gia_vao_usd_moi_trieu: 0.50, gia_ra_usd_moi_trieu: 3.00, timeout_giay: 90, ghi_chu: "Không tiền định - chỉ làm dự phòng"}
  - {tang: 3, ten: claude, model: anthropic/claude-sonnet-5, api_key_env: ANTHROPIC_API_KEY, gia_vao_usd_moi_trieu: <điền theo bảng giá hiện hành>, gia_ra_usd_moi_trieu: <điền>, timeout_giay: 90}
  - {tang: 4, ten: openai, model: openai/gpt-5.6-terra, api_key_env: OPENAI_API_KEY, gia_vao_usd_moi_trieu: 2.00, gia_ra_usd_moi_trieu: 12.00, timeout_giay: 90}
cai_dat_chung: { so_lan_thu_lai_moi_tang: 2, giay_gian_cach_dau: 0.5, gioi_han_token_ra: 1024, ngu_canh_du_phong_token: 512 }

Viết dạng YAML nhiều dòng dễ đọc (không nhất thiết dạng một dòng như trên). Mỗi hồ sơ GPU có chú thích VRAM ước tính; gpu8 ghi rõ "laptop/máy trạm 8 GB, khoảng 6,5 GB cho bậc chinh, không nạp đồng thời bậc nho".

2. backend/app/config.py dùng pydantic-settings đọc .env ở GỐC repo (Path(__file__).resolve().parents[2] / ".env"; biến môi trường thật được ưu tiên hơn .env), nạp config/models.yaml theo cùng thư mục gốc, thay ${BIEN} bằng giá trị đã gộp từ môi trường và .env (không chỉ os.environ). Khi chạy NGOÀI container (không có tệp /.dockerenv): nếu DIA_CHI_BO_CHAY chứa host.docker.internal mà tên này không phân giải được thì đổi thành localhost; nếu DATABASE_URL trỏ máy "db" thì đổi thành localhost - ghi một dòng nhật ký thông tin. Nhờ vậy kịch bản và pytest chạy thẳng trên Windows mà không phải sửa .env. Tiếp theo xác thực - vi phạm thì TỪ CHỐI khởi động với thông điệp tiếng Việt rõ ràng:
   - mọi thẻ model local phải có dấu hai chấm và phần lượng tử hoá; sai thì báo "thẻ model phải ghi đầy đủ, ví dụ qwen3.5:9b-q4_K_M"
   - num_ctx của bậc nho phải nhỏ hơn hoặc bằng bậc chinh
   - HO_SO_GPU phải là một trong năm khoá đã khai báo; so_model_nap_cung_luc là 1 hoặc 2
   - CHE_DO_DINH_TUYEN phải là chi_local, local_truoc hoặc dam_may_truoc
   - chuoi_dam_may có tang tăng dần, không trùng
   - KHÔNG đặt giá trị mặc định cho bất kỳ khoá API nào
   Phơi ra đối tượng cau_hinh với các thuộc tính: bac_local (danh sách 2 bậc đã chọn theo hồ sơ), so_model_nap_cung_luc, chuoi_dam_may, che_do_dinh_tuyen, cai_dat_chung.
   Tầng đám mây nào thiếu khoá API thì đánh dấu kha_dung=False và ghi nhật ký mức thông tin MỘT lần lúc khởi động.

3. backend/tests/test_config.py: từ chối thẻ thiếu lượng tử hoá; từ chối bậc nho có num_ctx lớn hơn bậc chinh; từ chối HO_SO_GPU lạ; từ chối CHE_DO_DINH_TUYEN lạ; tầng thiếu khoá bị đánh dấu không khả dụng chứ không làm hỏng khởi động; ngoài container thì "db" trong DATABASE_URL đổi thành localhost.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
(chạy trong Git Bash, đã source backend/.venv/Scripts/activate)
1. cd backend && pytest tests/test_config.py -v; cd .. -> kỳ vọng: ít nhất 6 kiểm thử, tất cả qua
2. grep -rnE "qwen|gemini-|claude-|gpt-" backend/app --include=*.py -> kỳ vọng: không có kết quả
3. (cd backend && HO_SO_GPU=gpu99 python -c "import app.config") -> kỳ vọng: thoát lỗi với thông điệp tiếng Việt nêu rõ HO_SO_GPU
4. (cd backend && HO_SO_GPU=gpu8 python -c "from app.config import cau_hinh; print(cau_hinh.bac_local, cau_hinh.so_model_nap_cung_luc)") -> kỳ vọng: in qwen3.5:4b-q8_0, qwen3.5:2b-q8_0 và 1
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- config/models.yaml có năm hồ sơ GPU và bốn tầng đám mây theo đúng thứ tự Gemini → OpenRouter → Claude → OpenAI, mỗi tầng có giá vào và giá ra.
- Dòng ngày rà soát ở đầu tệp YAML.
- app/config.py từ chối khởi động với thông điệp rõ ràng ở cả bốn loại cấu hình sai; chạy được cả trong container lẫn trực tiếp trên Windows.
- Không có tên model nào trong mã Python.
- Kiểm thử test_config.py qua hết.

**Tự đánh giá**

```danhgia
source backend/.venv/Scripts/activate                                  # Git Bash trên Windows
(cd backend && pytest tests/test_config.py -v)                         # kỳ vọng: >= 6 kiểm thử qua
grep -rnE "qwen|gemini-|claude-|gpt-" backend/app --include=*.py       # kỳ vọng: rỗng
(cd backend && HO_SO_GPU=gpu99 python -c "import app.config")          # kỳ vọng: lỗi tiếng Việt về HO_SO_GPU
(cd backend && HO_SO_GPU=gpu8 python -c "from app.config import cau_hinh; print(cau_hinh.bac_local, cau_hinh.so_model_nap_cung_luc)")   # kỳ vọng: 4b-q8_0, 2b-q8_0, 1
```

```batbuoc
Thẻ model và giá của cả bốn nhà cung cấp đổi vài tháng một lần. Đừng để agent đoán rồi tin ngay: chạy kịch bản kiểm tra ở PROMPT 4 và sửa lại theo danh mục chính thức (thư viện Ollama, trang model của từng nhà cung cấp). Ghi ngày rà soát vào đầu tệp YAML.
```

```meo
Chọn HO_SO_GPU nhỏ hơn một bậc so với VRAM thật nếu máy còn chạy màn hình, trình duyệt hoặc IDE trên cùng GPU. Máy 8GB dùng làm máy trạm thường chỉ còn 6-6,5GB cho model.
```

### PROMPT 4. Hai kịch bản kiểm tra: bộ chạy local và bốn nhà cung cấp

**Chế độ:** Editor View · **Đọc Plan:** Không

**Mục tiêu.** Trước khi viết lõi định tuyến, biết chắc máy đã có đủ model local và bốn khoá API gọi được. Hai kịch bản này là thứ người vận hành chạy đầu tiên mỗi khi có sự cố.

```prompt
Đọc AGENTS.md. Viết scripts/kiem_tra_bo_chay.py và scripts/kiem_tra_nha_cung_cap.py. Cả hai đọc cấu hình qua backend/app/config.py (thêm backend/ vào sys.path), không tự đọc YAML riêng, chạy được bằng một lệnh từ gốc workspace với python của backend/.venv. Đầu mỗi kịch bản gọi sys.stdout.reconfigure(encoding="utf-8") để in tiếng Việt trên Git Bash/Windows không lỗi.

1. scripts/kiem_tra_bo_chay.py:
   a) Với LOAI_BO_CHAY=ollama: gọi GET <gốc>/api/tags (gốc = DIA_CHI_BO_CHAY bỏ hậu tố /v1), đối chiếu mọi thẻ model của hồ sơ HO_SO_GPU đang chọn. Thiếu model nào thì in ĐÚNG lệnh cần chạy: ollama pull <thẻ>.
   b) Gọi GET <gốc>/api/ps, in bảng model đang nằm trong bộ nhớ: tên, dung lượng, dung lượng VRAM, còn bao lâu thì bị giải phóng. Nếu so_model_nap_cung_luc = 1 mà /api/ps thấy hơn một model, in cảnh báo OLLAMA_MAX_LOADED_MODELS chưa đặt bằng 1 (GPU 8 GB sẽ tràn VRAM sang RAM và chậm hẳn).
   c) Với LOAI_BO_CHAY=lmstudio: gọi GET <dia_chi>/models, đối chiếu tên model; thiếu thì in lệnh lms get <tên> và nhắc tải trong giao diện LM Studio.
   d) Gọi thử POST <dia_chi>/chat/completions với model bậc chinh, một câu rất ngắn, max_tokens 8, in thời gian tới token đầu tiên. Nếu lớn hơn 5 giây, in dòng giải thích: đây là thời gian nạp model vào VRAM, lần sau sẽ nhanh.
   e) In cảnh báo nếu DIA_CHI_BO_CHAY trỏ tới 0.0.0.0 hoặc một địa chỉ công cộng.
   Mã thoát 1 nếu thiếu model hoặc bộ chạy không phản hồi.

2. scripts/kiem_tra_nha_cung_cap.py: gọi thử TỪNG tầng đám mây bằng litellm với câu "Trả lời đúng một từ: xin chào", in bảng: tầng, tên, model, ĐẠT/HỎNG/BỎ QUA (thiếu khoá), độ trễ ms, token vào, token ra, model thực dùng (với openrouter/auto đọc từ phản hồi). Nếu lỗi 404 hoặc thông điệp chứa "model", in gợi ý: tra danh mục model của nhà cung cấp và sửa config/models.yaml. Nếu lỗi 401, in gợi ý kiểm tra khoá trong .env. Không in khoá ra màn hình dưới bất kỳ hình thức nào.
   Tham số --tang 1|2|3|4|all, mặc định all. Mã thoát 1 nếu cả tầng 1 và tầng 2 đều không ĐẠT.

3. Ghi chú đầu mỗi kịch bản: đây là hai kịch bản DUY NHẤT được phép gọi thẳng bộ chạy và litellm ngoài router.py, vì chúng là công cụ chẩn đoán chạy tay, không nằm trong ứng dụng. Bổ sung ngoại lệ này vào AGENTS.md dưới quy tắc 1.

4. Bổ sung vào README.md mục "Kiểm tra trước khi chạy" với hai lệnh trên.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
(Git Bash, đã source backend/.venv/Scripts/activate; Ollama đang chạy trên Windows)
1. python scripts/kiem_tra_bo_chay.py -> kỳ vọng: bảng model; nếu thiếu thì có dòng "ollama pull ..."; mã thoát đúng với tình trạng
2. HO_SO_GPU=gpu24 python scripts/kiem_tra_bo_chay.py -> kỳ vọng: in lệnh kéo cho model 27b (chỉ in, KHÔNG kéo về - GPU 8 GB không chạy nổi 27b)
3. python scripts/kiem_tra_nha_cung_cap.py -> kỳ vọng: bốn dòng, tầng thiếu khoá ghi BỎ QUA chứ không làm dừng kịch bản
4. GOOGLE_API_KEY=sai python scripts/kiem_tra_nha_cung_cap.py --tang 1 -> kỳ vọng: HỎNG kèm gợi ý kiểm tra khoá, không in khoá
5. grep -rn "import litellm\|httpx" backend/app --include=*.py | grep -v "llm/" -> kỳ vọng: rỗng
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- kiem_tra_bo_chay.py in đúng lệnh kéo model còn thiếu, và bảng model đang nằm trong VRAM.
- kiem_tra_nha_cung_cap.py in bảng bốn tầng, phân biệt ĐẠT / HỎNG / BỎ QUA, có gợi ý sửa khi sai tên model hoặc sai khoá.
- Không kịch bản nào in khoá API ra màn hình.
- AGENTS.md có ghi ngoại lệ cho hai kịch bản chẩn đoán.

**Tự đánh giá**

```danhgia
python scripts/kiem_tra_bo_chay.py                                 # kỳ vọng: bảng model, lệnh ollama pull nếu thiếu
HO_SO_GPU=gpu24 python scripts/kiem_tra_bo_chay.py                 # kỳ vọng: chỉ IN lệnh kéo 27b, không kéo
python scripts/kiem_tra_nha_cung_cap.py                            # kỳ vọng: 4 dòng; ít nhất tầng 1, 2 ĐẠT
GOOGLE_API_KEY=sai python scripts/kiem_tra_nha_cung_cap.py --tang 1   # kỳ vọng: HỎNG + gợi ý, không lộ khoá
```

```meo
Chạy kiem_tra_bo_chay.py hai lần liên tiếp. Lần đầu thời gian tới token đầu tiên thường 10-40 giây (nạp model), lần hai dưới 1 giây. Nếu lần hai vẫn chậm, keep_alive đang không có tác dụng. PROMPT 5 xử lý lỗi này.
```

## Giai đoạn 2: Lõi định tuyến lai

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View. Bảo đảm Ollama (hoặc LM Studio) đang chạy và python scripts/kiem_tra_bo_chay.py đã ĐẠT trước khi bắt đầu.

**Mục tiêu giai đoạn.** Một hàm duy nhất gọi model: thử model local trước, tự hạ cấp khi local quá tải, rơi xuống bốn tầng đám mây khi được phép, và không bao giờ để dữ liệu nhạy cảm ra khỏi máy. Các giai đoạn sau đều xây trên sáu prompt này, nên sai ở đây sẽ kéo theo sai ở mọi chỗ khác.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Bộ chạy local qua giao diện tương thích OpenAI, hạ cấp bậc 1 → bậc 2, hâm nóng | Endpoint HTTP, SSE ra trình duyệt → Giai đoạn 3 |
| Nhà cung cấp đám mây qua litellm, ba loại lỗi xử lý khác nhau | Lưu hội thoại vào cơ sở dữ liệu → Giai đoạn 3 |
| Chính sách định tuyến ba chế độ, nhãn NHAY_CAM | Giao diện → Giai đoạn 4 |
| router.py với goi_mo_hinh và goi_mo_hinh_theo_dong | Hạn mức theo người dùng → Giai đoạn 5 |
| Đếm token, dựng ngữ cảnh cắt theo cặp | Redis, hàng đợi phân tán → Giai đoạn 9 |
| Hàng đợi local, chi phí, ngân sách ngày, tỷ lệ rơi tầng | Nhúng vector → Giai đoạn 6 |

**Điều kiện hoàn thành**

- `grep -rn "def goi_mo_hinh" backend/app | wc -l` in 2 (goi_mo_hinh và goi_mo_hinh_theo_dong, cả hai trong router.py).
- Kiểm thử chi_local khẳng định KHÔNG có lời gọi mạng nào tới nhà cung cấp đám mây, kể cả khi local hỏng.
- `keep_alive` nằm ở cấp cao nhất của thân JSON, có kiểm thử.
- Toàn bộ kiểm thử backend/tests qua mà không cần mạng thật.
- Tắt Ollama (PowerShell: Stop-Process -Name "ollama*" -Force) rồi gọi thử với local_truoc: vẫn có câu trả lời từ tầng 1.
- Phát hành phiên bản `0.2.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml (frontend/package.json chỉ có từ PROMPT 14), ghi CHANGELOG.md, gắn thẻ `git tag v0.2.0` và `git tag giai-doan-2` trên cùng commit

### PROMPT 5. Bộ chạy local và chuỗi hạ cấp

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Gọi model local qua giao diện tương thích OpenAI bằng httpx, tự hạ cấp sang model nhỏ khi bậc chính không đáp ứng, và nạp sẵn model vào VRAM trước người dùng đầu tiên.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: keep_alive nằm ở cấp cao nhất của thân JSON, và lỗi 4xx không kích hoạt hạ cấp.

```prompt
Đọc AGENTS.md, quy tắc tuyệt đối 1 và 3, quy tắc kỹ thuật 5, 6, 9. Viết backend/app/llm/bo_chay_local.py.

1. Lớp giao diện BoChay với hai hiện thực BoChayOllama và BoChayLMStudio, chọn theo LOAI_BO_CHAY. Các phương thức: goi(...), goi_theo_dong(...), liet_ke_model(), model_dang_nap(), doc_ngu_canh_thuc_te(model). Nơi khác chỉ phụ thuộc giao diện, đổi bộ chạy không phải sửa chỗ khác.

2. Gọi POST {dia_chi}/chat/completions bằng httpx.AsyncClient, KHÔNG dùng SDK. Thân JSON:
   {model, messages, stream, temperature, max_tokens, options: {num_ctx: <theo bậc>}, keep_alive: "<theo cấu hình>"}
   LƯU Ý: keep_alive nằm ở CẤP CAO NHẤT, là anh em với options, KHÔNG nằm trong options. Đặt sai chỗ thì bị bỏ qua âm thầm. Với LM Studio bỏ options và keep_alive (LM Studio quản lý ngữ cảnh khi nạp model).
   Header Authorization gửi chuỗi bất kỳ, ví dụ "Bearer local" - bộ chạy yêu cầu có nhưng bỏ qua giá trị.

3. Hàm async def goi_local(tin_nhan, *, ma_yeu_cau, do_dai_hang_doi=0, phat_theo_dong=False) thử theo thứ tự bậc 1 (chinh) rồi bậc 2 (nho):
   - Hạ xuống bậc 2 khi: quá hạn timeout, bộ chạy trả 5xx, lỗi kết nối, HOẶC do_dai_hang_doi > nguong_hang_doi_ha_cap (khi đó bỏ qua bậc 1 ngay).
   - NGOẠI LỆ khi so_model_nap_cung_luc = 1 (gpu6, gpu8, gpu24): KHÔNG hạ cấp chỉ vì hàng đợi dài. Đổi model trong VRAM tốn 5–20 giây và đẩy bậc chinh ra ngoài, chậm hơn cả việc chờ. Chỉ hạ cấp khi bậc 1 lỗi hoặc quá hạn.
   - KHÔNG hạ cấp khi 4xx do yêu cầu sai: ném LoiDauVao lên, đó là lỗi của mã cần sửa.
   - Hết cả hai bậc: ném LoiHetBacLocal kèm lý do từng bậc (router sẽ quyết định rơi ra đám mây hay trả câu có kiểm soát).

4. Đo và trả về: thoi_gian_nap_ms (thời gian tới token đầu tiên), do_tre_ms, toc_do_tok_s, token_vao, token_ra (đọc usage; bộ chạy không trả thì ước lượng bằng dem_token ở PROMPT 9 - tạm để TODO). Ba số thoi_gian_nap_ms, toc_do_tok_s, do_dai_hang_doi là chỉ số sức khoẻ chính của bản local.

5. Phát theo dòng: bóc từng dòng "data: " của SSE tương thích OpenAI, xử lý dòng "data: [DONE]", bỏ qua dòng rỗng và dòng chú thích.

6. async def ham_nong(): gọi bậc 1 với tin nhắn "xin chào", max_tokens 1, để model được nạp sẵn. CHỈ hâm nóng bậc 1; không bao giờ hâm nóng bậc 2 khi so_model_nap_cung_luc = 1. Gọi trong sự kiện lifespan của FastAPI nhưng KHÔNG chặn khởi động nếu thất bại (chạy nền, ghi nhật ký cảnh báo).

7. async def doc_ngu_canh_thuc_te(model): với Ollama gọi POST <gốc>/api/show và GET <gốc>/api/ps để đọc cửa sổ ngữ cảnh bộ chạy đang thực sự dùng; lệch so với num_ctx cấu hình thì ghi cảnh báo lúc khởi động. Lý do: Ollama tự hạ ngữ cảnh khi VRAM căng.

8. backend/tests/test_bo_chay_local.py dùng httpx.MockTransport hoặc respx, không gọi mạng thật:
   - hạ cấp khi bậc 1 quá hạn
   - hạ cấp khi bậc 1 trả 503
   - KHÔNG hạ cấp khi trả 400, ném LoiDauVao
   - bỏ qua bậc 1 khi hàng đợi dài hơn ngưỡng và so_model_nap_cung_luc = 2
   - KHÔNG bỏ qua bậc 1 vì hàng đợi khi so_model_nap_cung_luc = 1
   - keep_alive nằm ở cấp cao nhất của thân JSON, không nằm trong options
   - hết hai bậc thì ném LoiHetBacLocal có đủ hai lý do
   - bóc SSE đúng, dừng ở [DONE]

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_bo_chay_local.py -v -> kỳ vọng: 8 kiểm thử qua, không cần mạng
2. grep -rnE "import (openai|anthropic|google)" backend/app -> kỳ vọng: rỗng
3. grep -n "keep_alive" backend/app/llm/bo_chay_local.py -> kỳ vọng: keep_alive được gán ở cùng cấp với "options", không nằm trong dict options
4. (cd backend && python -c "import asyncio; from app.llm.bo_chay_local import ham_nong; asyncio.run(ham_nong())") với Ollama đang chạy trên Windows, rồi ollama ps -> kỳ vọng: chỉ model bậc 1 xuất hiện, UNTIL khoảng 30 phút
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Giao diện BoChay với hai hiện thực Ollama và LM Studio.
- keep_alive ở cấp cao nhất của thân JSON, có kiểm thử khẳng định.
- Hạ cấp khi quá hạn, 5xx, hàng đợi dài; không hạ cấp khi 4xx.
- ham_nong chạy nền lúc khởi động, thất bại không làm hỏng khởi động.
- Tám kiểm thử qua mà không cần mạng; với gpu8 không bao giờ nạp hai model cùng lúc.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_bo_chay_local.py -v          # kỳ vọng: 8 passed
grep -rnE "import (openai|anthropic|google)" backend/app     # kỳ vọng: rỗng
grep -n "keep_alive" backend/app/llm/bo_chay_local.py        # kỳ vọng: cùng cấp với options
(cd backend && python -c "import asyncio; from app.llm.bo_chay_local import ham_nong; asyncio.run(ham_nong())")
ollama ps                                                    # kỳ vọng: chỉ model bậc 1 đã nạp sau ham_nong
```

```batbuoc
Đặt keep_alive vào trong options là lỗi rất hay gặp vì trông nó giống num_ctx. Hậu quả: tham số bị bỏ qua, model dùng mặc định năm phút, và một hệ thống ít người dùng khởi động nguội liên tục mà không ai hiểu vì sao.
```

```meo
Hàm hâm nóng trông như thừa. Không có nó, người dùng đầu tiên mỗi buổi sáng phải chờ khoảng ba mươi giây để model nạp.
```

### PROMPT 6. Nhà cung cấp đám mây và ba loại lỗi

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Bốn tầng đám mây gọi qua litellm, thử lại đúng chỗ, rơi tầng đúng chỗ, và không bao giờ thử lại ba lần với một khoá API sai.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: ba loại lỗi (tạm thời, vĩnh viễn, đầu vào) có ba nhánh xử lý khác nhau, không bị gộp chung một khối except.

```prompt
Đọc AGENTS.md, quy tắc tuyệt đối 1 và 4. Viết backend/app/llm/nha_cung_cap_dam_may.py.

1. Hàm async def goi_dam_may(tang, tin_nhan, *, ma_yeu_cau, phat_theo_dong=False, **tuy_chon) gọi MỘT tầng qua litellm.acompletion. Đọc model, api_key_env, timeout_giay, tham_so_them từ cấu hình của tầng. Khoá API đọc từ biến môi trường theo tên api_key_env; không bao giờ ghi khoá vào nhật ký.

2. Phân loại lỗi thành ba lớp ngoại lệ riêng:
   - LoiTamThoi: 429, 500, 502, 503, 504, quá hạn, lỗi mạng -> thử lại tối đa so_lan_thu_lai_moi_tang lần, giãn cách tăng dần từ giay_gian_cach_dau, nhân đôi mỗi lần, có nhiễu ngẫu nhiên; hết lượt thì báo router rơi tầng.
   - LoiVinhVien: 401 sai khoá, 403 không có quyền, 404 sai tên model -> KHÔNG thử lại, ghi nhật ký mức cảnh báo, báo router rơi tầng ngay.
   - LoiDauVao: 400 lời nhắc quá dài, nội dung bị chặn bởi bộ lọc của nhà cung cấp -> KHÔNG rơi tầng, ném lên trên vì mọi tầng đều sẽ lỗi như nhau.

3. Với tầng openrouter_auto: đọc tên model thực sự đã dùng trong phản hồi, trả về trong trường ten_model, và đánh dấu chi_phi_la_uoc_tinh_tho=True.

4. Phát theo dòng: dùng stream=True của litellm, trả về AsyncIterator các mẩu văn bản; mẩu cuối mang usage. Nếu nhà cung cấp không trả usage khi stream, ước lượng bằng dem_token (TODO nối ở PROMPT 9).

5. Trả về cùng kiểu kết quả thô với bo_chay_local (noi_dung, ten_model, token_vao, token_ra, do_tre_ms, so_lan_thu) để router ghép thành KetQuaGoi.

6. backend/tests/test_nha_cung_cap_dam_may.py dùng giả lập litellm (monkeypatch), không gọi mạng thật:
   - 429 hai lần rồi thành công -> so_lan_thu = 3
   - 429 liên tục -> ném tín hiệu rơi tầng sau đúng N lần thử
   - 401 -> không thử lại, rơi tầng ngay (đếm số lần gọi = 1)
   - 400 -> ném LoiDauVao, không rơi tầng
   - openrouter/auto ghi model thực dùng
   - khoá API không xuất hiện trong bất kỳ bản ghi nhật ký nào (dùng caplog)

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_nha_cung_cap_dam_may.py -v -> kỳ vọng: 6 kiểm thử qua, không cần mạng
2. grep -n "class Loi" backend/app/llm/nha_cung_cap_dam_may.py -> kỳ vọng: ba lớp LoiTamThoi, LoiVinhVien, LoiDauVao
3. grep -rn "litellm" backend/app --include=*.py | grep -v "nha_cung_cap_dam_may.py" -> kỳ vọng: rỗng
4. python scripts/kiem_tra_nha_cung_cap.py --tang 1 -> kỳ vọng: vẫn ĐẠT (không phá kịch bản chẩn đoán)
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Ba lớp lỗi riêng, ba nhánh xử lý khác nhau; đọc mã xác nhận, không tin mô tả.
- Thử lại có giãn cách tăng dần và nhiễu ngẫu nhiên, lấy tham số từ cai_dat_chung.
- Model thực dùng của openrouter/auto được ghi lại.
- litellm chỉ xuất hiện trong đúng một tệp.
- Sáu kiểm thử qua mà không cần mạng.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_nha_cung_cap_dam_may.py -v             # kỳ vọng: 6 passed
grep -n "class Loi" backend/app/llm/nha_cung_cap_dam_may.py            # kỳ vọng: 3 lớp
grep -rn "litellm" backend/app --include=*.py | grep -v nha_cung_cap_dam_may.py   # kỳ vọng: rỗng
python scripts/kiem_tra_nha_cung_cap.py --tang 1                       # kỳ vọng: ĐẠT
```

```batbuoc
Phải phân biệt lỗi tạm thời với lỗi vĩnh viễn. Chi tiết này hay bị bỏ qua và gây tốn kém: thử lại ba lần với một khoá API sai chỉ làm mọi yêu cầu chậm thêm vài giây mà không bao giờ thành công.
```

### PROMPT 7. Chính sách định tuyến và nhãn dữ liệu nhạy cảm

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Biến quy tắc tuyệt đối số 2 thành mã có kiểm thử: quyết định mỗi yêu cầu được đi qua những tầng nào, và bảo đảm dữ liệu khách hàng không bao giờ rời hạ tầng của doanh nghiệp.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: nhãn NHAY_CAM thắng mọi cấu hình khác, kể cả khi CHE_DO_DINH_TUYEN=dam_may_truoc.

```prompt
Đọc AGENTS.md, quy tắc tuyệt đối 2. Viết backend/app/llm/chinh_sach.py và config/chinh_sach_du_lieu.yaml.

1. Hai enum:
   - CheDoDinhTuyen: chi_local | local_truoc | dam_may_truoc
   - NhanDuLieu: THUONG | NHAY_CAM

2. Hàm def phat_hien_nhay_cam(van_ban) -> bool, dùng biểu thức chính quy khai báo trong config/chinh_sach_du_lieu.yaml:
   - mã khách hàng dạng KH + 8 chữ số (ví dụ KH00012345)
   - số điện thoại Việt Nam 10 chữ số bắt đầu bằng 0, có hoặc không có dấu cách, dấu chấm
   - số CCCD 12 chữ số
   - cụm "chỉ số công tơ" kèm một con số
   - email
   Ghi chú rõ: đây là bộ phát hiện tối giản, đặt nghiêng về an toàn - nhận nhầm thành nhạy cảm chỉ làm câu hỏi đi local, không gây rò rỉ.

3. config/chinh_sach_du_lieu.yaml khai báo thêm:
   phong_ban_chi_local: [CHAM_SOC_KHACH_HANG, KINH_DOANH]
   phong_ban_mac_dinh: CNTT
   Phòng ban mẫu: KINH_DOANH, KY_THUAT, AN_TOAN, CHAM_SOC_KHACH_HANG, CNTT.

4. Hàm def xac_dinh_chuoi(nguoi, nhan_du_lieu, che_do) -> list[Tang]:
   - nhan_du_lieu = NHAY_CAM, hoặc nguoi.phong_ban thuộc phong_ban_chi_local, hoặc che_do = chi_local -> chỉ [tầng 0]
   - local_truoc -> [0, 1, 2, 3, 4]
   - dam_may_truoc -> [1, 2, 3, 4, 0]
   - bỏ các tầng đám mây kha_dung=False (thiếu khoá)
   - trả kèm lý do đã chọn chuỗi (ly_do_chuoi) để ghi nhật ký kiểm toán
   Tang là dataclass: so (0..4), nguon ("local"|"dam_may"), ten, cua_so_ngu_canh.

5. Nhãn áp theo HỘI THOẠI chứ không chỉ theo tin nhắn: một khi hội thoại đã có tin nhắn NHAY_CAM thì mọi lượt sau của hội thoại đó cũng chi_local (vì ngữ cảnh gửi đi chứa tin nhắn cũ). Viết hàm def nhan_cua_hoi_thoai(lich_su, tin_nhan_moi) -> NhanDuLieu.

6. backend/tests/test_chinh_sach.py:
   - tin nhắn chứa KH00012345 -> chuỗi chỉ có tầng 0
   - dam_may_truoc + NHAY_CAM -> vẫn chỉ tầng 0
   - phòng ban CHAM_SOC_KHACH_HANG -> chỉ tầng 0
   - lượt thứ ba của hội thoại mà lượt đầu có số điện thoại -> chỉ tầng 0
   - thiếu ANTHROPIC_API_KEY -> tầng 3 không có trong chuỗi
   - local_truoc, câu hỏi thường -> đúng thứ tự 0,1,2,3,4

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_chinh_sach.py -v -> kỳ vọng: 6 kiểm thử qua
2. python -c "from app.llm.chinh_sach import phat_hien_nhay_cam as f; print(f('Khách KH00012345 gọi 0900 000 001'), f('Cách tính tiền điện bậc thang'))" -> kỳ vọng: True False
3. grep -n "phong_ban_chi_local" config/chinh_sach_du_lieu.yaml -> kỳ vọng: có dòng khai báo
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Hai enum CheDoDinhTuyen và NhanDuLieu; hàm xac_dinh_chuoi trả chuỗi kèm ly_do_chuoi.
- Nhãn NHAY_CAM thắng mọi chế độ; nhãn áp theo cả hội thoại.
- Biểu thức phát hiện nằm trong YAML, không ghi cứng trong mã.
- Sáu kiểm thử qua.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_chinh_sach.py -v       # kỳ vọng: 6 passed
python -c "from app.llm.chinh_sach import phat_hien_nhay_cam as f; print(f('Khách KH00012345 gọi 0900 000 001'), f('Cách tính tiền điện bậc thang'))"   # kỳ vọng: True False
grep -n "phong_ban_chi_local" config/chinh_sach_du_lieu.yaml   # kỳ vọng: có
```

```batbuoc
Nhãn phải áp theo hội thoại. Nếu chỉ xét tin nhắn mới, lượt hỏi "thế còn tháng trước?" sẽ không chứa mã khách hàng và được gửi ra đám mây, kèm theo toàn bộ lịch sử có mã khách hàng ở lượt trước.
```

### PROMPT 8. Router hợp nhất: một cửa duy nhất gọi model

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Ghép bộ chạy local, nhà cung cấp đám mây và chính sách thành đúng một hàm công khai, luôn nói rõ tầng nào đã phục vụ, và xử lý đúng hai tình huống lỗi khi đang phát theo dòng.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: có đúng hai hàm công khai, và lỗi giữa chừng khi phát theo dòng KHÔNG dẫn tới rơi tầng rồi phát lại từ đầu.

```prompt
Đọc AGENTS.md, quy tắc tuyệt đối 1 và 2, quy tắc kỹ thuật 7. Viết backend/app/llm/router.py.

1. Phơi ra ĐÚNG HAI hàm công khai:
   async def goi_mo_hinh(tin_nhan: list[dict], *, nguoi: NguoiDung, ma_yeu_cau: str, nhan_du_lieu: NhanDuLieu = NhanDuLieu.THUONG, phat_theo_dong: bool = False, **tuy_chon) -> KetQuaGoi
   async def goi_mo_hinh_theo_dong(tin_nhan, *, nguoi, ma_yeu_cau, nhan_du_lieu, do_dai_hang_doi=0, **tuy_chon) -> AsyncIterator[ManhPhatRa]
   NguoiDung tạm là dataclass (id, ten_dang_nhap, vai_tro, bac, phong_ban, pham_vi_doc, che_do_dinh_tuyen) đặt trong app/core/xac_thuc.py.

2. KetQuaGoi: noi_dung, nguon, tang, bac_local, ten_model, token_vao, token_ra, chi_phi_usd, do_tre_ms, thoi_gian_nap_ms, toc_do_tok_s, so_lan_thu, danh_sach_tang_da_hong, da_cat_ngu_canh, so_luot_bi_cat, ly_do_chuoi.
   ManhPhatRa: loai ("manh" | "xong" | "loi"), noi_dung, ket_qua (KetQuaGoi, chỉ có ở mảnh xong).

3. Luồng:
   a) chuoi = xac_dinh_chuoi(nguoi, nhan_du_lieu, nguoi.che_do_dinh_tuyen hoặc CHE_DO_DINH_TUYEN)
   b) thử lần lượt: tầng 0 gọi goi_local (tự hạ cấp bên trong), tầng 1..4 gọi goi_dam_may
   c) LoiHetBacLocal, tín hiệu rơi tầng của đám mây -> ghi vào danh_sach_tang_da_hong, sang tầng sau
   d) LoiDauVao -> ném lên ngay, không rơi tầng
   e) hết chuỗi: nếu chuỗi chỉ có tầng 0 thì trả câu có kiểm soát lấy từ prompts/he_thong.md mục "tra_loi_khi_ban" (đại ý: hệ thống đang bận, Anh/Chị vui lòng thử lại sau ít phút) với nguon="local", tang=0, ten_model="khong_co"; nếu chuỗi có đám mây thì ném LoiHetChuoiDuPhong chứa lý do từng tầng.

4. Phát theo dòng - xử lý đúng hai tình huống khó:
   - Tầng hiện tại lỗi TRƯỚC mảnh đầu tiên: rơi xuống tầng sau bình thường, người dùng không thấy gì bất thường.
   - Tầng hiện tại lỗi GIỮA CHỪNG sau khi đã phát vài mảnh: KHÔNG rơi tầng và phát lại từ đầu (người dùng sẽ thấy câu trả lời bị viết lại). Kết thúc luồng bằng mảnh "loi" kèm phần văn bản đã nhận. Ghi nhật ký rõ tình huống này.
   - Mảnh "xong" luôn mang đủ KetQuaGoi.

5. Tuyệt đối không gọi httpx tới bộ chạy hay litellm trong router.py - chỉ gọi qua bo_chay_local và nha_cung_cap_dam_may.

5b. Thêm khối if __name__ == "__main__" nhận --thu "<câu hỏi>" và --che-do, gọi goi_mo_hinh với một NguoiDung giả (phong_ban CNTT) rồi in nguon, tang, ten_model, do_tre_ms. Đây là công cụ chạy tay, không phải hàm công khai.

6. backend/tests/test_router.py dùng giả lập:
   - tầng 0 thành công thì không chạm tầng 1
   - tầng 0 hỏng, local_truoc -> tang = 1, danh_sach_tang_da_hong có tầng 0
   - NHAY_CAM, tầng 0 hỏng -> trả câu có kiểm soát; bộ giả lập đám mây ghi nhận 0 lần gọi
   - tầng 1 trả 401 -> rơi tầng 2 ngay
   - LoiDauVao ở tầng 1 -> ném lên, tầng 2 không được gọi
   - stream: lỗi trước mảnh đầu -> rơi tầng, người dùng nhận đủ câu từ tầng sau
   - stream: lỗi sau 2 mảnh -> mảnh cuối là "loi", có phần đã nhận, tầng sau không được gọi
   - hết chuỗi đám mây -> LoiHetChuoiDuPhong có đủ lý do từng tầng

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_router.py -v -> kỳ vọng: 8 kiểm thử qua
2. grep -rn "^async def goi_mo_hinh\|^def goi_mo_hinh" backend/app | wc -l -> kỳ vọng: 2
3. grep -n "httpx\|litellm" backend/app/llm/router.py -> kỳ vọng: rỗng
4. Tắt Ollama (PowerShell: Stop-Process -Name "ollama*" -Force), rồi (cd backend && python -m app.llm.router --thu "Cách tính tiền điện bậc thang" --che-do local_truoc) -> kỳ vọng: tang = 1 (Gemini) phục vụ; bật lại Ollama sau khi thử
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Đúng hai hàm công khai; mọi nơi khác trong mã chỉ gọi hai hàm này.
- Kiểm thử NHAY_CAM khẳng định 0 lời gọi tới đám mây khi local hỏng.
- Hai tình huống lỗi khi phát theo dòng được xử lý khác nhau.
- router.py không import httpx hay litellm.
- Tám kiểm thử qua.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_router.py -v                                   # kỳ vọng: 8 passed
grep -rn "^async def goi_mo_hinh\|^def goi_mo_hinh" backend/app | wc -l         # kỳ vọng: 2
grep -n "httpx\|litellm" backend/app/llm/router.py                             # kỳ vọng: rỗng
# PowerShell: Stop-Process -Name "ollama*" -Force   (tắt Ollama)
(cd backend && python -m app.llm.router --thu "Cách tính tiền điện bậc thang" --che-do local_truoc)   # kỳ vọng: tang = 1
```

```batbuoc
Kiểm thử "NHAY_CAM, local hỏng, đám mây không bị gọi" là thứ bảo vệ quy tắc tuyệt đối số 2 bằng mã. Không được đánh dấu bỏ qua (skip) nó vì bất cứ lý do gì.
```

```meo
Ghi ly_do_chuoi vào mọi bản ghi. Sáu tháng sau, khi có người hỏi "vì sao câu này lại do Claude trả lời", câu trả lời nằm sẵn trong nhật ký.
```

### PROMPT 9. Đếm token và quản lý cửa sổ ngữ cảnh

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Không để hội thoại tràn cửa sổ ngữ cảnh mà không ai biết. Model local có cửa sổ nhỏ nên chuyện này hay xảy ra. Với chuỗi lai, ngân sách token phải tính theo tầng có cửa sổ nhỏ nhất, vì không biết trước tầng nào sẽ phục vụ.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: việc cắt ngữ cảnh có quy tắc rõ và có báo cho người dùng, hay chỉ cắt bừa phần đầu.

```prompt
Đọc AGENTS.md, quy tắc kỹ thuật 11. Viết backend/app/llm/dem_token.py và backend/app/chat/ngu_canh.py, rồi nối dem_token vào các TODO ở PROMPT 5 và 6.

1. dem_token.py: def dem_token(van_ban: str) -> int dùng tiktoken, bộ mã hoá cl100k_base. Ghi chú rõ đây là ƯỚC LƯỢNG vì model local và từng nhà cung cấp dùng bộ tách từ khác; tiếng Việt tốn 1–3 token mỗi chữ. Hằng số HE_SO_AN_TOAN = 1.15 áp khi tính ngân sách.

2. ngu_canh.py: def dung_ngu_canh(lich_su, tin_nhan_moi, chuoi: list[Tang]) -> KetQuaNguCanh(danh_sach, da_cat, so_luot_bi_cat).
   Ngân sách token = min(cửa sổ của mọi tầng trong chuoi) - gioi_han_token_ra - ngu_canh_du_phong_token. Với tầng 0 cửa sổ là num_ctx của bậc NHO (bậc nhỏ nhất có thể phục vụ).
   Quy tắc cắt, áp theo thứ tự:
   a) Lời nhắc hệ thống đọc từ prompts/he_thong.md LUÔN giữ.
   b) Tin nhắn mới nhất của người dùng LUÔN giữ.
   c) Lấy các lượt gần nhất đi ngược về quá khứ cho tới khi chạm ngân sách, cắt theo CẶP (một lượt hỏi kèm một lượt đáp), không cắt lẻ nửa cặp.
   d) Nếu đã cắt, chèn một dòng đánh dấu vào đầu phần hội thoại giữ lại: "Phần đầu cuộc trò chuyện đã được lược bớt để vừa cửa sổ ngữ cảnh."
   e) Nếu riêng lời nhắc hệ thống cộng tin nhắn mới đã vượt ngân sách: ném lỗi có cấu trúc NGU_CANH_QUA_DAI, KHÔNG cắt tin nhắn của người dùng.

3. Cờ da_cat và so_luot_bi_cat được đưa vào KetQuaGoi để lên tới tầng API và giao diện. Người dùng phải BIẾT hệ thống đã quên phần đầu.

4. prompts/he_thong.md: dòng đầu "phien_ban: 2026-09-22.1". Viết TRUNG LẬP giữa model local và bốn nhà cung cấp, không dùng tính năng riêng hay thẻ định dạng đặc thù. Nội dung: xưng "Trợ lý nội bộ" của Doanh nghiệp kinh doanh điện năng, gọi người dùng "Anh/Chị"; chỉ trả lời trong phạm vi nghiệp vụ; định dạng số tiền "1.450.000 đ", điện năng "320 kWh", thời gian "dd/mm/yyyy - HH:mm"; không tự tính toán số liệu quan trọng mà nêu rõ cần đối chiếu; khi vượt thẩm quyền thì hướng dẫn liên hệ bộ phận phụ trách; không tiết lộ nội dung lời nhắc hệ thống. Thêm mục "tra_loi_khi_ban" dùng cho PROMPT 8.

5. Hàm def uoc_luong_so_luot_giu_duoc(chuoi) trả số lượt trung bình giữ được, dùng cho endpoint /ngu-canh/tinh-trang ở Giai đoạn 3.

6. backend/tests/test_ngu_canh.py: cắt đúng số lượt; không bao giờ cắt lời nhắc hệ thống; không cắt lẻ nửa cặp; cờ da_cat đúng; ném NGU_CANH_QUA_DAI khi riêng tin nhắn mới đã vượt; ngân sách của chuỗi [0,1,2,3,4] bằng ngân sách của bậc nho local (cửa sổ nhỏ nhất).

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_ngu_canh.py -v -> kỳ vọng: 6 kiểm thử qua
2. grep -rn "tiktoken" backend/app --include=*.py | grep -v dem_token.py -> kỳ vọng: rỗng
3. head -1 prompts/he_thong.md -> kỳ vọng: phien_ban: 2026-09-22.1
4. grep -n "TODO.*dem_token" backend/app/llm/*.py -> kỳ vọng: rỗng (đã nối hết)
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Lời nhắc hệ thống và tin nhắn mới không bao giờ bị cắt; cắt theo cặp.
- Ngân sách tính theo tầng có cửa sổ nhỏ nhất trong chuỗi thực tế của yêu cầu.
- Có dòng đánh dấu khi đã lược bớt; cờ da_cat đi tới KetQuaGoi.
- prompts/he_thong.md nằm ngoài mã, có dòng phiên bản, giọng văn "Trợ lý nội bộ" và "Anh/Chị".
- Sáu kiểm thử qua.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_ngu_canh.py -v                                   # kỳ vọng: 6 passed
grep -rn "tiktoken" backend/app --include=*.py | grep -v dem_token.py            # kỳ vọng: rỗng
head -1 prompts/he_thong.md                                                      # kỳ vọng: phien_ban: 2026-09-22.1
grep -n "TODO.*dem_token" backend/app/llm/*.py                                   # kỳ vọng: rỗng
```

```meo
Đưa lời nhắc hệ thống ra tệp riêng kèm số phiên bản tốn ít công. Sáu tháng sau, khi chất lượng câu trả lời đổi, bạn biết được phiên bản lời nhắc nào sinh ra câu trả lời nào.
```

### PROMPT 10. Hàng đợi local, chi phí, ngân sách và tỷ lệ rơi tầng

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Người dùng thứ hai thấy mình đang chờ ở vị trí nào thay vì nhìn màn hình trắng. Mỗi câu trả lời có chi phí đo được, và hoá đơn đám mây không tăng mà không ai biết vì sao.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: kiểm tra ngân sách xảy ra TRƯỚC lời gọi đám mây, và hàng đợi chỉ bao quanh tầng local.

```prompt
Đọc AGENTS.md. Viết backend/app/hang_doi/dieu_phoi.py và backend/app/llm/chi_phi.py, rồi nối vào router.py.

Phần 1 - hàng đợi (chỉ cho tầng 0):
1. class DieuPhoi: một asyncio.Semaphore giới hạn số lời gọi local đồng thời, lấy từ SO_LUONG_DONG_THOI (mặc định bằng num_parallel của hồ sơ GPU). Chú thích: giá trị này phải KHỚP với OLLAMA_NUM_PARALLEL; đặt cao hơn không làm nhanh hơn, chỉ đẩy hàng đợi vào bên trong bộ chạy nơi không quan sát được.
2. Độ dài hàng đợi tối đa DO_DAI_HANG_DOI_TOI_DA (mặc định 20). Vượt thì: nếu chuỗi còn tầng đám mây, bỏ qua tầng 0 và đi tiếp; nếu chuỗi chỉ có tầng 0 thì từ chối ngay mã HANG_DOI_DAY. Không để người dùng chờ vô hạn.
3. async def vao_hang(ma_yeu_cau) -> ViTri(vi_tri, uoc_luong_giay). Ước lượng = vị trí x thời gian xử lý trung vị của 20 yêu cầu local gần nhất. Router phát ra ManhPhatRa loại "hang_doi" ngay khi vào hàng (bổ sung loại này vào ManhPhatRa).
4. Truyền độ dài hàng đợi hiện tại vào goi_local để nó quyết định hạ cấp.
5. Hàm trang_thai() trả: dang_chay, dang_cho, thoi_gian_cho_trung_vi, so_bi_tu_choi_1_gio.

Phần 2 - chi phí và ngân sách (chỉ tính cho đám mây):
6. def uoc_tinh_chi_phi(tang, token_vao, token_ra) -> float lấy giá từ models.yaml. Tầng 0 trả 0 nhưng vẫn ghi token và toc_do_tok_s.
7. Mọi lượt gọi ghi một dòng vào bộ lưu luot_goi (thoi_diem, nguoi_id, nguon, tang, model, token_vao, token_ra, chi_phi_usd, do_tre_ms, thanh_cong, ma_yeu_cau). Giai đoạn này dùng lớp giao diện KhoLuotGoi với hiện thực trong bộ nhớ; Giai đoạn 3 thay bằng bảng PostgreSQL mà không đổi chữ ký.
8. Trước MỖI lời gọi tầng đám mây: tổng chi phí trong ngày vượt NGAN_SACH_NGAY_USD thì bỏ qua mọi tầng đám mây (không gọi), ghi cảnh báo; nếu cũng không còn local thì trả lỗi VUOT_NGAN_SACH. Đạt 80% ngân sách thì ghi cảnh báo mỗi lần.
9. def bao_cao_chi_phi() trả: chi_phi_hom_nay_usd, ngan_sach_ngay_usd, phan_tram_da_dung, phan_ra_theo_tang (so_luot, token, chi_phi), ty_le_local (phần trăm lượt do tầng 0 phục vụ).

Phần 3 - tỷ lệ rơi tầng:
10. Tính phần trăm số lượt KHÔNG được tầng ĐẦU của chuỗi phục vụ trong một giờ gần nhất. Vượt 20% thì ghi cảnh báo kèm lý do hỏng của tầng đầu. Đưa con số này vào bao_cao_chi_phi.

11. Kiểm thử backend/tests/test_hang_doi.py và backend/tests/test_chi_phi.py:
   - vượt độ dài tối đa, chuỗi chỉ local -> HANG_DOI_DAY
   - vượt độ dài tối đa, chuỗi có đám mây -> tầng 1 phục vụ
   - vị trí và ước lượng thời gian tính đúng
   - độ dài hàng đợi được truyền vào goi_local
   - vượt ngân sách -> 0 lời gọi đám mây, local vẫn phục vụ
   - chi phí tầng 0 bằng 0, tầng 4 tính đúng theo giá YAML
   - tỷ lệ rơi tầng tính đúng trên dữ liệu giả

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_hang_doi.py tests/test_chi_phi.py -v -> kỳ vọng: 7 kiểm thử qua
2. cd backend && pytest -q -> kỳ vọng: toàn bộ kiểm thử Giai đoạn 1–2 qua, không cần mạng
3. grep -n "OLLAMA_NUM_PARALLEL" backend/app/hang_doi/dieu_phoi.py -> kỳ vọng: có chú thích
4. grep -n "NGAN_SACH\|ngan_sach" backend/app/llm/router.py -> kỳ vọng: kiểm tra ngân sách nằm TRƯỚC lời gọi goi_dam_may
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Giới hạn đồng thời đọc từ cấu hình, có chú thích quan hệ với OLLAMA_NUM_PARALLEL.
- Hàng đợi đầy thì rơi sang đám mây nếu được phép, hoặc trả HANG_DOI_DAY ngay.
- Kiểm tra ngân sách TRƯỚC lời gọi đám mây; vượt ngân sách thì local vẫn phục vụ.
- Báo cáo chi phí có phân rã theo tầng, tỷ lệ local và tỷ lệ rơi tầng.
- Toàn bộ kiểm thử Giai đoạn 1-2 qua.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_hang_doi.py tests/test_chi_phi.py -v    # kỳ vọng: 7 passed
cd backend && pytest -q                                                 # kỳ vọng: tất cả passed
grep -n "OLLAMA_NUM_PARALLEL" backend/app/hang_doi/dieu_phoi.py         # kỳ vọng: có chú thích
grep -n "ngan_sach" backend/app/llm/router.py                           # kỳ vọng: trước goi_dam_may
```

```batbuoc
Rơi xuống tầng dưới thường đắt hơn. Phải ghi tầng nào đã phục vụ từng yêu cầu và cảnh báo khi tỷ lệ rơi tầng vượt ngưỡng. Nếu không, hoá đơn tăng mà không ai biết vì sao.
```

```meo
Khi chạm trần ngân sách đám mây, chuỗi lai không sập mà lùi về model local. Chất lượng giảm một chút, nhưng người dùng vẫn được phục vụ.
```

## Giai đoạn 3: API chạy được

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View. Chạy docker compose up -d db trước để có PostgreSQL cho migration (cổng 127.0.0.1:5432, nên alembic và pytest chạy được thẳng từ Git Bash).

**Mục tiêu giai đoạn.** Đưa lõi định tuyến ra thành một API hoàn chỉnh: phát theo dòng bằng SSE, lưu hội thoại kèm đầy đủ số liệu đo được, và đủ endpoint để bất kỳ giao diện nào dựng lên trên.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| POST /chat/stream với năm sự kiện SSE | Giao diện Angular → Giai đoạn 4 |
| Lược đồ nguoi_dung, hoi_thoai, luot, luot_goi và Alembic | Đăng nhập thật, JWT → Giai đoạn 5 (tạm dùng XAC_THUC_GIA) |
| Tự đặt tiêu đề hội thoại bằng model nhỏ | Hạn mức theo người dùng, theo IP → Giai đoạn 5 |
| Đủ endpoint hội thoại, chi phí, models, hàng đợi, ngữ cảnh | Trích dẫn tài liệu trong sự kiện xong → Giai đoạn 6 |
| /health tách khỏi /ready; lỗi thống nhất có ma_yeu_cau | Nhật ký JSON đầy đủ, /chi-so → Giai đoạn 5 |
| Hai móc kiểm duyệt rỗng nhưng đã được gọi | Ruột kiểm duyệt, che dữ liệu cá nhân → Giai đoạn 5 |

**Điều kiện hoàn thành**

- `curl -N` tới /api/v1/chat/stream thấy chữ hiện dần, đủ các sự kiện bat_dau, manh, xong.
- `alembic upgrade head` chạy sạch trên cơ sở dữ liệu trống; bảng luot có cột nguon_tham_chieu kiểu jsonb.
- Dừng db thì /ready trả 503 còn /health vẫn 200.
- Mọi phản hồi lỗi có dạng {"loi": {"ma", "thong_diep", "ma_yeu_cau"}}, không lộ vết ngăn xếp.
- Phát hành phiên bản `0.3.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml (frontend/package.json chỉ có từ PROMPT 14), ghi CHANGELOG.md, gắn thẻ `git tag v0.3.0` và `git tag giai-doan-3` trên cùng commit

### PROMPT 11. Phát câu trả lời theo dòng bằng SSE

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Chữ hiện dần ngay khi model sinh ra. Model local sinh chậm hơn đám mây, nên phát theo dòng là bắt buộc. Khi người dùng đóng tab, khe xử lý của GPU phải được giải phóng ngay.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: có đặt X-Accel-Buffering: no, và đóng kết nối thì lời gọi tới bộ chạy bị huỷ.

```prompt
Đọc AGENTS.md, quy tắc kỹ thuật 8. Viết backend/app/chat/su_kien_sse.py và endpoint POST /api/v1/chat/stream trong backend/app/main.py.

1. Thân yêu cầu (Pydantic): {hoi_thoai_id: int | None, noi_dung: str}. Chưa lưu cơ sở dữ liệu ở prompt này - lịch sử tạm lấy rỗng, lưu trữ nối ở PROMPT 12. Người dùng lấy qua lay_nguoi_dung_hien_tai() (tạm trả người dùng giả khi XAC_THUC_GIA=true).

2. Năm loại sự kiện, mỗi sự kiện là dòng "event: <tên>" và dòng "data: <JSON>":
   hang_doi {vi_tri, uoc_luong_giay}      - phát ngay khi vào hàng đợi local
   bat_dau  {hoi_thoai_id, nguon, tang, model, da_cat_ngu_canh, so_luot_bi_cat}
   manh     {noi_dung}                     - từng mẩu văn bản
   xong     {token_vao, token_ra, chi_phi_usd, toc_do_tok_s, do_tre_ms, nguon, tang, model, nhan_ai}
   loi      {ma, thong_diep, ma_yeu_cau, phan_da_nhan}
   nhan_ai là chuỗi "Nội dung do AI tạo - <model> - <dd/mm/yyyy - HH:mm>" để giao diện dán nhãn.
   Viết hàm dong_goi_su_kien(ten, du_lieu) -> str dùng chung; JSON giữ nguyên tiếng Việt (ensure_ascii=False).

3. Header: Content-Type text/event-stream, Cache-Control no-cache, Connection keep-alive, X-Accel-Buffering no. Gửi dòng chú thích ": ping" mỗi 15 giây khi đang chờ trong hàng đợi để proxy không cắt kết nối.

4. Luồng: sinh ma_yeu_cau 12 ký tự -> nhan = nhan_cua_hoi_thoai(...) -> dung_ngu_canh(...) -> goi_mo_hinh_theo_dong(...) -> đổi từng ManhPhatRa thành sự kiện SSE.

5. Lỗi giữa luồng: KHÔNG xoá phần chữ đã phát. Phát sự kiện loi với phan_da_nhan và đóng luồng. Lỗi trước khi phát mảnh đầu (ví dụ NGU_CANH_QUA_DAI, HANG_DOI_DAY) cũng trả bằng sự kiện loi, mã HTTP vẫn 200 vì luồng đã mở.

6. Người dùng đóng kết nối: bắt asyncio.CancelledError hoặc kiểm request.is_disconnected(), huỷ luôn lời gọi tới bộ chạy và nhả semaphore của DieuPhoi. Ghi nhật ký "nguoi_dung_huy". Đây là khác biệt quan trọng với bản chỉ có đám mây: một khe GPU bị chiếm vô ích nghĩa là người tiếp theo phải chờ.

7. backend/tests/test_stream.py dùng httpx.AsyncClient với router giả lập:
   - thứ tự sự kiện: bat_dau -> ít nhất 2 manh -> xong; xong có đủ siêu dữ liệu
   - khi vào hàng đợi, sự kiện hang_doi đứng trước bat_dau
   - lỗi sau 2 mảnh -> sự kiện loi có phan_da_nhan khớp hai mảnh đã phát
   - đóng kết nối giữa chừng -> lời gọi giả lập bị huỷ, semaphore trở về giá trị ban đầu
   - header X-Accel-Buffering bằng no

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_stream.py -v -> kỳ vọng: 5 kiểm thử qua
2. docker compose up -d --build backend, chờ healthy (docker compose ps), rồi curl -N -X POST localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"Giải thích ngắn gọn giá điện bậc thang là gì"}' -> kỳ vọng: chữ hiện DẦN, thấy event: bat_dau, nhiều event: manh, event: xong
3. curl -s -D - -o /dev/null -X POST localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}' | grep -i x-accel -> kỳ vọng: X-Accel-Buffering: no
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Năm loại sự kiện đúng tên và đúng trường như quy ước.
- Có X-Accel-Buffering: no và Cache-Control: no-cache.
- Lỗi giữa luồng không xoá phần chữ đã phát, có phan_da_nhan.
- Đóng kết nối thì huỷ lời gọi và giải phóng khe đồng thời.
- Năm kiểm thử qua.

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_stream.py -v                     # kỳ vọng: 5 passed
curl -N -X POST localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"Giải thích ngắn gọn giá điện bậc thang là gì"}'   # kỳ vọng: chữ hiện dần
curl -s -D - -o /dev/null -X POST localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}' | grep -i x-accel   # kỳ vọng: no
```

```batbuoc
Tham số -N của curl tắt bộ đệm phía curl. Không có nó, bạn sẽ tưởng phát theo dòng bị hỏng trong khi nó vẫn chạy. Ngược lại, nếu có -N mà chữ vẫn im lặng rồi hiện một lần thì chưa đạt. Nguyên nhân thường là thiếu X-Accel-Buffering hoặc trả về bằng một chuỗi gom sẵn.
```

### PROMPT 12. Lưu hội thoại và lược đồ cơ sở dữ liệu

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Nhớ được mạch trò chuyện trong phiên, xem lại được sau, và lưu đủ số liệu từng lượt để làm nền cho bộ đánh giá, giám sát chi phí và truy vết theo luật.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: nội dung lưu vào bảng luot là nội dung đã qua móc kiểm duyệt, và cột nguon_tham_chieu được tạo sẵn nhưng để trống.

```prompt
Đọc AGENTS.md. Viết backend/app/core/csdl.py, backend/app/chat/hoi_thoai.py và migration Alembic.

1. csdl.py: SQLAlchemy 2 bất đồng bộ (psycopg), đọc DATABASE_URL, phiên làm việc qua dependency lay_phien(). psycopg bất đồng bộ KHÔNG chạy với ProactorEventLoop mặc định của Windows: trong alembic/env.py và backend/tests/conftest.py, khi sys.platform == "win32" thì đặt asyncio.WindowsSelectorEventLoopPolicy() trước khi tạo vòng lặp. Trong container Linux không cần.

2. Bốn bảng, tên tiếng Việt không dấu, kèm migration đầu tiên:
   nguoi_dung: id, ten_dang_nhap (duy nhất), mat_khau_bam (cho phép rỗng tới Giai đoạn 5), ho_ten, vai_tro, bac, phong_ban, dang_hoat_dong, tao_luc
   hoi_thoai: id, nguoi_id, tieu_de, tao_luc, cap_nhat_luc, da_xoa
   luot: id, hoi_thoai_id (ON DELETE CASCADE), vai_tro (he_thong|nguoi_dung|tro_ly), noi_dung, nguon, tang, bac_local, model_da_dung, token_vao, token_ra, chi_phi_usd, toc_do_tok_s, thoi_gian_nap_ms, do_tre_ms, da_cat_ngu_canh, so_luot_bi_cat, nhan_du_lieu, nguon_tham_chieu (jsonb, để trống - chừa cho RAG ở Giai đoạn 6), phien_ban_loi_nhac, ma_yeu_cau, tao_luc
   luot_goi: id, thoi_diem, nguoi_id, nguon, tang, model, token_vao, token_ra, chi_phi_usd, do_tre_ms, thanh_cong, ma_yeu_cau
   Chỉ mục: luot(hoi_thoai_id, tao_luc), hoi_thoai(nguoi_id, cap_nhat_luc), luot_goi(thoi_diem), luot_goi(nguoi_id, thoi_diem).
   Thay hiện thực KhoLuotGoi trong bộ nhớ ở PROMPT 10 bằng hiện thực PostgreSQL, giữ nguyên chữ ký.

3. Khi nhận tin nhắn mới ở /api/v1/chat/stream: nếu không có hoi_thoai_id thì tạo hội thoại mới và trả id trong sự kiện bat_dau; đọc các lượt của hội thoại theo thứ tự thời gian (bỏ hội thoại đã xoá mềm), gọi dung_ngu_canh(), rồi goi_mo_hinh_theo_dong(). Sau khi xong, lưu cả lượt người dùng và lượt trả lời trong MỘT giao dịch, kèm đầy đủ số liệu đo được, phien_ban_loi_nhac đọc từ dòng đầu prompts/he_thong.md. Nếu luồng lỗi giữa chừng, vẫn lưu phần đã nhận và ghi nhật ký ket_thuc_do_loi.

4. Tự đặt tiêu đề: sau lượt trả lời ĐẦU TIÊN, chạy nền một lời gọi goi_mo_hinh với lời nhắc prompts/tieu_de.md (tối đa 8 từ), BUỘC dùng tầng 0 bậc nho - tham số tuy_chon uu_tien_bac_nho=True. NGOẠI LỆ: khi so_model_nap_cung_luc = 1 (gpu8 trên laptop) dùng bậc chinh đang nằm trong VRAM, vì nạp bậc nho sẽ đẩy model chính ra và người hỏi tiếp theo phải chờ nạp lại. Chú thích rõ: dùng bậc nhỏ để không chiếm khe của model chính, và không gửi nội dung hội thoại ra đám mây chỉ để đặt tiêu đề. Không chặn phản hồi cho người dùng.

5. Người dùng tạm: lay_nguoi_dung_hien_tai() trong app/core/xac_thuc.py trả một người dùng giả cố định (id 1, phong_ban CNTT, vai_tro nguoi_dung) khi XAC_THUC_GIA=true; khi false thì trả 401 CHUA_XAC_THUC. Ghi chú: đây là chỗ thay ruột ở Giai đoạn 5 và Giai đoạn 8, mọi nơi khác chỉ phụ thuộc đối tượng NguoiDung. Khởi động với MOI_TRUONG=prod mà XAC_THUC_GIA=true thì từ chối khởi động.

6. backend/tests/test_hoi_thoai.py (dùng PostgreSQL thật qua docker compose hoặc testcontainers): ghép ngữ cảnh đúng thứ tự thời gian; số liệu đo được lưu đầy đủ; đặt tiêu đề dùng đúng bậc nho (hoặc bậc chinh khi so_model_nap_cung_luc = 1) và không gọi đám mây; xoá hội thoại thì các lượt bị xoá theo.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && alembic upgrade head -> kỳ vọng: chạy sạch, không cảnh báo
2. docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d luot"' -> kỳ vọng: có cột nguon_tham_chieu kiểu jsonb và cột phien_ban_loi_nhac
3. cd backend && pytest tests/test_hoi_thoai.py -v -> kỳ vọng: 4 kiểm thử qua
4. docker compose up -d --build backend; gửi tin thứ nhất bằng curl -N -X POST localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}', đọc hoi_thoai_id trong sự kiện bat_dau, gửi tin thứ hai kèm hoi_thoai_id đó; rồi docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select vai_tro, nguon, tang, token_ra from luot order by id"' -> kỳ vọng: 4 dòng, lượt tro_ly có nguon, tang, token_ra
5. docker compose run --rm -e MOI_TRUONG=prod -e XAC_THUC_GIA=true backend -> kỳ vọng: thoát mã khác 0 với thông điệp rõ ràng (biến đặt trước lệnh docker compose KHÔNG ghi đè env_file, phải dùng -e)
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Bốn bảng đúng như liệt kê, có cột nguon_tham_chieu để trống và cột phien_ban_loi_nhac.
- Mỗi lượt trả lời lưu đủ nguồn, tầng, bậc, model, token, chi phí, tốc độ, độ trễ.
- Đặt tiêu đề dùng bậc nho local, chạy nền, không gọi đám mây.
- KhoLuotGoi đã chuyển sang PostgreSQL mà không đổi chữ ký.
- prod kèm XAC_THUC_GIA=true thì không khởi động.

**Tự đánh giá**

```danhgia
cd backend && alembic upgrade head                                          # kỳ vọng: sạch
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d luot"'   # kỳ vọng: nguon_tham_chieu jsonb
cd backend && pytest tests/test_hoi_thoai.py -v                             # kỳ vọng: 4 passed
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select vai_tro, nguon, tang, token_ra from luot order by id"'   # kỳ vọng: 4 dòng
docker compose run --rm -e MOI_TRUONG=prod -e XAC_THUC_GIA=true backend     # kỳ vọng: từ chối khởi động
```

```meo
Lưu phien_ban_loi_nhac trên từng lượt chỉ tốn vài byte. Khi có khiếu nại, đây là cách duy nhất để trả lời "câu trả lời sai hôm 15 là do lời nhắc cũ hay do model đổi".
```

### PROMPT 13. API đầy đủ, hai móc kiểm duyệt và lỗi thống nhất

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Tập hợp mọi thứ thành một API dùng được cho giao diện và cho tích hợp máy với máy, chừa sẵn chỗ cắm kiểm duyệt, và bảo đảm lỗi không bao giờ lộ chi tiết kỹ thuật ra ngoài.

**Làm trước.** Đọc Implementation Plan, kiểm hai điều: /ready không gọi sinh văn bản, và hai móc kiểm duyệt được GỌI trong luồng dù ruột còn rỗng.

```prompt
Đọc AGENTS.md. Hoàn thiện backend/app/main.py, backend/app/core/loi.py, backend/app/core/bao_mat.py (phần móc).

1. Các endpoint, mọi đầu vào kiểm bằng Pydantic, mọi endpoint nghiệp vụ phụ thuộc lay_nguoi_dung_hien_tai(). Endpoint nghiệp vụ đặt dưới tiền tố /api/v1 (theo .agents/rules/versioning.md); riêng /health và /ready ở gốc.
   POST /api/v1/chat/stream           - như PROMPT 11–12
   POST /api/v1/chat                  - không phát theo dòng, cho tích hợp máy với máy; trả đủ nguồn, tầng, model, token, chi phí, độ trễ, nhan_ai
   GET  /api/v1/hoi-thoai             - danh sách của người dùng hiện tại, phân trang, sắp theo cap_nhat_luc giảm dần
   GET  /api/v1/hoi-thoai/{id}        - toàn bộ lượt; trả 404 KHONG_TIM_THAY nếu không thuộc người dùng hiện tại
   DELETE /api/v1/hoi-thoai/{id}      - xoá mềm
   GET  /api/v1/chi-phi               - bao_cao_chi_phi() ở PROMPT 10
   GET  /api/v1/models                - chế độ định tuyến hiện hành, hồ sơ GPU, hai bậc local, bốn tầng đám mây và cờ kha_dung (KHÔNG trả khoá)
   GET  /api/v1/hang-doi/tinh-trang   - DieuPhoi.trang_thai()
   GET  /api/v1/ngu-canh/tinh-trang   - num_ctx cấu hình và thực tế theo bậc, ngân sách token, số lượt trung bình giữ được
   GET  /health                    - chỉ kiểm tiến trình còn sống, trả ngay, không chạm cơ sở dữ liệu hay bộ chạy
   GET  /ready                     - kiểm cơ sở dữ liệu VÀ (bộ chạy local HOẶC ít nhất một tầng đám mây khả dụng); trả 503 kèm chi tiết thành phần hỏng. Kiểm bộ chạy bằng GET /api/tags (hoặc /models với LM Studio) timeout 2 giây, KHÔNG gọi sinh văn bản.

2. Hai móc kiểm duyệt trong bao_mat.py, viết RỖNG nhưng GỌI SẴN trong luồng /api/v1/chat và /api/v1/chat/stream:
   async def kiem_duyet_dau_vao(noi_dung, nguoi) -> KetQuaKiemDuyet   (gọi trước khi dựng ngữ cảnh)
   async def kiem_duyet_dau_ra(noi_dung, nguoi) -> KetQuaKiemDuyet    (gọi trên toàn văn trước khi lưu)
   KetQuaKiemDuyet: cho_qua (bool), ly_do (str | None), noi_dung_thay_the (str | None). Giai đoạn này luôn trả cho_qua=True. Chú thích: đây là chỗ cắm kiểm duyệt ở Giai đoạn 5, gắn vào đây thì không phải sửa luồng.

3. loi.py: lớp LoiUngDung(ma, thong_diep, http) và bộ bắt lỗi toàn cục. Mọi lỗi trả {"loi": {"ma", "thong_diep", "ma_yeu_cau"}}. Thông điệp cho người dùng viết tiếng Việt dễ hiểu; vết ngăn xếp chỉ ghi nhật ký, KHÔNG BAO GIỜ trả ra ngoài. Bảng mã tối thiểu: HANG_DOI_DAY 503, QUA_HAN 504, NGU_CANH_QUA_DAI 422, BO_CHAY_KHONG_PHAN_HOI 503, HET_CHUOI_DU_PHONG 503, VUOT_NGAN_SACH 503, VUOT_HAN_MUC 429, KHONG_CO_QUYEN 403, CHUA_XAC_THUC 401, DAU_VAO_KHONG_HOP_LE 422, NOI_DUNG_BI_CHAN 422, KHONG_TIM_THAY 404, LOI_HE_THONG 500.

4. ma_yeu_cau: middleware sinh 12 ký tự, nhận mã do phía gọi truyền qua header X-Ma-Yeu-Cau, trả lại trong header phản hồi. Lưu trong contextvars.

5. CORS: đọc CORS_ORIGINS; MOI_TRUONG=prod thì cấm dấu sao.

6. Ghi đủ các endpoint và mã lỗi vào README.md mục "API".

7. backend/tests/test_api.py: /health trả nhanh kể cả khi cơ sở dữ liệu hỏng; /ready trả 503 và nêu rõ thành phần hỏng; /ready không gọi sinh văn bản (đếm lời gọi giả lập); GET /api/v1/hoi-thoai/{id} của người khác trả 404; mọi lỗi có ma_yeu_cau và không có chữ "Traceback"; hai móc kiểm duyệt được gọi đúng một lần mỗi yêu cầu.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest -q -> kỳ vọng: toàn bộ kiểm thử qua
2. docker compose up -d --build && docker compose exec backend alembic upgrade head && curl -s localhost:8000/health -> kỳ vọng: 200 ngay
3. curl -s localhost:8000/ready | python -m json.tool -> kỳ vọng: 200, nêu tình trạng db, bo_chay, dam_may
4. docker compose stop db && curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/ready && curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/health -> kỳ vọng: 503 rồi 200; sau đó docker compose start db
5. curl -s localhost:8000/api/v1/hoi-thoai/999999 -> kỳ vọng: {"loi": {"ma": "KHONG_TIM_THAY", ...}} có ma_yeu_cau
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- /health và /ready tách biệt; /ready không gọi sinh văn bản.
- Hai móc kiểm duyệt rỗng nhưng đã được gọi trong luồng, có kiểm thử đếm số lần gọi.
- Mọi lỗi có mã, thông điệp tiếng Việt và ma_yeu_cau; không lộ vết ngăn xếp.
- GET /api/v1/hoi-thoai/{id} của người khác trả 404.
- README có mục API liệt kê endpoint và mã lỗi.

**Tự đánh giá**

```danhgia
cd backend && pytest -q                                              # kỳ vọng: tất cả passed
curl -s localhost:8000/health                                        # kỳ vọng: 200 ngay
curl -s localhost:8000/ready | python -m json.tool                   # kỳ vọng: 200, có db/bo_chay/dam_may
docker compose stop db && curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/ready   # kỳ vọng: 503
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/health       # kỳ vọng: 200
curl -s localhost:8000/api/v1/hoi-thoai/999999                          # kỳ vọng: KHONG_TIM_THAY + ma_yeu_cau
```

```batbuoc
/health và /ready hay bị gộp làm một. Bộ cân bằng tải và Kubernetes (Giai đoạn 10) dùng /ready để quyết định có đẩy lưu lượng vào hay không; gộp làm một khiến lưu lượng đổ vào lúc tiến trình vừa lên mà cơ sở dữ liệu chưa sẵn sàng.
```

```meo
Nhiều mẫu mã trên mạng kiểm tra sức khoẻ bằng cách sinh một câu ngắn. Với đám mây chỉ tốn vài đồng; với bản local, mỗi lần kiểm tra chiếm một trong rất ít khe GPU, trong khi bộ kiểm tra sức khoẻ thường chạy mỗi mười giây.
```

## Giai đoạn 4: Giao diện Angular, mốc chatbot dùng được

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View. Cài Node LTS và Angular CLI (npm install -g @angular/cli), đặt export NG_CLI_ANALYTICS=false để CLI không hỏi, chạy docker compose up -d để backend sẵn sàng ở cổng 8000. Antigravity có trình duyệt tích hợp để agent tự mở trang và chụp màn hình khi tự đánh giá.

**Mục tiêu giai đoạn.** Một giao diện Angular theo đúng chuẩn thiết kế DESIGN.md, hiển thị trung thực những gì đặc thù của chuỗi lai (hàng đợi, nạp model, cắt ngữ cảnh, tầng nào trả lời), không gọi ra Internet, và đóng gói chung với backend bằng một lệnh. Cuối giai đoạn này, một cán bộ, công nhân viên có thể mở trình duyệt và trò chuyện được.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Workspace Angular standalone, signals, token màu từ DESIGN.md | Trang đăng nhập, guard, interceptor → Giai đoạn 5 |
| Tự host phông Lexend và Source Code Pro, không CDN | Khung trích dẫn tài liệu → Giai đoạn 6 |
| Dịch vụ SSE bằng fetch và ReadableStream, API client có kiểu | Trang quản trị nạp tài liệu → Giai đoạn 6 |
| Màn hình chat, danh sách hội thoại, chip gợi ý nhanh | Bảng quản trị người dùng, chi phí phòng ban → Giai đoạn 8 |
| Hiển thị hàng đợi, nạp model, cắt ngữ cảnh, huy hiệu tầng | Đăng nhập một lần OIDC → Giai đoạn 8 |
| Đóng gói nginx, proxy /api tắt đệm; kiểm thử đơn vị và Playwright | Triển khai Kubernetes → Giai đoạn 10 |

**Điều kiện hoàn thành**

- `docker compose up -d --build` rồi mở http://localhost:8080 trò chuyện được; chữ hiện dần qua nginx.
- Tab Network của trình duyệt không có yêu cầu nào ra ngoài localhost.
- Lỗi giữa chừng giữ nguyên phần chữ đã hiện; nút Dừng huỷ được luồng.
- `ng test` và `npx playwright test` qua; dùng được ở bề ngang 375 và 1280.
- Nhờ một cán bộ chưa từng thấy dự án dùng thử mười phút và ghi lại chỗ họ vấp.
- Phát hành phiên bản `0.4.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v0.4.0` và `git tag giai-doan-4` trên cùng commit

### PROMPT 14. Workspace Angular và chuẩn thiết kế

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Dựng workspace Angular theo cách hiện đại (standalone, signals), đưa toàn bộ token thiết kế của DESIGN.md vào một chỗ, và tự host phông chữ để giao diện không gọi ra Internet.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: không có liên kết nào tới fonts.googleapis.com, CDN hay dịch vụ ngoài.

```prompt
Đọc AGENTS.md và DESIGN.md. Tạo workspace Angular trong thư mục frontend/. XOÁ tệp frontend/README.md tạm ở PROMPT 2 TRƯỚC khi chạy ng new (thư mục phải trống, nếu không ng new báo trùng tệp) - đây là lần xoá được phép.

1. Tạo bằng Angular CLI bản ổn định hiện hành, không tương tác: NG_CLI_ANALYTICS=false ng new tro-ly-noi-bo --directory frontend --routing --style=scss --ssr=false --skip-git --defaults. Đặt "version" trong frontend/package.json bằng đúng số phiên bản hiện tại của backend/pyproject.toml (theo .agents/rules/versioning.md). Ghi phiên bản Angular thực dùng vào README.md. Dùng standalone components và signals cho trạng thái; bật change detection không zone nếu bản CLI hỗ trợ ổn định.

2. Cấu trúc:
   src/app/core/      api.service.ts, sse.service.ts, mo-hinh.ts (kiểu dữ liệu), cau-hinh.ts
   src/app/features/chat/, src/app/features/hoi-thoai/
   src/app/shared/    huy-hieu-mo-hinh/, dong-thong-bao/
   src/styles/        _tokens.scss, _typography.scss, _base.scss
   Tên tệp dạng kebab-case không dấu; tên lớp, biến TypeScript dùng camelCase nhất quán.

3. _tokens.scss: chép NGUYÊN VĂN khối :root ở mục 9 của DESIGN.md (màu, phông, khoảng cách, bo góc, bóng đổ, chuyển động). Không tự đặt mã màu mới ngoài bộ token.

4. Phông chữ: cài @fontsource/lexend (400, 500, 600, 700) và @fontsource/source-code-pro (400), hoặc chép tệp woff2 vào src/assets/fonts/ và khai báo @font-face cục bộ với font-display: swap. KHÔNG dùng Google Fonts hay CDN. Ghi giấy phép SIL OFL của phông vào frontend/THIRD_PARTY.md.

5. _typography.scss theo thang chữ mục 4.2 DESIGN.md; line-height đoạn văn tối thiểu 1.5 cho dấu tiếng Việt; không viết hoa toàn bộ câu dài.

6. App shell theo mục 6 DESIGN.md: header 64px (tiêu đề "Trợ lý nội bộ", vùng tên người dùng tạm), sidebar 240px thu gọn 72px, ẩn thành drawer dưới 768px. Trong sidebar chỉ để mục "Trò chuyện" - các mục khác của DESIGN.md chưa làm.

7. src/environments: apiGoc = "/api/v1" (đi qua proxy), không ghi cứng localhost:8000. Thêm proxy.conf.json cho ng serve trỏ /api, /health, /ready tới http://localhost:8000 và khai báo proxyConfig trong angular.json để ng serve tự dùng.

8. Không cài thư viện UI lớn (Angular Material, PrimeNG...). Được cài: @fontsource/*. Thư viện hiển thị Markdown ở PROMPT 16 phải hỏi trước.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd frontend && npx ng build -> kỳ vọng: build thành công
2. grep -rnE "googleapis|gstatic|cdn\.|unpkg|jsdelivr" frontend/src -> kỳ vọng: rỗng
3. grep -n "brand-blue-base" frontend/src/styles/_tokens.scss -> kỳ vọng: có, giá trị #016BF8
4. ls frontend/node_modules/@fontsource/lexend hoặc frontend/src/assets/fonts -> kỳ vọng: có tệp woff2
5. (cd frontend && npx ng serve --port 4200 &) rồi chờ khoảng 20 giây, curl -s localhost:4200 | grep -c "<app-root" -> kỳ vọng: 1; mở http://localhost:4200 bằng trình duyệt tích hợp của Antigravity ở bề ngang 375 và 1280, chụp màn hình -> kỳ vọng: header, sidebar hoặc drawer hiển thị đúng; xong thì dừng ng serve
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Workspace Angular trong frontend/, standalone, dùng signals; phiên bản ghi trong README.
- _tokens.scss khớp nguyên văn mục 9 DESIGN.md.
- Phông tự host, có THIRD_PARTY.md; không một liên kết ngoài nào.
- App shell responsive theo mục 6 DESIGN.md.
- ng build thành công; version trong package.json bằng version backend.

**Tự đánh giá**

```danhgia
cd frontend && npx ng build                                             # kỳ vọng: thành công
grep -rnE "googleapis|gstatic|cdn\.|unpkg|jsdelivr" frontend/src        # kỳ vọng: rỗng
grep -n "brand-blue-base" frontend/src/styles/_tokens.scss              # kỳ vọng: #016BF8
(cd frontend && npx ng serve --port 4200 &)                            # chạy nền
curl -s localhost:4200 | grep -c "<app-root"                           # kỳ vọng: 1; xem ảnh chụp ở 375 và 1280
```

```batbuoc
Không gọi phông từ Google Fonts. Ngoài lý do máy chủ nội bộ có thể không ra được Internet, mỗi lần tải phông là một lần trình duyệt của cán bộ gửi địa chỉ IP và trang đang xem ra dịch vụ bên ngoài.
```

### PROMPT 15. Dịch vụ SSE và API client

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Nhận luồng SSE từ POST /api/v1/chat/stream một cách đáng tin cậy. EventSource của trình duyệt chỉ hỗ trợ GET và không gửi được header Authorization, nên phải tự đọc luồng bằng fetch.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: bộ tách sự kiện xử lý đúng trường hợp một sự kiện bị cắt đôi giữa hai lần đọc.

```prompt
Đọc AGENTS.md. Viết frontend/src/app/core/mo-hinh.ts, api.service.ts, sse.service.ts.

1. mo-hinh.ts: kiểu TypeScript khớp CHÍNH XÁC năm sự kiện của backend: SuKienHangDoi {vi_tri, uoc_luong_giay}, SuKienBatDau {hoi_thoai_id, nguon, tang, model, da_cat_ngu_canh, so_luot_bi_cat}, SuKienManh {noi_dung}, SuKienXong {token_vao, token_ra, chi_phi_usd, toc_do_tok_s, do_tre_ms, nguon, tang, model, nhan_ai}, SuKienLoi {ma, thong_diep, ma_yeu_cau, phan_da_nhan}. Hợp chúng thành union có trường phân biệt loai. Thêm kiểu HoiThoai, Luot, BaoCaoChiPhi, TrangThaiModels.

2. sse.service.ts: hàm guiTinNhan(noiDung, hoiThoaiId, signal: AbortSignal) trả về Observable<SuKien>:
   - dùng fetch POST /api/v1/chat/stream, header Accept: text/event-stream, Content-Type: application/json
   - đọc response.body bằng getReader() và TextDecoder với stream: true
   - tách sự kiện theo dòng trống; ghép dòng "event:" và "data:"; bỏ qua dòng chú thích bắt đầu bằng ":" (ping)
   - giữ phần dư khi một sự kiện bị cắt giữa hai lần đọc
   - AbortController để nút Dừng huỷ luồng; huỷ thì đóng reader, không phát lỗi giả
   - phản hồi không phải 200 (401, 429, 503): đọc JSON {loi: {...}} và phát SuKienLoi với thông điệp của máy chủ, không nuốt lỗi; 429 đọc thêm header Retry-After
   - chú thích rõ vì sao không dùng EventSource

3. api.service.ts dùng HttpClient: layDanhSachHoiThoai(trang), layHoiThoai(id), xoaHoiThoai(id), layChiPhi(), layModels(), layTrangThaiHangDoi(). Nhận header X-Ma-Yeu-Cau; khi lỗi, hiển thị được ma_yeu_cau để người dùng báo bộ phận hỗ trợ.

4. Kiểm thử đơn vị bằng trình chạy mặc định của bản CLI (Vitest hoặc Jasmine): sse.service.spec.ts dùng ReadableStream giả:
   - tách đúng ba sự kiện nằm trong một khối dữ liệu
   - ghép đúng một sự kiện bị cắt đôi giữa hai khối
   - bỏ qua dòng ": ping"
   - phản hồi 429 phát SuKienLoi có thông điệp máy chủ
   - abort thì dừng mà không phát SuKienLoi

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd frontend && npx ng test --watch=false -> kỳ vọng: 5 kiểm thử của sse.service qua
2. grep -rn "new EventSource" frontend/src -> kỳ vọng: rỗng
3. grep -n "Retry-After" frontend/src/app/core/sse.service.ts -> kỳ vọng: có xử lý
4. npx ng build -> kỳ vọng: thành công, không lỗi kiểu
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Kiểu TypeScript khớp đúng tên và trường của năm sự kiện backend.
- Dịch vụ SSE dùng fetch và ReadableStream, xử lý sự kiện bị cắt đôi, bỏ qua ping, hỗ trợ huỷ.
- Lỗi HTTP hiển thị thông điệp và ma_yeu_cau của máy chủ.
- Năm kiểm thử đơn vị qua.

**Tự đánh giá**

```danhgia
cd frontend && npx ng test --watch=false                       # kỳ vọng: 5 passed
grep -rn "new EventSource" frontend/src                        # kỳ vọng: rỗng
grep -n "Retry-After" frontend/src/app/core/sse.service.ts     # kỳ vọng: có
npx ng build                                                   # kỳ vọng: thành công
```

```meo
Lỗi "sự kiện bị cắt đôi" không bao giờ lộ ra khi chạy trên máy cá nhân vì mạng quá nhanh, nhưng xuất hiện ngay khi đi qua proxy hoặc mạng chậm. Kiểm thử ghép khối là kiểm thử rẻ nhất để tránh nó.
```

### PROMPT 16. Màn hình trò chuyện và danh sách hội thoại

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Một màn hình trò chuyện dùng được hằng ngày. Người dùng thấy được mình đang chờ, hệ thống đã lược bớt phần nào của hội thoại, và câu trả lời do model nào sinh ra.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: khi luồng lỗi giữa chừng, phần chữ đã hiện được giữ nguyên.

```prompt
Đọc AGENTS.md và DESIGN.md mục 7, 8. Viết frontend/src/app/features/chat/ và frontend/src/app/features/hoi-thoai/.

1. Bố cục: cột trái là danh sách hội thoại (nút "Hội thoại mới", xoá có hỏi lại bằng hộp thoại của ứng dụng - không dùng window.confirm); vùng chính là khung chat, ô nhập ở dưới.

2. Bong bóng theo DESIGN.md 7.1: người dùng nền #016BF8 chữ trắng căn phải bo 16 16 4 16; trợ lý nền trắng viền #E8EDEB căn trái bo 16 16 16 4. Dùng biến token, không ghi mã màu trực tiếp.

3. Màn hình chào: bốn chip gợi ý nhanh theo DESIGN.md 7.3 ("Tra cứu tiền điện tháng gần nhất", "Lịch ngừng giảm cung cấp điện tuần này", "Quy trình đăng ký gắn mới công tơ điện tử", "Báo cáo sự cố mất điện đột xuất"). Bấm chip là gửi câu đó.

4. Hành vi bắt buộc:
   a) Chữ hiện dần theo sự kiện manh, tự cuộn xuống, nhưng KHÔNG giật cuộn nếu người dùng đang kéo lên đọc.
   b) Trong lúc chờ: nút gửi bị khoá, có chỉ báo đang soạn; có nút Dừng gọi AbortController.
   c) Sự kiện hang_doi: hiện "Anh/Chị đang ở vị trí N, dự kiến chờ khoảng X giây", cập nhật dần.
   d) Nạp model: nếu sau 3 giây vẫn chưa có manh đầu tiên, hiện "Đang nạp model, lần đầu mất lâu hơn".
   e) da_cat_ngu_canh = true: chèn một dòng nhỏ màu xám trong hội thoại "Đã lược bớt N lượt đầu để vừa cửa sổ ngữ cảnh".
   f) Huy hiệu đo lường dưới mỗi câu trả lời (DESIGN.md 7.2, Source Code Pro 12px, nền blue-light-3): nguồn "Local" hoặc "Đám mây", tầng, model, token vào/ra, chi phí (ẩn khi bằng 0), tok/s, độ trễ. Nếu câu do bậc nho hoặc tầng đám mây trả lời trong chế độ local_truoc, huy hiệu có viền vàng yellow-base để người dùng biết đã hạ cấp hoặc rơi tầng.
   g) Nhãn "Nội dung do AI tạo" lấy từ nhan_ai, hiển thị dưới mọi câu trả lời.
   h) Lỗi giữa chừng: GIỮ NGUYÊN phần chữ đã nhận, hiện một dòng lỗi nhỏ màu red-base bên dưới kèm ma_yeu_cau. KHÔNG xoá trắng những gì người dùng đã đọc.
   i) Enter để gửi, Shift+Enter xuống dòng; ô nhập tự giãn tối đa 6 dòng.
   j) Hiển thị khối mã, danh sách, bảng, in đậm. Nội dung model sinh ra luôn được làm sạch trước khi chèn vào DOM (DomSanitizer hoặc thư viện Markdown có sanitize - thêm thư viện phải hỏi trước). Không gán innerHTML bằng chuỗi thô.
   k) Nút sao chép câu trả lời.

5. Thanh trạng thái nhỏ cuối khung chat: chế độ định tuyến hiện hành (lấy từ /api/v1/models), chi phí đám mây hôm nay (lấy từ /api/v1/chi-phi).

6. Mọi nhãn tiếng Việt, xưng hô "Anh/Chị". Tiếp cận: nút có aria-label, vùng tin nhắn có aria-live="polite", tương phản đạt WCAG AA theo DESIGN.md 3.4, điều khiển được bằng bàn phím.

7. Kiểm thử đơn vị cho component chat: lỗi giữa chừng giữ chữ; da_cat hiện dòng xám; huy hiệu viền vàng khi tang khác 0 hoặc bac_local = 2; chuỗi có thẻ script trong manh không được thực thi.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd frontend && npx ng test --watch=false -> kỳ vọng: kiểm thử chat và sse đều qua
2. grep -rnE "innerHTML\s*=" frontend/src/app -> kỳ vọng: rỗng
3. grep -rnE "window\.confirm|alert\(" frontend/src/app -> kỳ vọng: rỗng
4. (cd frontend && npx ng serve &), mở http://localhost:4200 bằng trình duyệt tích hợp, gửi "Cách tính tiền điện sinh hoạt bậc thang" -> kỳ vọng: chữ hiện dần, có huy hiệu, có nhãn Nội dung do AI tạo
5. Đặt CHE_DO_DINH_TUYEN=chi_local trong .env, docker compose up -d backend; gửi câu yêu cầu trả lời dài ("Viết 20 gạch đầu dòng về an toàn điện"), khi chữ đang hiện thì tắt Ollama bằng PowerShell: Stop-Process -Name "ollama*" -Force -> kỳ vọng: phần chữ đã hiện giữ nguyên, có dòng lỗi đỏ kèm ma_yeu_cau. Sau đó bật lại Ollama và trả CHE_DO_DINH_TUYEN=local_truoc
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Màn hình chat, danh sách hội thoại, chip gợi ý đúng DESIGN.md.
- Hiển thị đủ: vị trí hàng đợi, đang nạp model, dòng cắt ngữ cảnh, huy hiệu tầng/model/tok/s/chi phí, nhãn AI.
- Lỗi giữa chừng không xoá phần chữ đã hiện; nút Dừng hoạt động.
- Nội dung model được làm sạch trước khi hiển thị; không innerHTML thô, không alert/confirm.
- Kiểm thử component qua.

**Tự đánh giá**

```danhgia
cd frontend && npx ng test --watch=false                 # kỳ vọng: tất cả passed
grep -rnE "innerHTML\s*=" frontend/src/app               # kỳ vọng: rỗng
grep -rnE "window\.confirm|alert\(" frontend/src/app     # kỳ vọng: rỗng
(cd frontend && npx ng serve &)                         # mở localhost:4200: chữ hiện dần, huy hiệu, nhãn AI
# chi_local + PowerShell: Stop-Process -Name "ollama*" -Force giữa chừng   # kỳ vọng: giữ chữ + dòng lỗi đỏ có ma_yeu_cau
```

```batbuoc
Câu trả lời của model là dữ liệu không đáng tin, kể cả khi model chạy trên máy của doanh nghiệp: một tài liệu hoặc một câu hỏi có chủ đích có thể khiến model sinh ra mã HTML hoặc script. Luôn làm sạch trước khi chèn vào DOM.
```

```meo
Khi hạ cấp hoặc rơi tầng, huy hiệu có viền vàng. Nhìn vào đó, người dùng tự hiểu vì sao hôm nay câu trả lời ngắn hơn hay khác giọng hơn, không cần gọi điện hỏi bộ phận CNTT.
```

### PROMPT 17. Đóng gói giao diện với nginx và kiểm thử đầu cuối

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Giao diện và backend chạy chung bằng một lệnh docker compose, phát theo dòng vẫn hoạt động khi đi qua nginx, và có bộ kiểm thử đầu cuối để mọi thay đổi sau không phá luồng chính.

**Làm trước.** Đọc Implementation Plan, kiểm một điều: khối location /api/ của nginx có proxy_buffering off.

```prompt
Đọc AGENTS.md. Viết frontend/Dockerfile, frontend/nginx.conf, cập nhật docker-compose.yml, và bộ kiểm thử Playwright.

1. frontend/Dockerfile hai tầng: tầng dựng node LTS chạy npm ci và ng build cấu hình production; tầng chạy nginxinc/nginx-unprivileged:alpine (chạy sẵn bằng người dùng không phải root, nghe cổng 8080 vì người dùng thường không bind được cổng 80), chép bản build vào /usr/share/nginx/html, HEALTHCHECK gọi http://localhost:8080/ bằng wget.

2. frontend/nginx.conf:
   - listen 8080; location / : try_files $uri $uri/ /index.html (định tuyến phía client)
   - location /api/ : proxy_pass http://backend:8000; proxy_http_version 1.1; proxy_set_header Connection ""; proxy_buffering off; proxy_cache off; proxy_read_timeout 300s; chuyển tiếp X-Ma-Yeu-Cau và X-Forwarded-For
   - location = /health và = /ready chuyển tới backend
   - header bảo mật: Content-Security-Policy chỉ cho phép 'self' (default-src 'self'; connect-src 'self'; font-src 'self'; img-src 'self' data:), X-Content-Type-Options nosniff, Referrer-Policy no-referrer, X-Frame-Options DENY
   - gzip cho tài nguyên tĩnh, KHÔNG gzip text/event-stream
   Chú thích tiếng Việt ở proxy_buffering off: thiếu dòng này nginx gom mảnh lại rồi trả một lần - nguyên nhân phổ biến nhất khiến phát theo dòng chạy tốt trên máy cá nhân nhưng hỏng khi lên máy chủ.

3. docker-compose.yml: thay dịch vụ frontend tạm ở PROMPT 2 bằng build từ frontend/Dockerfile, cổng 8080:8080, depends_on backend điều kiện service_healthy. Đây là sửa dịch vụ đã có, không thêm dịch vụ mới. Ghi chú: ở môi trường prod backend không cần mở cổng 8000 ra ngoài, giữ 8000 cho dev.

4. Kiểm thử đầu cuối Playwright trong frontend/e2e/ (cài @playwright/test làm devDependency - được phép; chạy npx playwright install chromium một lần), baseURL http://localhost:8080, chạy trên compose thật với XAC_THUC_GIA=true. Đặt thời gian chờ mỗi kịch bản 120 giây vì model local trên GPU 8 GB có thể mất 10–30 giây nạp lần đầu:
   - gửi câu hỏi, thấy chữ hiện dần (ít nhất 2 lần cập nhật nội dung trước khi xong), có huy hiệu và nhãn AI
   - bấm Dừng giữa chừng, phần chữ đã hiện giữ nguyên
   - tải lại trang, hội thoại vẫn trong danh sách, mở lại thấy đủ lượt
   - xoá hội thoại qua hộp thoại xác nhận
   - khung nhìn 375x812 dùng được: drawer mở được, ô nhập không bị che
   - không có yêu cầu mạng nào tới máy chủ khác localhost (bắt sự kiện request của trang)

5. Cập nhật README.md: lệnh chạy một lần, địa chỉ http://localhost:8080, cách chạy kiểm thử đơn vị và đầu cuối. Cập nhật CHANGELOG.md các Giai đoạn 1–4 và mục "Không làm ở giai đoạn hiện tại" trong AGENTS.md (bỏ các việc đã làm).

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. docker compose up -d --build && docker compose ps -> kỳ vọng: db, backend, frontend đều healthy
2. curl -N -X POST localhost:8080/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}' -> kỳ vọng: chữ hiện DẦN qua nginx, không dồn một lần
3. curl -sI localhost:8080 | grep -i content-security-policy -> kỳ vọng: có header, chỉ 'self'
4. cd frontend && npx playwright install chromium && npx playwright test -> kỳ vọng: 6 kịch bản qua
5. grep -n "proxy_buffering off" frontend/nginx.conf -> kỳ vọng: có, trong location /api/
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- frontend/Dockerfile hai tầng, nginx không chạy bằng root, nghe cổng 8080.
- nginx.conf có proxy_buffering off cho /api/, CSP chỉ 'self', không gzip SSE.
- docker-compose vẫn đúng ba dịch vụ, frontend build từ mã Angular.
- Sáu kịch bản Playwright qua, gồm kịch bản không gọi ra ngoài localhost.
- README, CHANGELOG, AGENTS.md đã cập nhật.

**Tự đánh giá**

```danhgia
docker compose up -d --build && docker compose ps               # kỳ vọng: 3 dịch vụ healthy
curl -N -X POST localhost:8080/api/v1/chat/stream -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}'   # kỳ vọng: chữ hiện dần
curl -sI localhost:8080 | grep -i content-security-policy        # kỳ vọng: 'self'
cd frontend && npx playwright install chromium && npx playwright test   # kỳ vọng: 6 passed
grep -n "proxy_buffering off" frontend/nginx.conf                # kỳ vọng: có
```

```batbuoc
Đến đây là mốc chatbot dùng được, nhưng CHƯA được mở cho người dùng thật: chưa có đăng nhập và hạn mức. XAC_THUC_GIA=true chỉ dùng trong mạng thử nghiệm; mở ra mạng nội bộ chung phải chờ Giai đoạn 5.
```

```meo
Hãy nhờ một cán bộ, công nhân viên chưa từng thấy dự án dùng thử mười phút và ghi lại chỗ họ vấp. Mười phút đó có giá trị hơn một ngày tự kiểm.
```
