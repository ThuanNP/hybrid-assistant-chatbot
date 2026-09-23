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

- **Frontend Web** (người dùng trong mạng nội bộ truy cập cổng này): <http://localhost:8080>
- **Backend API** (chỉ mở ở `127.0.0.1` trên chính máy chủ, tắt khi `MOI_TRUONG=prod`):
  <http://localhost:8000/docs>

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

Sau khi cài, chạy công cụ Python từ thư mục `backend/` bằng `uv run --frozen` (quy tắc kỹ thuật 13
trong `AGENTS.md`), ví dụ `uv run --frozen pytest -q`, `uv run --frozen pyright app`,
`uv run --frozen alembic upgrade head`; `uv` dùng lại `backend/.venv` đã cài ở trên.

Để chuẩn bị môi trường frontend và chạy kiểm thử:

```bash
cd frontend
npm ci
npm test                            # Chạy kiểm thử đơn vị frontend (Vitest)
npx playwright install chromium     # Tải trình duyệt cho kiểm thử E2E (chỉ cần chạy một lần)
E2E_MAT_KHAU='<mật khẩu>' npx playwright test   # Kiểm thử đầu cuối trên hệ thống compose đang chạy
```

Kiểm thử đầu cuối đăng nhập bằng `E2E_EMAIL` (mặc định `nv01@vidu.com`) và `E2E_MAT_KHAU`;
không ghi mật khẩu vào mã.

Giao diện theo chuẩn thiết kế `DESIGN.md`. Bản thiết kế tham chiếu bố cục đã duyệt là dự án
Google Stitch "Trợ lý AI nội bộ · v2"
(<https://stitch.withgoogle.com/projects/13299602320821438075>), gồm bốn màn hình Trang chủ, Cuộc
trò chuyện mới, màn hình đang trò chuyện và Lịch sử hội thoại. Khi bản thiết kế khác `DESIGN.md`
về màu, phông chữ hoặc khoảng cách thì theo `DESIGN.md`.

## 5. Kết nối an toàn bộ chạy cục bộ và kiểm tra trước khi chạy

### 5.1. Bối cảnh và vì sao điều này quan trọng

Máy chủ Ollama mặc định **không có cơ chế xác thực danh tính**.
API của Ollama không chỉ cung cấp tính năng sinh văn bản phục vụ suy luận
mà còn cung cấp các quyền quản trị mô hình:
tải model mới (`/api/pull`), tạo model (`/api/create`),
sao chép (`/api/copy`), đẩy lên registry (`/api/push`),
và xoá model (`/api/delete`).

Mặc định Ollama chỉ lắng nghe ở giao diện vòng lặp `127.0.0.1` nên an toàn.
Rủi ro phát sinh khi mở rộng để container hoặc máy trạm khác truy cập:

- Kẻ tấn công hoặc người ngoài mạng có thể chiếm dụng GPU máy chủ miễn phí.
- Tải các model tuỳ ý về máy chủ làm lấp đầy dung lượng ổ đĩa.
- Xoá trực tiếp các model đang phục vụ cán bộ, công nhân viên ngành điện.
- Tương tự đối với LM Studio khi bật tuỳ chọn "Serve on Local Network".

### 5.2. Ba cách nối an toàn (xếp theo thứ tự ưu tiên)

#### Cách A - GIỮ 127.0.0.1 (Ưu tiên số 1, mặc định của Ollama)

- **Windows/macOS với Docker Desktop** (phần cứng thử nghiệm):
  Không cần đổi biến `OLLAMA_HOST`. Container gọi qua `http://host.docker.internal:11434`,
  Docker Desktop tự chuyển tiếp an toàn tới loopback của máy chủ mà không mở ra LAN.
- **Linux (Docker Engine)**:
  Backend dùng `network_mode: host` trong Docker Compose hoặc chạy backend
  trực tiếp ngoài container.

#### Cách B - Chỉ dùng trên máy chủ Linux (Ưu tiên số 2)

- Bind dịch vụ Ollama vào địa chỉ cầu nối Docker (thường là `172.17.0.1`,
  xem bằng lệnh `ip addr show docker0`), tuyệt đối **không** bind vào `0.0.0.0`.
- Thiết lập luật tường lửa `ufw` chỉ cho phép dải mạng Docker truy cập cổng 11434:

```bash
sudo ufw allow in on docker0 to 172.17.0.1 port 11434 proto tcp
```

- Trên Windows không cần cách này; nếu bắt buộc phải cho máy khác trong LAN gọi,
  dùng PowerShell quản trị tạo luật hạn chế:

```powershell
New-NetFirewallRule -DisplayName "Ollama LAN han che" -Direction Inbound `
  -Protocol TCP -LocalPort 11434 -RemoteAddress <dải IP được phép> -Action Allow
New-NetFirewallRule -DisplayName "Ollama LAN chan tat ca" -Direction Inbound `
  -Protocol TCP -LocalPort 11434 -Action Block
```

#### Cách C - Buộc phải mở rộng hơn (Ưu tiên số 3)

- Đặt máy chủ Nginx phía trước làm lá chắn, bật xác thực cơ bản (Basic Auth) hoặc mTLS.
- **CHẶN** triệt để các đường dẫn quản trị nguy hiểm:
  `/api/pull`, `/api/create`, `/api/delete`, `/api/push`, `/api/copy`.
- **CHỈ CHO PHÉP** các đường dẫn phục vụ suy luận và tra cứu trạng thái:
  `/api/chat`, `/v1/chat/completions`, `/v1/embeddings`,
  `/api/embed`, `/api/tags`, `/api/ps`, `/api/show`.
- Tham khảo tệp cấu hình mẫu tại [`deploy/nginx-ollama.conf`](deploy/nginx-ollama.conf).

### 5.3. Kiểm tra chẩn đoán trước khi khởi chạy

Trước khi khởi động hệ thống, thực hiện kiểm tra chẩn đoán bộ chạy mô hình cục bộ
và các nhà cung cấp đám mây (chạy từ thư mục `backend/`):

```bash
# Kiểm tra bộ chạy mô hình cục bộ (Ollama / LM Studio)
uv run --frozen python ../scripts/kiem_tra_bo_chay.py

# Kiểm tra kết nối tới các nhà cung cấp đám mây qua LiteLLM
uv run --frozen python ../scripts/kiem_tra_nha_cung_cap.py
```

Để kiểm tra nguy cơ phơi lộ cổng 11434 ra mạng ngoài:

- **Trên máy chủ**: Chạy từ một máy tính khác trong mạng nội bộ:

```bash
python scripts/kiem_tra_phoi_lo.py --dia-chi http://<IP-LAN>:11434
```

- **Trên phần cứng thử nghiệm** (tự động phát hiện IP LAN):

```bash
cd backend && uv run --frozen python ../scripts/kiem_tra_phoi_lo.py --tu-dong-ip
```

- **Phép thử bổ sung từ container** (yêu cầu kết nối phải thất bại):

```bash
docker run --rm curlimages/curl -s -m 3 http://<IP-LAN>:11434/api/tags
```

## 6. Giao diện lập trình ứng dụng (API)

Toàn bộ các endpoint nghiệp vụ được đặt dưới tiền tố `/api/v1/` và yêu cầu xác thực người dùng.
Hai endpoint giám sát sức khoẻ hệ thống (`/health` và `/ready`) được đặt trực tiếp tại gốc.

### 6.1. Danh sách các endpoint

| Phương thức | Đường dẫn | Mô tả chức năng | Xác thực |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Tiến trình còn chạy, trả `song` và số phiên bản | Không |
| `GET` | `/ready` | Sẵn sàng phục vụ: trả `san_sang` (200) hoặc `chua_san_sang` (503) | Không |
| `POST` | `/api/v1/chat/stream` | Trò chuyện hội thoại phát theo dòng (Server-Sent Events) | Bắt buộc |
| `POST` | `/api/v1/chat` | Trò chuyện không phát theo dòng cho tích hợp máy với máy | Bắt buộc |
| `GET` | `/api/v1/hoi-thoai` | Danh sách hội thoại của người dùng hiện tại, lọc và phân trang (mục 6.2) | Bắt buộc |
| `GET` | `/api/v1/hoi-thoai/{id}` | Chi tiết toàn bộ các lượt tin nhắn trong cuộc hội thoại | Bắt buộc |
| `DELETE` | `/api/v1/hoi-thoai/{id}` | Xoá mềm cuộc hội thoại của người dùng hiện tại | Bắt buộc |
| `GET` | `/api/v1/chi-phi` | Chi phí, tỷ lệ định tuyến, số câu hỏi hôm nay và ngưỡng cảnh báo | Bắt buộc |
| `GET` | `/api/v1/models` | Cấu hình mô hình, hồ sơ GPU, bậc local và tầng đám mây | Bắt buộc |
| `GET` | `/api/v1/hang-doi/tinh-trang` | Trạng thái tức thời của bộ điều phối hàng đợi local | Bắt buộc |
| `GET` | `/api/v1/ngu-canh/tinh-trang` | Hiện trạng ngữ cảnh cấu hình, thực tế và ngân sách token | Bắt buộc |
| `GET` | `/api/v1/huong-dan` | Nội dung tài liệu hướng dẫn sử dụng Markdown | Bắt buộc |
| `GET` | `/api/v1/cau-hoi-thuong-gap` | Danh sách 20 câu hỏi thường gặp phân theo 5 nhóm nghiệp vụ | Bắt buộc |

### 6.2. Tham số và trường dữ liệu chính

`GET /api/v1/hoi-thoai` nhận các tham số tuỳ chọn sau; `tong_so` là số hội thoại khớp bộ lọc,
mỗi mục kèm `so_luot` (số câu hỏi):

| Tham số | Kiểu | Ý nghĩa |
| :--- | :--- | :--- |
| `trang`, `kich_thuoc` | số nguyên | Trang (từ 1) và số mục mỗi trang (1–100, mặc định 20) |
| `tu_khoa` | chuỗi | Tìm trong tiêu đề, không phân biệt hoa thường |
| `tu_ngay`, `den_ngay` | `YYYY-MM-DD` | Lọc theo ngày cập nhật (giờ Việt Nam), `den_ngay` lấy trọn cả ngày |
| `sap_xep` | chuỗi | `moi_nhat` (mặc định), `cu_nhat`, `ten_tang`, `ten_giam` |

- Sự kiện SSE `xong` và phản hồi `POST /api/v1/chat` có thêm `ma_yeu_cau` và `ha_cap`.
  `ha_cap` bằng `true` khi tầng phục vụ khác tầng đầu của chuỗi định tuyến, hoặc khi câu trả lời
  do bậc `nho` sinh ra.
- Mỗi lượt trong `GET /api/v1/hoi-thoai/{id}` trả thêm `toc_do_tok_s`, `do_tre_ms`,
  `da_cat_ngu_canh`, `so_luot_bi_cat`, `ma_yeu_cau`, `ha_cap`. Lượt trợ lý có thêm `nhan_ai`.
- `GET /api/v1/chi-phi`:
  - Mọi trường `ty_le_*` là phân số 0–1; riêng `phan_tram_da_dung` theo thang 0–100.
  - `so_cau_hoi_hom_nay`, `so_cau_hoi_noi_bo`, `so_cau_hoi_dam_may` đếm câu hỏi và câu trả lời
    trong ngày theo giờ Việt Nam, không tính lời gọi nền đặt tiêu đề.
  - `nguong_canh_bao_ngan_sach`, `nguong_ty_le_roi_tang` lấy từ `config/models.yaml`.

### 6.3. Cấu trúc phản hồi lỗi chuẩn

Mọi phản hồi lỗi dùng chung một cấu trúc JSON với thông điệp chuẩn; chi tiết kỹ thuật
(vết ngăn xếp, lỗi thô của bộ chạy, tên thành phần) chỉ ghi vào nhật ký:

```json
{
  "loi": {
    "ma": "KHONG_TIM_THAY",
    "thong_diep": "Không tìm thấy cuộc hội thoại.",
    "ma_yeu_cau": "a1b2c3d4e5f6"
  }
}
```

Mã định danh `ma_yeu_cau` (12 ký tự) được đồng bộ giữa header phản hồi `X-Ma-Yeu-Cau`,
nội dung lỗi JSON, nhật ký vận hành và bản ghi cơ sở dữ liệu.

### 6.4. Bảng mã lỗi hệ thống

| Mã lỗi | HTTP | Ý nghĩa và mô tả |
| :--- | :--- | :--- |
| `HANG_DOI_DAY` | 503 | Hàng đợi local đã đầy |
| `QUA_HAN` | 504 | Quá thời gian chờ |
| `NGU_CANH_QUA_DAI` | 422 | Tin nhắn vượt ngân sách ngữ cảnh |
| `BO_CHAY_KHONG_PHAN_HOI` | 503 | Bộ chạy local không phản hồi |
| `DICH_VU_TAM_NGUNG` | 503 | Dịch vụ tạm gián đoạn |
| `HET_CHUOI_DU_PHONG` | 503 | Mọi tầng trong chuỗi dự phòng đều lỗi |
| `VUOT_NGAN_SACH` | 503 | Vượt ngân sách đám mây trong ngày |
| `VUOT_HAN_MUC` | 429 | Gửi yêu cầu quá tần suất cho phép |
| `KHONG_CO_QUYEN` | 403 | Không có quyền truy cập |
| `CHUA_XAC_THUC` | 401 | Chưa đăng nhập hoặc phiên hết hạn |
| `DAU_VAO_KHONG_HOP_LE` | 422 | Dữ liệu đầu vào không hợp lệ |
| `NOI_DUNG_BI_CHAN` | 422 | Nội dung vi phạm chính sách kiểm duyệt |
| `KHONG_TIM_THAY` | 404 | Không tìm thấy dữ liệu |
| `LOI_DONG` | 200 | Chỉ có trong sự kiện SSE `loi`: luồng ngắt sau khi đã phát, kèm `phan_da_nhan` |
| `LOI_HE_THONG` | 500 | Lỗi hệ thống không xác định |

Lỗi xảy ra sau khi luồng SSE đã mở được trả bằng sự kiện `loi` với HTTP 200. CORS mở hai header
`X-Ma-Yeu-Cau` và `Retry-After` để giao diện khác nguồn đọc được.

## 7. Đánh giá chất lượng các tầng mô hình (Evaluation Suite)

Hệ thống tích hợp bộ đánh giá tự động hai lớp (lớp tất định và lớp mô hình cục bộ bậc 1)
đối chiếu với bộ 40 câu hỏi nghiệp vụ ngành điện lực (`eval/bo_cau_hoi.yaml`):

```bash
docker compose exec backend python -m app.eval.runner --tang all --lan 3
```

- `--tang` nhận `local1`, `local2`, `1`, `2`, `3`, `4`, `all` hoặc danh sách cách nhau bằng dấu
  phẩy; chạy tuần tự từng tầng, mỗi câu `--lan` lần, ngữ cảnh dựng giống luồng chat thật.
- Tuân thủ Quy tắc tuyệt đối 2: Câu hỏi có nhãn `nhay_cam: true` chỉ chạy trên các tầng local
  (`local1`, `local2`) và tự động ghi nhận `BO_QUA` khi chạy trên các tầng đám mây.
- Lượt bị giới hạn tần suất ghi `GIỚI HẠN`, không tính trượt. Tầng 2 (`openrouter_free`) chỉ để
  tham khảo, không đưa vào danh sách bất đồng và không so với lần chạy trước.
- Bảng in ra có mỗi cột là một tầng; các hàng gồm tỷ lệ đạt theo từng loại câu hỏi, tỷ lệ chung,
  độ trễ p50/p95, tok/s, chi phí cả bộ, độ dài trung bình, chênh lệch so với lần trước và kết luận
  ngưỡng (`cai_dat_chung.nguong_dat_danh_gia` trong `config/models.yaml`).
- Kết quả lưu tại `ket_qua_eval/<ngày>_<tầng>.json`.

## 8. Kiểm tra toàn diện trước khi mở vận hành (Go-Live Checklist)

Trước khi mở hệ thống cho người dùng, chạy danh mục kiểm tra theo Phụ lục 4 (cần hệ thống compose
đang chạy, Ollama đang chạy và kết quả bộ đánh giá gần nhất trong `ket_qua_eval/`):

```bash
cd backend
uv run --frozen python ../scripts/kiem_tra_truoc_khi_mo.py
```

Kịch bản in bảng theo đúng số dòng của Phụ lục 4:

- Dòng Máy 1-16, 19, 25 (Giai đoạn 1-5): mỗi dòng dùng lại kiểm thử hoặc kịch bản chẩn đoán của
  tính năng tương ứng (`quet_bi_mat.py`, `kiem_tra_bo_chay.py`, `kiem_tra_phoi_lo.py`, các tệp
  `tests/test_*.py`) và đọc kết quả bộ đánh giá lần gần nhất cho dòng 16.
- Dòng 17, 18, 20 in `CHƯA ÁP DỤNG` cho tới khi Giai đoạn 6, 7 bổ sung.
- Dòng Người 21-24 in `CHỜ XÁC NHẬN`, không tính vào mã thoát.

Mã thoát 0 khi mọi dòng Máy đang áp dụng đều đạt, 1 khi còn dòng chưa đạt.
