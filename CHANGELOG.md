# Nhật ký thay đổi (Changelog)

Mọi thay đổi đáng chú ý của dự án sẽ được ghi lại trong tệp này.
Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/)
và tuân thủ [Semantic Versioning](https://semver.org/lang/vi/).

## [Chưa phát hành]

## [0.4.0] - 2026-09-23

### Thêm

- Đóng gói frontend bằng Dockerfile hai tầng: tầng dựng Node.js 22 LTS và tầng chạy Nginx
  không đặc quyền (`nginxinc/nginx-unprivileged:alpine`) lắng nghe cổng 8080.
- Cấu hình Nginx (`frontend/nginx.conf`): định tuyến client-side cho SPA, reverse proxy API
  FastAPI với `proxy_buffering off` cho SSE, thiết lập đầy đủ tiêu đề bảo mật CSP,
  X-Content-Type-Options, Referrer-Policy, X-Frame-Options và nén gzip cho tài nguyên tĩnh.
- Bộ kiểm thử đầu cuối Playwright trong `frontend/e2e/chat.e2e.ts` với 6 kịch bản toàn diện:
  truyền phát dòng, dừng giữa chừng, lưu và phục hồi lịch sử, xoá hội thoại qua hộp thoại
  xác nhận, phản hồi giao diện di động 375x812 và kiểm tra an toàn mạng/CSP; kịch bản lịch sử và
  kịch bản xoá tự tạo dữ liệu kiểm thử riêng.
- `GET /api/v1/hang-doi/tinh-trang` trả thêm trường `do_dai_toi_da` (sức chứa tối đa của hàng đợi,
  lấy từ cấu hình); thay đổi bổ sung, tương thích ngược.
- `GET /api/v1/hoi-thoai` trả thêm trường `so_luot` cho mỗi hội thoại (số câu hỏi của người dùng,
  đếm gộp trong một truy vấn); thay đổi bổ sung, tương thích ngược.
- Breadcrumb quá dài tự gộp các mục giữa thành `…`, luôn giữ `Trang chủ` và mục hiện tại; trên di
  động thanh đầu trang chỉ hiện tiêu đề trang thay cho breadcrumb.
- Workspace Angular 22 (standalone, signals, zoneless), app shell theo DESIGN.md, phông tự host;
  `api.service`, `sse.service` đọc luồng SSE bằng `fetch` kèm kiểm thử đơn vị; ba màn Trang chủ,
  Trò chuyện, Lịch sử hội thoại và tác vụ nhanh dùng chung.
- `GET /api/v1/hoi-thoai` nhận tham số `tu_khoa`, `tu_ngay`, `den_ngay`, `sap_xep`; `tong_so` đếm
  theo bộ lọc, ngày tính theo giờ Việt Nam.
- Sự kiện SSE `xong` và phản hồi `POST /api/v1/chat` có thêm `ma_yeu_cau` và `ha_cap`.
- Mỗi lượt trong `GET /api/v1/hoi-thoai/{id}` trả thêm `toc_do_tok_s`, `do_tre_ms`,
  `da_cat_ngu_canh`, `so_luot_bi_cat`, `ma_yeu_cau`, `ha_cap`; lượt trợ lý có thêm `nhan_ai`.
- `GET /api/v1/chi-phi` trả thêm `so_cau_hoi_hom_nay`, `so_cau_hoi_noi_bo`, `so_cau_hoi_dam_may`,
  `nguong_canh_bao_ngan_sach`, `nguong_ty_le_roi_tang`.
- Migration `002_luot_goi_roi_tang`: bảng `luot_goi` thêm `roi_tang`, `ly_do_that_bai_tang_dau`
  (chỉ lưu loại lỗi) và `muc_dich` (`chat` hoặc `tieu_de`).
- Mã lỗi `LOI_DONG` vào bảng mã lỗi; CORS mở header `X-Ma-Yeu-Cau`, `Retry-After`.

### Thay đổi

- Dịch vụ frontend trong `docker-compose.yml` chuyển sang build từ `./frontend/Dockerfile`,
  lắng nghe cổng 8080:8080 và phụ thuộc backend ở trạng thái healthy.
- Tắt `optimization.styles.inlineCritical` trong `frontend/angular.json` để loại bỏ thuộc tính
  `onload` nội tuyến trên thẻ style link, tuân thủ chặt chẽ chính sách bảo mật CSP `script-src 'self'`.
- Bổ sung hướng dẫn chạy kiểm thử đơn vị frontend và kiểm thử đầu cuối Playwright, cùng bản thiết
  kế tham chiếu trên Google Stitch, vào `README.md`.
- Màn Lịch sử hội thoại tìm, lọc và sắp xếp qua máy chủ; kết quả đúng ngay từ trang đầu, không cần
  tải hết các trang.
- Huy hiệu mô hình chuyển màu cảnh báo theo cờ `ha_cap` của máy chủ (đúng cả với chế độ ưu tiên
  đám mây); mở lại hội thoại vẫn giữ huy hiệu, nhãn AI và dòng lược bớt.
- KPI `Lượt hỏi hôm nay` lấy số câu hỏi do máy chủ đếm; ngưỡng thông báo lấy từ máy chủ.
- `GET /api/v1/chi-phi`: mọi trường `ty_le_*` là phân số 0–1; "hôm nay" và ngân sách ngày tính theo
  giờ Việt Nam; lời gọi nền đặt tiêu đề không tính vào tỷ lệ định tuyến.
- `AGENTS.md`: quy tắc kỹ thuật đánh số 5–13 nối tiếp bốn quy tắc tuyệt đối; bổ sung quy định về
  thông tin được đưa vào tệp commit.

- Màn Lịch sử hội thoại: nút xoá hội thoại (thùng rác 28px) luôn hiển thị ở cuối mỗi dòng thay vì
  chỉ hiện khi rê chuột, dùng được trên màn hình cảm ứng; DESIGN.md mục 6.4a bổ sung quy định dòng
  hội thoại.
- Màn Lịch sử hội thoại: `Từ ngày`, `Đến ngày` mặc định `null` (không giới hạn, lấy toàn bộ lịch
  sử); mỗi ô ngày có nút `×` riêng đưa ô về `null`.
- Màn Lịch sử hội thoại: dòng hội thoại đổi sang danh sách phẳng theo bản thiết kế Stitch, dòng phụ
  dạng `8 lượt · cập nhật 14:30`.
- Bỏ hiển thị tổng số hội thoại: dòng mô tả màn Lịch sử là câu hướng dẫn cố định, chỉ ghi số kết quả
  khi đang tìm hoặc lọc; sidebar ghi `Xem tất cả`; cuối danh sách ghi `Đã hiển thị toàn bộ`.
- Màn Lịch sử hội thoại chỉ còn ba nhóm thời gian `Hôm nay`, `Hôm qua`, `Cũ hơn` (bỏ nhóm
  `7 ngày qua`, gộp vào `Cũ hơn`).

### Sửa lỗi

- Bản build production không chứa thuộc tính `onload` nội tuyến, tương thích CSP
  `script-src 'self'`.
- Tỷ lệ rơi tầng được tính và cảnh báo đúng khi dùng kho PostgreSQL; lượt hết chuỗi cũng được ghi.
- Siết kiểm tra quyền truy cập hội thoại khi phát theo dòng; mã hội thoại không hợp lệ trả
  `KHONG_TIM_THAY`, máy chủ tự cấp mã khi tạo hội thoại mới; `noi_dung` không được rỗng.
- Không lưu nội dung bị móc kiểm duyệt từ chối; kiểm duyệt đầu vào chạy trước khi tạo hội thoại.
- Lời gọi nhà cung cấp đám mây chỉ nhận tham số sinh văn bản; tham số nội bộ của router được giữ
  lại trong router.
- Nhãn AI ghi giờ Việt Nam; nhật ký không ghi tiêu đề hội thoại tự đặt.

## [0.3.0] - 2026-09-23

### Thêm

- Hệ thống định tuyến API FastAPI hoàn thiện tại `backend/app/main.py`:
  - `POST /api/v1/chat/stream`: phát phản hồi hội thoại theo dòng (SSE) qua chuỗi định tuyến lai.
  - `POST /api/v1/chat`: hội thoại không phát dòng cho tích hợp máy - máy, trả đầy đủ siêu dữ
    liệu kỹ thuật (nguồn, tầng, model, token, chi phí, độ trễ, tốc độ) và `nhan_ai`.
  - `GET /api/v1/hoi-thoai`: danh sách hội thoại của người dùng hiện tại có phân trang, sắp
    theo thời gian cập nhật giảm dần.
  - `GET /api/v1/hoi-thoai/{id}`: xem chi tiết toàn bộ các lượt tin nhắn trong cuộc hội thoại.
  - `DELETE /api/v1/hoi-thoai/{id}`: xoá mềm cuộc hội thoại của người dùng hiện tại.
  - `GET /api/v1/chi-phi`: báo cáo tổng hợp chi phí và tỷ lệ định tuyến sử dụng mô hình.
  - `GET /api/v1/models`: thông tin chế độ định tuyến, hồ sơ GPU, 2 bậc local và 4 tầng đám mây
    không để lộ khoá API.
  - `GET /api/v1/hang-doi/tinh-trang`: hiện trạng bộ điều phối hàng đợi local tức thời.
  - `GET /api/v1/ngu-canh/tinh-trang`: hiện trạng cửa sổ ngữ cảnh cấu hình, thực tế và ngân sách.
  - `GET /health`: kiểm tra tiến trình sống cực nhanh, không truy cập CSDL hay mô hình.
  - `GET /ready`: kiểm tra sẵn sàng dịch vụ (CSDL và bộ chạy local hoặc ít nhất một tầng đám mây).
- Chuẩn hóa mã lỗi và bộ bắt lỗi toàn cục trong `backend/app/core/loi.py`: lớp `LoiUngDung` kế thừa
  `LoiHeThong`, ánh xạ toàn bộ mã lỗi chuẩn hóa sang cấu trúc JSON `{"loi": {"ma", "thong_diep",
  "ma_yeu_cau"}}`, thông điệp tiếng Việt dễ hiểu và tuyệt đối không làm lộ `Traceback` ra ngoài.
- Quản lý mã yêu cầu `ma_yeu_cau` 12 ký tự xuyên suốt trong `backend/app/core/nhat_ky.py` và
  middleware HTTP tại `main.py`, đồng bộ qua header `X-Ma-Yeu-Cau`, `contextvars`, nhật ký và
  bảng CSDL `luot`.
- Móc kiểm duyệt nội dung trong `backend/app/core/bao_mat.py`: `KetQuaKiemDuyet`,
  `kiem_duyet_dau_vao` (trước khi dựng ngữ cảnh) và `kiem_duyet_dau_ra` (trước khi lưu CSDL và trả
  về).
- Quản lý hội thoại và cơ sở dữ liệu: migration Alembic 4 bảng (`nguoi_dung`, `hoi_thoai`, `luot`,
  `luot_goi`), `app/chat/hoi_thoai.py` hỗ trợ tạo mới, lưu cặp lượt trong một giao dịch, xoá mềm,
  đọc danh sách phân trang, đọc phiên bản prompt và tự đặt tiêu đề chạy nền bậc nhỏ local.
- Bộ kiểm thử tự động toàn diện `backend/tests/test_api.py`, `backend/tests/test_hoi_thoai.py`,
  `backend/tests/test_stream.py`.
- Mục 6 "Giao diện lập trình ứng dụng (API)" trong `README.md` mô tả toàn bộ endpoints và bảng mã
  lỗi.

### Thay đổi

- Nâng phiên bản `backend/pyproject.toml` lên `0.3.0` đồng bộ toàn hệ thống.
- Endpoint `POST /api/v1/chat/stream` đọc `ma_yeu_cau` từ `contextvars` thay vì tự sinh mã mới để
  đảm bảo tính nhất quán trên toàn chu trình xử lý.
- Gắn hai móc kiểm duyệt vào luồng phát dòng SSE và luồng chat đồng bộ.
- Cấu hình CORS đọc `CORS_ORIGINS` và cấm ký tự `*` khi môi trường là `prod`.

### Sửa lỗi

- Khắc phục nguy cơ rò rỉ vết ngăn xếp (`Traceback`) ra ngoài bằng bộ bắt lỗi tập trung
  `dang_ky_bo_bat_loi`.
- Đảm bảo kiểm tra sẵn sàng `/ready` không bao giờ gọi hàm sinh văn bản của mô hình và bọc
  `asyncio.wait_for` 2 giây ngăn chặn treo tiến trình kiểm tra.
- Truy cập hoặc thao tác trên hội thoại của người khác trả 404.

## [0.2.0] - 2026-09-23

### Thêm

- Điều phối hàng đợi local `backend/app/hang_doi/dieu_phoi.py`: giới hạn số lời gọi đồng thời
  qua `asyncio.Semaphore` lấy từ `cau_hinh.so_luong_dong_thoi`, kiểm soát độ dài hàng đợi tối đa
  `do_dai_hang_doi_toi_da` (mặc định 20), tính vị trí và ước lượng thời gian chờ theo trung vị
  của 20 yêu cầu local gần nhất, cung cấp hàm `trang_thai()` báo cáo vận hành hàng đợi.
- Quản lý chi phí và ngân sách `backend/app/llm/chi_phi.py`: ước tính chi phí theo bảng giá
  `models.yaml`, kho lưu trữ `KhoLuotGoi` với hiện thực bộ nhớ `KhoLuotGoiBoNho` ghi nhận 14
  trường chỉ số theo Quy tắc kỹ thuật 7, kiểm tra ngân sách ngày và ngưỡng cảnh báo 80%, theo dõi
  tỷ lệ rơi tầng trong 1 giờ gần nhất kèm lý do hỏng tầng đầu, hàm tổng hợp `bao_cao_chi_phi()`.
- Lớp ngoại lệ nghiệp vụ `LoiHangDoiDay` (mã `HANG_DOI_DAY`) và `LoiVuotNganSach` (mã
  `VUOT_NGAN_SACH`) trong `backend/app/core/loi.py`.
- Mảnh `ManhPhatRa` loại `"hang_doi"` trong `router.py` để phát thông tin vị trí và thời gian
  ước lượng ngay khi yêu cầu vào hàng đợi.
- Bộ chạy local `backend/app/llm/bo_chay_local.py`: giao diện `BoChay` cho Ollama và
  LM Studio, hạ cấp bậc chinh sang bậc nho, hâm nóng bậc 1, đọc ngữ cảnh thực tế.
- `backend/app/main.py` tối giản: `/health` trả `phien_ban`, lifespan chạy nền
  hâm nóng bậc 1 và cảnh báo khi ngữ cảnh thực tế nhỏ hơn `num_ctx` cấu hình.
- Bộ 7 bài kiểm thử đơn vị tự động tại `backend/tests/test_hang_doi.py` và
  `backend/tests/test_chi_phi.py`.
- Kiểm thử cho `LOAI_BO_CHAY` lạ, thông báo thẻ model sai, tệp `.env` được truyền vào
  và điểm nhập FastAPI.
- Hướng dẫn PowerShell trong `README.md` mục "Chuẩn bị môi trường phát triển".

### Thay đổi

- `backend/app/llm/router.py`: tích hợp hàng đợi `DieuPhoi` và quản lý chi phí `KhoLuotGoi`; kiểm
  tra ngân sách ngày trước mỗi lời gọi tầng đám mây; bỏ qua đám mây khi vượt ngân sách và ném
  `VUOT_NGAN_SACH` nếu không còn local; truyền độ dài hàng đợi thực tế vào `goi_local`.
- `config/models.yaml` và `backend/app/config.py`: bổ sung cấu hình `nguong_canh_bao_ngan_sach`
  (0.80) và `nguong_ty_le_roi_tang` (0.20) vào `cai_dat_chung`.
- Nâng phiên bản `backend/pyproject.toml` lên `0.2.0` đồng bộ toàn hệ thống.
- `config.py` kiểm tra `HO_SO_GPU` theo các khoá khai báo trong `config/models.yaml`; kiểm tra
  thêm `LOAI_BO_CHAY` (`ollama` hoặc `lmstudio`).
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

- Khắc phục nguy cơ treo yêu cầu vô hạn khi hàng đợi local quá tải bằng cơ chế từ chối nhanh
  `HANG_DOI_DAY` khi chuỗi chỉ có local, hoặc tự động chuyển tiếp tầng đám mây tiếp theo.
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
