---
name: secrets-gitleaks
description: >
  Phát hiện và ngăn chặn rò rỉ bí mật (khoá API, mật khẩu, chuỗi kết nối, khoá riêng tư)
  trong mã nguồn và lịch sử git bằng Gitleaks. Sử dụng khi: (1) Quét kho mã tìm bí mật
  bị ghim cứng, (2) Cài móc pre-commit chặn bí mật trước khi commit, (3) Tích hợp quét bí
  mật vào quy trình CI, (4) Rà soát tuân thủ quy tắc tuyệt đối 4 của AGENTS.md,
  (5) Thiết lập mốc nền (baseline) và theo dõi phát hiện mới, (6) Khắc phục bí mật đã lọt
  vào lịch sử git.
version: 0.1.0
category: devsecops
tags: [secrets, gitleaks, secret-scanning, devsecops, ci, api-keys]
frameworks: [OWASP, CWE]
dependencies:
  tools: [gitleaks, git, python]
references:
  - https://github.com/gitleaks/gitleaks
  - https://cwe.mitre.org/data/definitions/798.html
---

# Phát hiện bí mật bằng Gitleaks

## Tổng quan

Gitleaks quét kho git, tệp và thư mục để tìm thông tin xác thực bị ghim cứng: mật khẩu,
khoá API, token và khoá riêng tư. Công cụ kết hợp so khớp biểu thức chính quy với phân
tích entropy Shannon.

Kỹ năng này là bản thích ứng của kỹ năng `secrets-gitleaks` thuộc bộ SecOpsAgentKit,
được cấu hình riêng cho dự án Trợ lý AI Nội bộ. Kỹ năng phục vụ trực tiếp **quy tắc
tuyệt đối số 4** trong `AGENTS.md`: không ghi khoá API, mật khẩu, chuỗi kết nối vào mã;
kiểm tra rò rỉ bí mật bằng `gitleaks`.

Nguồn gốc: <https://github.com/AgentSecOps/SecOpsAgentKit> (thư mục
`skills/devsecops/secrets-gitleaks`). Các tệp trong `references/` là bản sao nguyên văn
tiếng Anh từ kho nguồn.

## Bắt đầu nhanh

Dự án đã có sẵn cấu hình `.gitleaks.toml` tại thư mục gốc và hai kịch bản hỗ trợ.

```powershell
# Quét toàn bộ dự án (lịch sử git và cây làm việc), xuất báo cáo Markdown
python scripts/quet_bi_mat.py --dinh-dang markdown

# Chỉ quét lịch sử git
python scripts/quet_bi_mat.py --pham-vi git

# Cài móc pre-commit chặn bí mật trên máy cục bộ
python scripts/cai_dat_moc_git.py
```

Gọi trực tiếp Gitleaks khi cần:

```powershell
gitleaks git . --redact --no-banner        # Quét lịch sử commit
gitleaks dir . --redact --no-banner        # Quét cây làm việc
gitleaks git --staged --redact --no-banner # Quét vùng staged (móc pre-commit dùng lệnh này)
```

Lưu ý phiên bản: từ Gitleaks 8.19 trở đi, lệnh `detect` và `protect` đã lỗi thời, thay
bằng `git`, `dir` và cờ `--staged`. Dự án chuẩn hoá theo cú pháp mới.

## Quy trình chuẩn của dự án

### 1. Quét trước mỗi lần commit

Móc pre-commit chạy `gitleaks git --staged` và chặn commit khi phát hiện bí mật. Cài đặt
bằng `python scripts/cai_dat_moc_git.py`. Móc nằm trong `.git/hooks/` nên chỉ có hiệu lực
trên máy cục bộ; mỗi thành viên phải tự cài sau khi clone kho mã.

### 2. Quét định kỳ và trước khi phát hành

Chạy `python scripts/quet_bi_mat.py --dinh-dang markdown` rồi lưu báo cáo vào thư mục
`secret/` (đã nằm trong `.gitignore`). Tuyệt đối không commit báo cáo vì báo cáo chứa
đường dẫn và ngữ cảnh của bí mật.

### 3. Quét tự động trong CI

Quy trình `.github/workflows/quet-bi-mat.yml` chạy trên mọi lần đẩy mã và pull request
vào nhánh `main`. Quy trình lấy toàn bộ lịch sử (`fetch-depth: 0`) để quét được các commit
cũ, và thất bại khi phát hiện bí mật.

### 4. Xử lý khi phát hiện bí mật

Thứ tự ưu tiên bắt buộc:

1. **Thu hồi và xoay vòng khoá ngay lập tức.** Bí mật đã lọt vào git phải coi như đã lộ,
   kể cả khi kho mã ở chế độ riêng tư.
2. Gỡ bí mật khỏi mã nguồn, chuyển sang biến môi trường trong `.env`.
3. Nếu bí mật nằm trong lịch sử commit, viết lại lịch sử bằng `git filter-repo`.
   Xem `references/remediation-guide.md`.
4. Ghi nhận sự cố theo mục 4 của `SECURITY.md`.

### 5. Xử lý dương tính giả

Thêm mục loại trừ vào `.gitleaks.toml` (khối `[allowlist]`) kèm chú thích nêu rõ lý do.
Không dùng `git commit --no-verify` để né móc pre-commit; nếu bắt buộc phải bỏ qua, ghi
chú lý do trong mô tả commit. Xem `references/false-positives.md`.

## Cấu hình của dự án

Tệp `.gitleaks.toml` ở thư mục gốc mở rộng bộ luật mặc định (`useDefault = true`) và bổ
sung danh sách loại trừ phù hợp với cấu trúc dự án:

| Đường dẫn loại trừ | Lý do |
| :--- | :--- |
| `backend/.venv/` | Thư viện Python bên thứ ba, không phải mã của dự án |
| `node_modules/`, `frontend/dist/`, `frontend/.angular/` | Phụ thuộc và sản phẩm dựng của frontend |
| `specs/`, `secret/`, `ket_qua_eval/` | Thư mục cục bộ đã nằm trong `.gitignore` |
| `.agents/skills/` | Kỹ năng bên thứ ba được nhúng vào kho mã |

Tệp `.env` **không** nằm trong danh sách loại trừ: tệp này chứa khoá thật và đã được
`.gitignore`, nhưng vẫn cần Gitleaks cảnh báo nếu ai đó vô tình đưa vào vùng staged.

## Cân nhắc bảo mật

- **Luôn dùng cờ `--redact`** khi in kết quả ra màn hình hoặc nhật ký CI, để bí mật
  không bị ghi lại lần thứ hai ở nơi khác.
- **Báo cáo quét là tài liệu mật.** Báo cáo JSON chứa đoạn mã và vị trí của bí mật; lưu
  trong `secret/`, không đính kèm vào issue hay pull request.
- **Không đưa nội dung tin nhắn hay dữ liệu `NHAY_CAM` vào báo cáo.** Kịch bản
  `quet_bi_mat.py` luôn bật chế độ che, không ghi giá trị bí mật ra tệp Markdown.
- **Gitleaks không thay thế kiểm tra thủ công.** Công cụ chỉ phát hiện các mẫu đã biết;
  bí mật có định dạng lạ vẫn có thể lọt.

## Ánh xạ khung tham chiếu

| Khung | Mã định danh | Nội dung |
| :--- | :--- | :--- |
| CWE | CWE-798 | Sử dụng thông tin xác thực ghim cứng |
| CWE | CWE-259 | Sử dụng mật khẩu ghim cứng |
| CWE | CWE-321 | Sử dụng khoá mật mã ghim cứng |
| OWASP | A07:2021 | Thất bại trong định danh và xác thực |

Chi tiết ánh xạ sang PCI-DSS, SOC2 và GDPR xem `references/compliance-mapping.md`.
Doanh nghiệp cần tự đối chiếu với quy định nội bộ và pháp luật Việt Nam hiện hành trước
khi viện dẫn các khung này.

## Tài liệu tham chiếu kèm theo

| Tệp | Nội dung |
| :--- | :--- |
| `references/detection-rules.md` | Danh sách luật phát hiện dựng sẵn kèm ánh xạ CWE |
| `references/remediation-guide.md` | Quy trình khắc phục, gồm viết lại lịch sử git |
| `references/false-positives.md` | Mẫu dương tính giả thường gặp và cách loại trừ |
| `references/compliance-mapping.md` | Ánh xạ chi tiết sang PCI-DSS, SOC2, GDPR, OWASP |

## Khắc phục sự cố

### Gitleaks báo lỗi `docx2txt.exe: command not found`

Git trên Windows dùng `astextplain` để chuyển tệp `.docx` sang văn bản khi so sánh, nhưng
`docx2txt` không có sẵn. Thông báo này vô hại với kết quả quét (Gitleaks vẫn báo
`no leaks found`). Nếu muốn loại bỏ hẳn, gỡ mục `*.docx diff=astextplain` khỏi
`.gitattributes` hoặc cài `docx2txt`.

### Quét thư mục quá chậm

Lệnh `gitleaks dir` không đọc `.gitignore`, nên mặc định quét cả `backend/.venv` và
`node_modules`. Cấu hình `.gitleaks.toml` của dự án đã loại trừ các thư mục này; hãy bảo
đảm luôn chạy lệnh từ thư mục gốc để Gitleaks tìm thấy tệp cấu hình.

### Móc pre-commit không chạy

Kiểm tra tệp `.git/hooks/pre-commit` có tồn tại và có quyền thực thi. Trên Windows, Git
Bash yêu cầu dòng đầu tiên là `#!/bin/sh`. Chạy lại `python scripts/cai_dat_moc_git.py`
để cài đè.

### Cần tạm bỏ qua một phát hiện đơn lẻ

Thêm chú thích `gitleaks:allow` ngay trên dòng bị báo. Chỉ dùng cho giá trị mẫu, giá trị
giữ chỗ hoặc dữ liệu kiểm thử; không bao giờ dùng cho bí mật thật.

## Giấy phép và miễn trừ trách nhiệm

Kỹ năng gốc thuộc bộ SecOpsAgentKit, phát hành theo giấy phép của kho nguồn. Gitleaks là
phần mềm mã nguồn mở theo giấy phép MIT.

Công cụ chỉ hỗ trợ phát hiện, **không bảo đảm phát hiện được toàn bộ bí mật**. Kết quả
quét sạch không thay thế cho rà soát mã, kiểm thử thâm nhập hay đánh giá an toàn thông
tin của bộ phận có thẩm quyền.
