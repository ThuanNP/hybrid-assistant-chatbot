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

## 6. Giao diện lập trình ứng dụng (API)

Toàn bộ các endpoint nghiệp vụ được đặt dưới tiền tố `/api/v1/` và yêu cầu xác thực người dùng.
Hai endpoint giám sát sức khoẻ hệ thống (`/health` và `/ready`) được đặt trực tiếp tại gốc.

### 6.1. Danh sách các endpoint

| Phương thức | Đường dẫn | Mô tả chức năng | Xác thực |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Tiến trình còn chạy, trả `healthy` và số phiên bản | Không |
| `GET` | `/ready` | Sẵn sàng phục vụ: trả `ready` (200) hoặc `not_ready` (503) | Không |
| `POST` | `/api/v1/chat/stream` | Trò chuyện hội thoại phát theo dòng (Server-Sent Events) | Bắt buộc |
| `POST` | `/api/v1/chat` | Trò chuyện không phát theo dòng cho tích hợp máy với máy | Bắt buộc |
| `GET` | `/api/v1/hoi-thoai` | Danh sách hội thoại của người dùng hiện tại (phân trang) | Bắt buộc |
| `GET` | `/api/v1/hoi-thoai/{id}` | Chi tiết toàn bộ các lượt tin nhắn trong cuộc hội thoại | Bắt buộc |
| `DELETE` | `/api/v1/hoi-thoai/{id}` | Xoá mềm cuộc hội thoại của người dùng hiện tại | Bắt buộc |
| `GET` | `/api/v1/chi-phi` | Báo cáo chi phí tiêu thụ token và tỷ lệ định tuyến | Bắt buộc |
| `GET` | `/api/v1/models` | Cấu hình mô hình, hồ sơ GPU, bậc local và tầng đám mây | Bắt buộc |
| `GET` | `/api/v1/hang-doi/tinh-trang` | Trạng thái tức thời của bộ điều phối hàng đợi local | Bắt buộc |
| `GET` | `/api/v1/ngu-canh/tinh-trang` | Hiện trạng ngữ cảnh cấu hình, thực tế và ngân sách token | Bắt buộc |

### 6.2. Cấu trúc phản hồi lỗi chuẩn

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

### 6.3. Bảng mã lỗi hệ thống

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
| `LOI_HE_THONG` | 500 | Lỗi hệ thống không xác định |
