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

### 2.4. Quét Bí mật Tự động bằng Gitleaks

Dự án triển khai ba lớp kiểm soát nhằm ngăn bí mật lọt vào kho mã:

| Lớp kiểm soát | Thời điểm | Cơ chế |
| :--- | :--- | :--- |
| Móc `pre-commit` | Trước mỗi lần commit trên máy cá nhân | `gitleaks git --staged`, chặn commit khi phát hiện |
| Quét thủ công | Trước khi phát hành, khi rà soát định kỳ | `python scripts/quet_bi_mat.py` |
| Quy trình CI | Mỗi lần đẩy mã, pull request vào `main`, và hằng tuần | `.github/workflows/quet-bi-mat.yml` |

Quy định vận hành:

- Cấu hình quét nằm tại `.gitleaks.toml`; hướng dẫn đầy đủ tại
  `.agents/skills/secrets-gitleaks/SKILL.md`.
- Mỗi thành viên **bắt buộc** chạy `python scripts/cai_dat_moc_git.py` ngay sau khi clone
  kho mã, vì móc git chỉ có hiệu lực trên máy cục bộ và không đi theo kho mã.
- Mọi kết quả quét đều bật chế độ che giá trị (`--redact`). Báo cáo quét là **tài liệu mật**,
  lưu trong thư mục `secret/` (đã loại trừ khỏi git), không đính kèm vào issue hay pull request.
- Khi phát hiện bí mật thật, thứ tự xử lý bắt buộc là: **thu hồi và xoay vòng khoá trước**,
  sau đó mới gỡ khỏi mã nguồn và viết lại lịch sử git. Bí mật đã vào git phải luôn được
  coi là đã lộ, kể cả khi kho mã ở chế độ riêng tư.
- Việc bỏ qua móc kiểm tra bằng `git commit --no-verify` chỉ được chấp nhận trong trường hợp
  đặc biệt và phải nêu rõ lý do trong mô tả commit.

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
- **Email**: `thuannp.hcmc@gmail.com` (quản trị viên hệ thống)
- **Tiêu đề email**: `[SECURITY VULNERABILITY] <Tóm tắt ngắn gọn sự cố>`

### 4.2. Thông tin Cần Cung cấp

Để giúp chúng tôi xác minh và xử lý nhanh chóng, bài báo cáo nên bao gồm:

1. Mô tả chi tiết loại lỗ hổng (ví dụ: Rò rỉ dữ liệu `NHAY_CAM`, bypass router, SQL Injection...).
2. Các bước tái hiện sự cố (Proof of Concept - PoC).
3. Tác động dự kiến tới dữ liệu và hệ thống nội bộ.

### 4.3. Cam kết Xử lý

Chúng tôi cam kết bảo mật danh tính người báo cáo (nếu được yêu cầu)
và phối hợp xử lý theo đúng quy trình nội bộ.

## 5. Miễn trừ Trách nhiệm Pháp lý (Legal Disclaimer)

### 5.1. Phạm vi áp dụng

Tài liệu này là quy định kỹ thuật nội bộ, không phải văn bản tư vấn pháp lý và không thay thế
cho các quy chế, quy trình an toàn thông tin do cấp có thẩm quyền của doanh nghiệp ban hành.
Khi có mâu thuẫn, quy chế của doanh nghiệp và pháp luật Việt Nam hiện hành được ưu tiên áp dụng.

### 5.2. Giới hạn của công cụ quét tự động

- Các công cụ quét bí mật (`gitleaks`) hoạt động theo mẫu nhận dạng và ngưỡng entropy đã biết,
  do đó **không bảo đảm phát hiện được toàn bộ** thông tin xác thực bị ghim cứng.
- Kết quả quét không phát hiện rò rỉ **không đồng nghĩa** với việc hệ thống không có lỗ hổng,
  và không thay thế cho rà soát mã nguồn thủ công, kiểm thử thâm nhập hay đánh giá an toàn
  thông tin độc lập.
- Các khung tham chiếu được viện dẫn trong tài liệu (OWASP, CWE, PCI-DSS, SOC2, GDPR) chỉ mang
  tính định hướng kỹ thuật. Việc tuân thủ phải do bộ phận có thẩm quyền đánh giá và công nhận
  bằng văn bản; tài liệu này không phải là chứng nhận tuân thủ.

### 5.3. Trách nhiệm của người sử dụng

- Người sử dụng và quản trị viên chịu trách nhiệm cấu hình, vận hành hệ thống đúng quy định,
  bao gồm bảo quản khoá API, mật khẩu và dữ liệu nhãn `NHAY_CAM`.
- Trợ lý AI có thể tạo ra nội dung không chính xác. Mọi số liệu nghiệp vụ, quyết định chuyên môn
  và văn bản có giá trị pháp lý phải được nhân sự có thẩm quyền kiểm tra, xác nhận trước khi
  sử dụng. Hệ thống hoạt động ở trần tự chủ Bậc 2 nêu tại mục 3 và không thay thế thẩm quyền
  phê duyệt của con người.
- Việc sử dụng phần mềm bên thứ ba đi kèm dự án tuân theo giấy phép tương ứng của từng phần mềm.

### 5.4. Phạm vi sử dụng

Hệ thống chỉ dành cho mục đích sử dụng nội bộ của doanh nghiệp. Nghiêm cấm sử dụng công cụ và
tài liệu trong dự án để dò quét, khai thác hay truy cập trái phép vào bất kỳ hệ thống nào mà
người sử dụng không được trao quyền hợp pháp.
