# Chính sách Bảo mật (Security Policy)

Chính sách bảo mật áp dụng cho hệ thống Trợ lý AI Nội bộ (Hybrid Assistant Chatbot)
dành cho cán bộ, công nhân viên của doanh nghiệp kinh doanh điện năng.

## 1. Phiên bản được hỗ trợ (Supported Versions)

Chỉ các phiên bản chính thức được ghi nhận bên dưới mới nhận được các bản vá bảo mật:

| Phiên bản | Trạng thái hỗ trợ | Ghi chú |
| :--- | :--- | :--- |
| `1.x.x` | :white_check_mark: Có hỗ trợ | Phiên bản hiện tại, được cập nhật bản vá bảo mật |
| `< 1.0.0` | :x: Không hỗ trợ | Phiên bản thử nghiệm cũ |

## 2. Nguyên tắc Bảo vệ Dữ liệu & Quyền riêng tư

Hệ thống được thiết kế theo các quy tắc bảo mật nghiêm ngặt để bảo vệ dữ liệu ngành điện:

### 2.1. Kiểm soát Dữ liệu Nhạy cảm (`NHAY_CAM`)

- Các trường dữ liệu gắn nhãn `NHAY_CAM` (gồm: mã khách hàng, số điện thoại, số công tơ,
  chỉ số công tơ, số CCCD/CMND) và các yêu cầu từ phòng ban cấu hình `chi_local`
  **KHÔNG BAO GIỜ** được gửi ra các mô hình đám mây ngoài doanh nghiệp (Gemini, OpenRouter,
  Claude, OpenAI).
- Khi toàn bộ chuỗi mô hình cục bộ (Ollama / LM Studio) gặp sự cố hoặc vượt quá năng lực,
  hệ thống sẽ phản hồi có kiểm soát, tuyệt đối không âm thầm đẩy dữ liệu nhạy cảm ra ngoài.

### 2.2. Kiểm soát Luồng và Hạ tầng Kết nối

- Mọi lời gọi mô hình AI (cục bộ lẫn đám mây) bắt buộc phải đi qua điểm tập trung duy nhất
  tại `backend/app/llm/router.py` (`goi_mo_hinh()`, `goi_mo_hinh_theo_dong()`). Cấm gọi trực tiếp
  HTTP client (`httpx`) tới các bộ chạy mô hình ở ngoài router này.
- Bộ chạy mô hình cục bộ (Ollama / LM Studio) chỉ được phép lắng nghe tại giao diện vòng lặp
  (`127.0.0.1`) hoặc mạng nội bộ được cô lập của Docker (`docker-compose.yml`).
- Mọi yêu cầu truy cập từ người dùng và hệ thống ngoài đều phải đi qua ứng dụng Backend
  xác thực.

### 2.3. Quản lý Nhật ký & Bảo mật Bí mật

- Mọi thông tin nhạy cảm như khoá API (API Keys), mật khẩu, chuỗi kết nối cơ sở dữ liệu
  phải được cấu hình qua biến môi trường (`.env`), không ghim cứng vào mã nguồn.
- Nội dung chi tiết tin nhắn chat của người dùng **KHÔNG** được ghi vào tập tin nhật ký (logs).
- Mã định danh yêu cầu `ma_yeu_cau` được truyền xuyên suốt mọi dòng nhật ký để truy vết
  mà không làm rò rỉ nội dung nghiệp vụ.
- Định kỳ thực hiện quét mã nguồn bằng công cụ `gitleaks` để ngăn chặn rò rỉ bí mật.

## 3. Quản lý Quyền hạn & Mức độ Tự chủ

- Hệ thống hoạt động theo trần tự chủ **Bậc 2 (L2)**: Chỉ hỗ trợ tra cứu, diễn giải,
  và soạn thảo văn bản.
- Trợ lý AI không có quyền tự động phê duyệt, cập nhật cơ sở dữ liệu trực tiếp hoặc
  thay đổi trạng thái nghiệp vụ mà không có sự xác nhận của nhân sự có thẩm quyền.

## 4. Báo cáo Lỗ hổng Bảo mật (Reporting a Vulnerability)

Chúng tôi đánh giá cao việc phát hiện và báo cáo kịp thời các lỗ hổng bảo mật.

### 4.1. Quy trình Gửi Báo cáo

Nếu phát hiện sự cố hoặc lỗ hổng bảo mật liên quan đến hệ thống, vui lòng **KHÔNG** tạo
Issue công khai trên repository. Hãy gửi thông báo bảo mật riêng tư tới:

- **Bộ phận tiếp nhận**: Ban An toàn thông tin / Phòng CNTT Doanh nghiệp
- **Email**: `security@evn-internal.local` (hoặc email quản trị viên hệ thống)
- **Tiêu đề email**: `[SECURITY VULNERABILITY] <Tóm tắt ngắn gọn sự cố>`

### 4.2. Thông tin Cần Cung cấp

Để giúp chúng tôi xác minh và xử lý nhanh chóng, bài báo cáo nên bao gồm:

1. Mô tả chi tiết loại lỗ hổng (ví dụ: Rò rỉ dữ liệu `NHAY_CAM`, bypass router, SQL Injection...).
2. Các bước tái hiện sự cố (Proof of Concept - PoC).
3. Tác động dự kiến tới dữ liệu và hệ thống nội bộ.

### 4.3. Cam kết Xử lý

- **Phản hồi ban đầu**: Trong vòng **24 giờ** làm việc kể từ khi nhận được báo cáo.
- **Đánh giá & Bản vá**: Cập nhật tiến độ xử lý cho người báo cáo mỗi **48 giờ** cho đến
  khi bản vá chính thức được phát hành.
- **Bảo mật thông tin**: Chúng tôi cam kết bảo mật danh tính người báo cáo (nếu được yêu cầu)
  và phối hợp xử lý theo đúng quy trình nội bộ.
