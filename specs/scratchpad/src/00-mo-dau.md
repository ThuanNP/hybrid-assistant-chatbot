```bia
XÂY DỰNG ỨNG DỤNG AI THỰC CHIẾN
DỰNG AI CHATBOT LAI
CHẠY TRÊN MÁY VÀ ĐÁM MÂY
Ollama · LM Studio · GPU 6-24GB · Docker
Chuỗi dự phòng Gemini → OpenRouter/auto → Claude → OpenAI
Backend FastAPI · Frontend Angular · Giao việc cho AI agent trong Google Antigravity
Dự án: hybrid-assistant-chatbot · Tháng 09/2026
```

# MỞ ĐẦU

## Tài liệu này dành cho ai và dùng thế nào

Tài liệu hướng dẫn dựng Trợ lý nội bộ, một ứng dụng AI chatbot web phục vụ cán bộ, công nhân viên của Doanh
nghiệp kinh doanh điện năng. Có thể dùng trợ lý để tra cứu quy trình, diễn giải số liệu, chuẩn hoá văn bản
và trả lời các câu hỏi nghiệp vụ lặp lại. Cách xây dựng là giao việc từng bước cho AI agent trong Google Antigravity.
Mỗi bước là một prompt mẫu đã viết sẵn: người đọc dán vào ô chat, duyệt kế hoạch agent đề xuất, rồi đọc bảng tự
đánh giá agent trả về.

Tài liệu hợp nhất hai hướng dẫn gốc thành một kiến trúc lai. Hướng dẫn thứ nhất dựng chatbot bằng bốn nhà cung
cấp đám mây xếp thành chuỗi dự phòng. Hướng dẫn thứ hai dựng chatbot chạy hoàn toàn trên máy bằng Ollama hoặc LM
Studio. Kiến trúc lai gồm:

- Model chạy trên máy (Ollama hoặc LM Studio, GPU 6-24GB) là tầng 0, phục vụ mặc định và giữ dữ liệu nhạy cảm trong
  hạ tầng doanh nghiệp.
- Bốn nhà cung cấp đám mây xếp thành chuỗi dự phòng Gemini → OpenRouter/auto → Claude → OpenAI. Chuỗi này chỉ dùng
  khi chính sách dữ liệu cho phép.
- Backend FastAPI và frontend Angular, đóng gói bằng Docker.

Tài liệu cũng triển khai đủ những hạng mục mà hai hướng dẫn gốc cố ý chưa làm: RAG và cơ sở dữ liệu vector, gọi
công cụ, đăng nhập một lần doanh nghiệp, cổng AI, Kubernetes, nhiều GPU và cân bằng tải, tinh chỉnh model. Các
hạng mục được xếp thành 11 giai đoạn. Hết mỗi giai đoạn là có một sản phẩm chạy được.

Cấu trúc tài liệu:

| Phần | Nội dung | Ai đọc |
| --- | --- | --- |
| PHẦN A: LẬP KẾ HOẠCH | Phạm vi, kiến trúc lai, chính sách định tuyến, các quyết định kỹ thuật và điều kiện dừng | Chủ sở hữu nghiệp vụ, trưởng nhóm kỹ thuật |
| PHẦN B: CHUẨN BỊ | Khoá API, chọn GPU và model, cài Ollama/LM Studio, Docker, công cụ phát triển, Antigravity | Người dựng hệ thống |
| PHẦN C: CÁC PROMPT THỰC HIỆN MẪU | 11 giai đoạn, 55 prompt giao việc cho AI agent | Người dựng hệ thống |
| PHỤ LỤC | Các tệp rule và AGENTS.md, models.yaml hợp nhất, bảng sự kiện và mã lỗi, danh mục kiểm tra, bảng thuật ngữ Anh-Việt | Tra cứu |

## Lộ trình 11 giai đoạn

| Giai đoạn | Tên | Prompt | Phiên bản | Kết quả khi xong |
| --- | --- | --- | --- | --- |
| 1 | Khung dự án và luật chơi | 1-4 | 0.1.0 | Repo có AGENTS.md, khung thư mục, Docker, danh mục model và hai kịch bản kiểm tra |
| 2 | Lõi định tuyến lai | 5-10 | 0.2.0 | Một hàm gọi model duy nhất, đi qua tầng local rồi chuỗi đám mây theo chính sách, có hàng đợi và trần ngân sách |
| 3 | API chạy được | 11-13 | 0.3.0 | API FastAPI đầy đủ: phát theo dòng, lưu hội thoại, /health và /ready |
| 4 | Giao diện Angular, mốc chatbot dùng được | 14-17 | 0.4.0 | Cán bộ mở trình duyệt và trò chuyện được |
| 5 | Sẵn sàng cho người dùng thật | 18-24 | 1.0.0 | Đăng nhập, hạn mức, nhật ký, giám sát VRAM, bảo vệ cổng Ollama, bộ đánh giá, đóng gói cho môi trường vận hành |
| 6 | RAG lai và cơ sở dữ liệu vector | 25-31 | 1.1.0 | Trả lời có căn cứ và trích dẫn từ tài liệu nội bộ, biết nói "không tìm thấy căn cứ" |
| 7 | Gọi công cụ có kiểm soát | 32-34 | 1.2.0 | Mọi con số do công cụ tính; tra cứu dữ liệu nghiệp vụ chỉ đọc |
| 8 | Đăng nhập một lần doanh nghiệp và bảng quản trị | 35-39 | 2.0.0 | Đăng nhập bằng tài khoản doanh nghiệp (OIDC), phân quyền theo phòng ban, bảng quản trị |
| 9 | Cổng AI, bộ nhớ đệm và quan sát | 40-43 | 2.1.0 | Khoá ảo và hạn mức theo phòng ban, Redis, bảng theo dõi vận hành và chất lượng |
| 10 | Kubernetes và vLLM | 44-49 | 2.2.0 | Chạy nhiều bản sao trên cụm có GPU, tự mở rộng theo tải |
| 11 | Tinh chỉnh model | 50-55 | 2.3.0 | Model tinh chỉnh văn phong và định dạng, qua cổng đánh giá, triển khai dần |

Từ Giai đoạn 1 đến Giai đoạn 5 là con đường ngắn nhất tới một sản phẩm mở được cho người dùng thật. Từ Giai đoạn 6 trở
đi, chỉ làm khi có tín hiệu nghiệp vụ rõ ràng; tín hiệu của từng giai đoạn được nêu ở mục A.1. Cột Phiên bản là số
phiên bản ứng dụng phát hành khi xong giai đoạn, theo quy tắc SemVer ở mục A.6.

## Cách đọc một prompt

Mỗi prompt trong Phần C trình bày theo cùng một khuôn:

| Thành phần | Ý nghĩa |
| --- | --- |
| Chế độ · Đọc Plan | Chọn Editor View hay Manager Surface trong Antigravity; có phải đọc Implementation Plan trước khi cho agent ghi tệp không |
| Mục tiêu | Vì sao bước này quan trọng |
| Làm trước | Điều phải kiểm trong Implementation Plan trước khi bấm cho phép |
| Khối PROMPT | Nội dung dán nguyên văn vào ô chat của agent; cuối khối luôn có đoạn TỰ ĐÁNH GIÁ để agent tự kiểm |
| Agent phải trả về | Yêu cầu trả về cụ thể, kiểm được. Thiếu một dòng là chưa xong |
| Tự đánh giá | Các lệnh agent tự chạy lại, kèm kết quả kỳ vọng. Agent trả về bảng Hạng mục, Lệnh, Kết quả, ĐẠT/CHƯA ĐẠT |
| BẮT BUỘC | Điều không được vi phạm, kèm lý do |
| MẸO | Kinh nghiệm giúp làm nhanh hơn hoặc tránh lỗi hay gặp |

```batbuoc
Không bỏ qua bảng Tự đánh giá. Agent rất hay báo "đã xong" dựa trên mô tả của chính nó. Chỉ tin bảng
ĐẠT/CHƯA ĐẠT sinh ra từ lệnh đã thực sự chạy. Khi bảng còn dòng CHƯA ĐẠT, không commit và không sang prompt sau.
```

```meo
Sau mỗi prompt đạt yêu cầu, commit ngay với thông điệp "PROMPT N: <tên>". Hết mỗi giai đoạn, gắn thẻ git
giai-doan-N. Khi một prompt sau làm hỏng thứ đã chạy, quay lại thẻ gần nhất sẽ nhanh hơn nhiều so với sửa tay.
```
