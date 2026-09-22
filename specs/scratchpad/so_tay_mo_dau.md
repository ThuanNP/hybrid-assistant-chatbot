```bia
SỔ TAY PROMPT CHO GOOGLE ANTIGRAVITY
DỰNG AI CHATBOT LAI
THEO TỪNG GIAI ĐOẠN
55 prompt mẫu · 11 giai đoạn · chép và dán thẳng vào ô chat của agent
Dự án: hybrid-assistant-chatbot · Backend FastAPI · Frontend Angular
Tháng 09/2026
```

# CÁCH DÙNG SỔ TAY

## Sổ tay gồm những gì

Sổ tay gom những gì cần khi làm việc với Antigravity, theo thứ tự thực hiện:

- thao tác đầu mỗi giai đoạn và bảng LÀM GÌ / CHƯA LÀM GÌ;
- nguyên văn từng PROMPT;
- danh sách kiểm "Agent phải trả về" và mục "Tự đánh giá";
- các hộp BẮT BUỘC và MẸO.

Mỗi giai đoạn kết thúc bằng một prompt chốt giai đoạn để rà điều kiện hoàn thành và phát hành phiên bản.

## Thiết lập workspace một lần

1. Chuẩn bị máy:
   - Ollama hoặc LM Studio đã chạy, đã kéo model theo hồ sơ GPU (máy GPU 8 GB dùng hồ sơ gpu8:
     qwen3.5:4b-q8_0 và qwen3.5:2b-q8_0);
   - Docker Desktop (WSL2), Python 3.12, Node.js LTS, Angular CLI, Git for Windows;
   - terminal mặc định của Antigravity đặt là Git Bash;
   - khoá API cho các tầng đám mây cần dùng (Gemini, OpenRouter, Claude, OpenAI). Tầng nào thiếu khoá thì bị bỏ qua.
     Nếu chỉ chạy chế độ chi_local thì không cần khoá nào.
2. Mở Antigravity, tạo thư mục trống tên `hybrid-assistant-chatbot`, mở làm workspace, chọn Editor View.
3. Dán PROMPT 1. Agent sẽ tự tạo năm tệp rule trong `.agents/rules/` và tệp AGENTS.md gọi tới chúng. Từ đó về sau,
   mọi prompt đều bắt đầu bằng "Đọc AGENTS.md", và agent tự tuân theo rule.
4. Không đưa dữ liệu thật của khách hàng hay tài liệu mật vào workspace. Mọi dữ liệu trong sổ tay đều là dữ liệu giả.

## Quy trình cho mỗi prompt

| Bước | Việc làm | Artifact cần xem |
| --- | --- | --- |
| 1 | Chọn đúng chế độ ghi ở dòng "Chế độ" |  |
| 2 | Chọn cả ô PROMPT, chép và dán vào ô chat của agent |  |
| 3 | Nếu dòng "Đọc Plan" là Có: đọc Implementation Plan, kiểm điều ghi ở mục "Làm trước", rồi mới cho phép chạy | Implementation Plan |
| 4 | Theo dõi agent làm; với prompt động tới bảo mật, xác thực hay định tuyến thì đọc kỹ phần thay đổi mã | Code diffs |
| 5 | Agent tự chạy TỰ ĐÁNH GIÁ và trả bảng Hạng mục, Lệnh, Kết quả, ĐẠT/CHƯA ĐẠT | Bảng tự đánh giá |
| 6 | Đánh dấu ☐ ở mục "Agent phải trả về"; thiếu dòng nào thì yêu cầu agent làm tiếp |  |
| 7 | Mọi dòng đều ĐẠT thì commit với thông điệp "PROMPT N: tên" |  |
| 8 | Hết giai đoạn: dán "Chốt Giai đoạn N" để phát hành phiên bản và gắn thẻ git | Walkthrough |

## Chế độ Antigravity theo giai đoạn

| Giai đoạn | Chế độ chủ yếu | Ghi chú |
| --- | --- | --- |
| 1-4 | Editor View | Làm tuần tự, mỗi prompt dựa trên kết quả prompt trước |
| 5 | Editor View, có 2 prompt Manager Surface | Các việc độc lập (giám sát, bảo vệ cổng) có thể chạy song song |
| 6-7 | Editor View, 1 prompt Manager Surface | Giao diện trích dẫn và trang nạp tài liệu làm song song được |
| 8-9 | Editor View, 1 prompt Manager Surface | Bảng quản trị Angular làm song song với API quản trị |
| 10 | Editor View và Manager Surface xen kẽ | Helm, CI/CD, chính sách mạng là các việc độc lập |
| 11 | Editor View | Huấn luyện và đánh giá phải tuần tự |

## Phiên bản phát hành khi chốt giai đoạn

Ứng dụng đánh số theo SemVer (https://semver.org/), quy định trong `.agents/rules/versioning.md` do PROMPT 1 tạo ra.

| Giai đoạn | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phiên bản | 0.1.0 | 0.2.0 | 0.3.0 | 0.4.0 | 1.0.0 | 1.1.0 | 1.2.0 | 2.0.0 | 2.1.0 | 2.2.0 | 2.3.0 |

```batbuoc
Không sang prompt sau khi bảng tự đánh giá còn dòng CHƯA ĐẠT. Agent rất hay báo "đã xong" dựa trên mô tả của chính
nó; chỉ tin bảng sinh ra từ lệnh đã thực sự chạy.
```

```meo
Khi một prompt sau làm hỏng thứ đã chạy, quay về thẻ giai-doan-N gần nhất (git checkout giai-doan-N) nhanh hơn nhiều
so với nhờ agent sửa ngược.
```

# PHẦN C: CÁC PROMPT THỰC HIỆN MẪU
