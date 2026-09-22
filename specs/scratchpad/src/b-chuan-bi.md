# PHẦN B: CHUẨN BỊ

## B.1. Bốn khoá API cho chuỗi đám mây

Tầng 0 (local) không cần khoá. Mỗi tầng đám mây cần một khoá riêng. Tầng nào thiếu khoá thì bị bỏ qua lặng lẽ trong
chuỗi. Nếu doanh nghiệp chạy chế độ `chi_local` cho toàn hệ thống thì có thể không cần khoá nào; khi đó nên có ít
nhất khoá tầng 1 và tầng 2 để thử chế độ `local_truoc`.

| Tầng | Lấy khoá ở đâu | Lưu ý quan trọng |
| --- | --- | --- |
| 1. Gemini | Google AI Studio | Bậc miễn phí có giới hạn tần suất: đủ để làm mẫu nhưng không đủ cho lưu lượng thật. Bật thanh toán trước khi mở cho người dùng. Lưu ý bậc miễn phí có thể dùng dữ liệu để cải tiến dịch vụ, nên chỉ gửi dữ liệu không nhạy cảm |
| 2. OpenRouter | openrouter.ai, trang Keys | Nạp tiền trước theo hạn mức. Đặt giới hạn chi tiêu cho khoá ngay khi tạo, làm lớp bảo vệ ngân sách đầu tiên |
| 3. Claude | Bảng điều khiển Claude Platform | Đặt giới hạn chi tiêu hằng tháng trong phần thanh toán |
| 4. OpenAI | Bảng điều khiển OpenAI Platform | Tạo khoá riêng cho từng dự án, không dùng chung một khoá cho mọi thứ |

```batbuoc
Ba việc làm ngay khi vừa tạo khoá.
Một: đặt giới hạn chi tiêu ở phía nhà cung cấp cho từng khoá. Kẻ tấn công không chạm được tới lớp bảo vệ này, khác
với trần ngân sách viết trong mã.
Hai: tạo khoá riêng cho môi trường phát triển và môi trường vận hành, không dùng chung.
Ba: dán cả bốn khoá vào tệp .env, và xác nhận .env đã nằm trong .gitignore TRƯỚC lần commit đầu tiên.
```

## B.2. Chọn GPU và model local

Bộ nhớ GPU cần ước lượng theo công thức:

```text
VRAM cần ≈ (Trọng số + Bộ đệm KV) ÷ 0,9
Trọng số  ≈ số tỷ tham số × số byte mỗi tham số   (q4_K_M ≈ 0,6 byte · q8_0 ≈ 1,1 byte · 16 bit = 2 byte)
Bộ đệm KV ≈ số yêu cầu đồng thời × độ dài ngữ cảnh × dung lượng mỗi token (phụ thuộc kiến trúc model)
```

Lập dự toán thường sai vì chỉ tính trọng số. Bộ đệm KV mới là thứ quyết định số người dùng đồng thời và độ dài
ngữ cảnh giữ được. Tiếng Việt tốn 1-3 token cho mỗi chữ, nhiều hơn tiếng Anh, nên cùng một hội thoại sẽ chiếm ngữ
cảnh nhiều hơn. Chọn hồ sơ GPU bằng biến `HO_SO_GPU`. Toàn bộ thông số nằm trong `config/models.yaml` (Phụ lục 2).

| HO_SO_GPU | GPU tham khảo | Bậc 1 (chính) | Bậc 2 (nhỏ) | num_ctx bậc 1 / bậc 2 | Số yêu cầu đồng thời | VRAM ước lượng | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpu6 | 6GB (máy trạm, laptop) | qwen3.5:4b-q4_K_M | qwen3.5:2b-q4_K_M | 8192 / 4096 | 1 | khoảng 4,5 GB cho bậc 1 | Chỉ nạp một model một lúc (OLLAMA_MAX_LOADED_MODELS=1); hạ cấp phải đổi model trong VRAM nên chậm vài giây. Hợp với chế độ dam_may_truoc |
| gpu8 | 8GB | qwen3.5:4b-q8_0 | qwen3.5:2b-q8_0 | 16384 / 8192 | 1 | khoảng 6,5 GB cho bậc 1 | Như gpu6. Lượng tử hoá q8_0 cho tiếng Việt tốt hơn q4 ở model nhỏ |
| gpu12 | 12GB | qwen3.5:9b-q4_K_M | qwen3.5:4b-q4_K_M | 16384 / 8192 | 1 | khoảng 11 GB cả hai | Sát trần. Nếu ollama ps cho thấy bậc 2 đẩy bậc 1 ra khỏi VRAM, đổi bậc 2 sang qwen3.5:2b-q4_K_M |
| gpu16 | 16GB | qwen3.5:9b-q4_K_M | qwen3.5:2b-q8_0 | 32768 / 8192 | 2 | khoảng 14 GB cả hai | Cấu hình cân bằng nhất cho dưới 5 người dùng đồng thời |
| gpu24 | 24GB | qwen3.5:27b-q4_K_M | qwen3.5:9b-q4_K_M | 16384 / 16384 | 1 | khoảng 20 GB cho bậc 1 | Model 27B cho chất lượng tiếng Việt cao nhất nhưng không chừa chỗ cho bậc 2. Phương án thay thế khi cần nhiều người đồng thời: bậc 1 qwen3.5:9b-q8_0 với 4 yêu cầu đồng thời, bậc 2 qwen3.5:2b-q8_0 |

Từ Giai đoạn 6 cần thêm model nhúng `bge-m3` (1024 chiều, khoảng 1,2 GB VRAM). Với gpu6 và gpu8, model nhúng chạy
trên CPU bằng bản `bge-m3-cpu` (tạo từ Modelfile có `PARAMETER num_gpu 0` ở PROMPT 27), còn VRAM dành trọn cho
model chat. Việc nạp tài liệu chạy theo lô nên độ chậm chấp nhận được.

```batbuoc
Mọi con số VRAM ở bảng trên chỉ là ước lượng để LẬP KẾ HOẠCH. Con số chính thức phải đến từ thử tải trên đúng phần
cứng: chạy scripts/do_toc_do.py (Giai đoạn 5) và đọc cột kích thước VRAM trong "ollama ps". Thẻ model cũng phải đối
chiếu lại với thư viện Ollama trước khi kéo về, vì tên và mức lượng tử hoá thay đổi theo từng đợt phát hành.
```

**Tiêu chí chọn model**, xếp theo thứ tự ưu tiên của doanh nghiệp:

1. Giấy phép: ưu tiên Apache-2.0 và MIT. Giấy phép cộng đồng riêng của nhà cung cấp cần rà soát pháp lý. Không dùng
   giấy phép phi thương mại.
2. Chất lượng tiếng Việt: kiểm chứng bằng bộ câu hỏi vàng của chính doanh nghiệp (Giai đoạn 5), không tin bảng xếp
   hạng tiếng Anh.
3. Cửa sổ ngữ cảnh: cửa sổ lớn giúp RAG, nhưng không thay được RAG.
4. Nhu cầu phần cứng và lượng tử hoá.

## B.3. Cài Ollama hoặc LM Studio

**Ollama** (khuyến nghị cho máy chủ):

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh
# Windows / macOS: tải bộ cài từ trang chủ Ollama
ollama --version
ollama pull qwen3.5:9b-q4_K_M      # thay theo hồ sơ GPU đã chọn
ollama pull qwen3.5:2b-q8_0
ollama run qwen3.5:9b-q4_K_M "Xin chào, hãy tự giới thiệu ngắn gọn bằng tiếng Việt."
ollama ps                           # model nào đang trong VRAM, chiếm bao nhiêu, bao giờ hết hạn
```

Sáu biến môi trường cần đặt cho Ollama:

| Biến | Giá trị đề xuất | Ý nghĩa |
| --- | --- | --- |
| OLLAMA_HOST | 127.0.0.1:11434 | Chỉ nghe ở địa chỉ vòng lặp. KHÔNG đặt 0.0.0.0 nếu không kèm biện pháp bù (Giai đoạn 5, ba cách nối an toàn) |
| OLLAMA_KEEP_ALIVE | 30m | Giữ model trong VRAM 30 phút sau lượt gọi cuối, tránh nạp lại nguội. Ứng dụng cũng gửi keep_alive trong từng lời gọi |
| OLLAMA_NUM_PARALLEL | theo hồ sơ GPU (1 hoặc 2) | Số yêu cầu một model xử lý song song. Phải KHỚP với SO_LUONG_DONG_THOI của ứng dụng |
| OLLAMA_MAX_LOADED_MODELS | 1 (gpu6, gpu8, gpu24) hoặc 2; từ Giai đoạn 6 đặt 2 cho gpu6 và gpu8 | Số model nạp cùng lúc. Từ Giai đoạn 6, gpu6 và gpu8 nạp thêm model nhúng bge-m3-cpu chạy trên RAM (num_gpu 0), nên cần 2 dù VRAM chỉ chứa một model chat |
| OLLAMA_FLASH_ATTENTION | 1 | Giảm bộ nhớ và tăng tốc với ngữ cảnh dài; là điều kiện để lượng tử hoá bộ đệm KV |
| OLLAMA_KV_CACHE_TYPE | q8_0 | Lượng tử hoá bộ đệm KV, tiết kiệm khoảng một nửa bộ nhớ KV mà chất lượng gần như không đổi |

```bash
# Linux (systemd): sudo systemctl edit ollama, thêm các dòng sau rồi khởi động lại
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
# sudo systemctl daemon-reload && sudo systemctl restart ollama
```

```bash
# Windows (PowerShell): đặt biến người dùng, thoát Ollama ở khay hệ thống rồi mở lại
setx OLLAMA_KEEP_ALIVE 30m
setx OLLAMA_NUM_PARALLEL 1
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KV_CACHE_TYPE q8_0
```

**LM Studio** (thuận tiện cho máy trạm Windows, có giao diện chọn model):

```bash
lms server start --port 1234
lms load qwen3.5-9b --context-length 16384 --gpu max --ttl 1800
lms ps
curl http://localhost:1234/v1/models
```

Ứng dụng gọi LM Studio qua `http://host.docker.internal:1234/v1` với `LOAI_BO_CHAY=lmstudio`. LM Studio không nhận
`keep_alive` và `options.num_ctx` theo từng lời gọi như Ollama: độ dài ngữ cảnh và thời gian giữ model (ttl) đặt lúc
nạp model. Bộ chạy trong mã (Giai đoạn 2) có giao diện chung `BoChay`, đổi Ollama sang LM Studio chỉ là đổi biến môi
trường.

```batbuoc
Ollama và LM Studio đều KHÔNG có xác thực. API của chúng không chỉ sinh văn bản mà còn tải và xoá model. Không bật
"Serve on Local Network" của LM Studio và không đặt OLLAMA_HOST=0.0.0.0 trên máy có địa chỉ mạng dùng chung, khi
chưa làm mục bảo vệ cổng ở Giai đoạn 5.
```

## B.4. Docker và GPU

| Thành phần | Yêu cầu | Kiểm tra |
| --- | --- | --- |
| Docker | Docker Desktop (Windows/macOS, backend WSL2) hoặc Docker Engine 24+ trên Linux; Compose v2 | docker compose version |
| Trình điều khiển NVIDIA | Bản hỗ trợ CUDA 12 trở lên | nvidia-smi |
| NVIDIA Container Toolkit | Chỉ cần khi chạy model TRONG container (vLLM ở Giai đoạn 10). Ở Giai đoạn 1-9, Ollama chạy trực tiếp trên máy chủ | docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi |
| Container gọi Ollama trên máy chủ | Docker Desktop hỗ trợ sẵn host.docker.internal. Trên Docker Engine cho Linux phải thêm extra_hosts "host.docker.internal:host-gateway" | docker compose exec backend curl -s http://host.docker.internal:11434/api/tags |

```meo
Trên Linux, khi Ollama chỉ nghe ở 127.0.0.1, container không gọi được qua host-gateway vì địa chỉ đó không phải
loopback của container. Có hai cách: chạy backend với network_mode: host, hoặc bind Ollama vào địa chỉ cầu nối
docker0 (thường là 172.17.0.1) kèm luật tường lửa. Giai đoạn 5 trình bày đủ ba cách nối an toàn. Trong lúc phát
triển trên Docker Desktop, host.docker.internal đã đủ.
```

## B.5. Công cụ phát triển

| Công cụ | Phiên bản | Dùng cho |
| --- | --- | --- |
| Python | 3.12 trở lên | Backend FastAPI, kịch bản kiểm tra, bộ đánh giá |
| Node.js | Bản LTS hiện hành (22 hoặc 24) | Angular CLI, build frontend |
| Angular CLI | Bản ổn định hiện hành (npm install -g @angular/cli) | Tạo và build workspace frontend |
| Git | 2.40 trở lên; trên Windows dùng Git for Windows và đặt Git Bash làm terminal mặc định của Antigravity | Quản lý mã, thẻ giai-doan-N. Mọi lệnh Tự đánh giá viết theo cú pháp bash |
| curl, jq | Bất kỳ | Lệnh tự đánh giá |
| k3d hoặc kind, kubectl, helm | Bản hiện hành | Chỉ từ Giai đoạn 10 |

## B.6. Google Antigravity: cài đặt và các điều cần biết

| Nội dung | Chi tiết |
| --- | --- |
| Hai chế độ | Editor View để tự đọc và sửa mã, dùng cho phần lớn prompt. Manager Surface để giao nhiều việc song song, dùng khi prompt ghi "Chế độ: Manager Surface" (các việc độc lập ở Giai đoạn 5, 9, 10) |
| Artifact cần đọc | Implementation Plan: đọc trước khi cho phép chạy, ở mọi prompt ghi "Đọc Plan: Có". Code diffs: đọc ở mọi prompt động tới bảo mật, xác thực, chính sách định tuyến. Walkthrough: đọc khi chốt giai đoạn. Ảnh chụp và bản ghi trình duyệt: dùng cho prompt giao diện ở Giai đoạn 4 |
| Quy trình mỗi prompt | Dán khối PROMPT → đọc Implementation Plan (nếu có) → cho phép → agent làm và chạy TỰ ĐÁNH GIÁ → đọc bảng ĐẠT/CHƯA ĐẠT → commit |
| Rule và AGENTS.md | Antigravity đọc AGENTS.md ở gốc workspace trong mọi lượt. Dự án dùng hai lớp luật: năm tệp rule dùng chung trong `.agents/rules/` (naming, clean_code, type_safety, markdown, versioning), mỗi tệp một chủ đề; và AGENTS.md chỉ chứa luật riêng của dự án, kèm bảng "Rule bắt buộc" GỌI TỚI năm tệp đó bằng đường dẫn. PROMPT 1 giao cho agent tự tạo cả hai lớp. Sau đó, sửa rule phải hỏi trước |
| Giới hạn cần biết | Antigravity dùng model đám mây của chính nó để viết mã. Bốn khoá API trong tài liệu là cho SẢN PHẨM đang xây, không phải cho IDE |

```batbuoc
Vì agent của IDE chạy trên đám mây, KHÔNG đưa dữ liệu thật của khách hàng hay tài liệu nội bộ mật vào workspace. Tài
liệu mẫu, câu hỏi đánh giá và dữ liệu thử trong suốt tài liệu này đều là dữ liệu GIẢ. Dữ liệu thật chỉ nạp trên máy
chủ vận hành, qua kịch bản nạp tài liệu, sau khi hệ thống đã hoàn thành.
```
