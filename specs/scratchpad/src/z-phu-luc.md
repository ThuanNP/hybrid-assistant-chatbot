# PHỤ LỤC

## Phụ lục 1: Các tệp rule và AGENTS.md hoàn chỉnh

PROMPT 1 giao cho agent tự tạo hai lớp luật chơi. Phụ lục này là kết quả mẫu để đối chiếu. Nếu muốn bỏ qua PROMPT 1,
tạo đúng các tệp dưới đây bằng tay.

| Tệp | Nội dung chính | Áp dụng khi |
| --- | --- | --- |
| .agents/rules/naming.md | snake_case tiếng Việt không dấu cho Python; kebab-case cho tệp TypeScript và Markdown; một khái niệm một từ | Đặt tên tệp, biến, hàm, lớp, bảng |
| .agents/rules/clean_code.md | Hàm một việc, trả sớm, không nuốt ngoại lệ, không mã chết, chú thích nói VÌ SAO | Viết hoặc sửa mã |
| .agents/rules/type_safety.md | Type hint đầy đủ, pyright; TypeScript strict, cấm any; thu hẹp Optional trước khi dùng | Viết mã và kiểm thử |
| .agents/rules/markdown.md | Mọi tệp .md qua markdownlint-cli2; văn xuôi tối đa 100 ký tự; kèm .markdownlint.json và .markdownlint-cli2.jsonc | Tạo hoặc sửa tệp .md |
| .agents/rules/versioning.md | SemVer theo https://semver.org/; 0.y.z khi phát triển, 1.0.0 khi vận hành chính thức; /api/v1/; CHANGELOG; thẻ vX.Y.Z | Phát hành, đổi API |

AGENTS.md chỉ nêu phần riêng của dự án và GỌI TỚI các rule trên, không chép lại nội dung. Mục "Không làm ở giai đoạn
hiện tại" phải được cập nhật ở cuối mỗi giai đoạn.

```text
# AGENTS.md - hybrid-assistant-chatbot

## Dự án
Trợ lý nội bộ cho cán bộ, công nhân viên của Doanh nghiệp kinh doanh điện năng.
Chatbot web hội thoại nhiều lượt. Back-end FastAPI (backend/), front-end Angular (frontend/).
Gọi mô hình qua chuỗi lai: tầng 0 local (Ollama hoặc LM Studio, hạ cấp bậc 1 -> bậc 2),
rồi chuỗi đám mây Gemini -> OpenRouter/auto -> Claude -> OpenAI, theo chính sách định tuyến.

## Rule bắt buộc - đọc trước mọi việc
| Tệp                           | Áp dụng khi                                 |
| ----------------------------- | ------------------------------------------- |
| .agents/rules/naming.md       | Đặt tên tệp, biến, hàm, lớp, bảng           |
| .agents/rules/clean_code.md   | Viết hoặc sửa mã                            |
| .agents/rules/type_safety.md  | Viết mã và kiểm thử                         |
| .agents/rules/markdown.md     | Tạo hoặc sửa bất kỳ tệp .md nào             |
| .agents/rules/versioning.md   | Phát hành, nâng phiên bản, đổi API          |
Khi AGENTS.md và rule mâu thuẫn, quy tắc tuyệt đối trong AGENTS.md thắng; muốn đổi rule phải hỏi trước.

## Quy tắc tuyệt đối
1. Mọi lời gọi mô hình (sinh văn bản và nhúng vector) đi qua ĐÚNG MỘT nơi: goi_mo_hinh(),
   goi_mo_hinh_theo_dong() và goi_nhung() trong backend/app/llm/router.py. Cấm gọi httpx tới bộ chạy
   hay litellm ở bất kỳ nơi nào khác.
2. Dữ liệu nhãn NHAY_CAM (mã khách hàng, số điện thoại, số căn cước, số và chỉ số công tơ, phòng ban
   cấu hình chi_local) KHÔNG BAO GIỜ được gửi tới nhà cung cấp đám mây, trong mọi trường hợp,
   kể cả khi model local hỏng. Hết chuỗi local thì trả câu có kiểm soát, KHÔNG im lặng.
3. Ollama/LM Studio chỉ lắng nghe ở địa chỉ vòng lặp hoặc mạng nội bộ có tường lửa.
   Mọi truy cập từ ngoài đi qua ứng dụng này, không đi thẳng vào bộ chạy.
4. Không ghi khoá API, mật khẩu, chuỗi kết nối vào mã nguồn; không ghi nội dung tin nhắn hay câu trả
   lời vào nhật ký (chỉ ghi độ dài và số token).

## Quy tắc kỹ thuật của dự án (những điều rule chung không nói)
5. Tên model, thứ tự chuỗi, hồ sơ GPU, giá và ngưỡng chỉ khai báo trong config/*.yaml.
6. Ghim thẻ model đầy đủ kèm mức lượng tử hoá, ví dụ qwen3.5:9b-q4_K_M.
7. Mọi lượt gọi mô hình ghi: nguồn, tầng, bậc, model, token vào/ra, chi phí, độ trễ,
   thời gian nạp model, tốc độ token/giây, ma_yeu_cau.
8. Chat phát theo dòng (SSE); POST /chat không phát theo dòng chỉ cho tích hợp máy với máy.
9. Mọi lời gọi ra ngoài có timeout tường minh và số lần thử lại rõ ràng.
10. ma_yeu_cau truyền xuyên suốt, có trong mọi dòng nhật ký và mọi phản hồi lỗi.
11. Mọi phép tính token dùng dem_token(); mọi con số nghiệp vụ do công cụ tính, không do model.
12. Trần tự chủ L2: chỉ tra cứu, diễn giải, soạn thảo; không có trường hop_le hay duoc_duyet.

## Phạm vi làm việc
Chỉ sửa: .agents/, backend/, frontend/, config/, prompts/, eval/, scripts/, deploy/, docs/, data/mau/
và các tệp gốc: AGENTS.md, README.md, CHANGELOG.md, docker-compose.yml, .env.example, .gitignore,
.markdownlint.json, .markdownlint-cli2.jsonc.

## Phải hỏi trước khi làm
- Thêm thư viện mới (Python hoặc npm)
- Đổi lược đồ cơ sở dữ liệu ngoài migration đã được giao
- Thêm dịch vụ mới vào docker-compose
- Xoá tệp
- Đổi thứ tự chuỗi định tuyến hoặc nới lỏng bất kỳ quy tắc tuyệt đối nào
- Sửa bất kỳ tệp nào trong .agents/rules/

## Không làm ở giai đoạn hiện tại (cập nhật cuối mỗi giai đoạn)
- RAG và cơ sở dữ liệu vector (Giai đoạn 6)
- Gọi công cụ (Giai đoạn 7)
- Đăng nhập một lần doanh nghiệp (Giai đoạn 8)
- Cổng AI riêng, Redis (Giai đoạn 9)
- Kubernetes, vLLM, nhiều GPU (Giai đoạn 10)
- Tinh chỉnh mô hình (Giai đoạn 11)
Đây là quyết định phạm vi có chủ đích, không phải thiếu sót.

## Các điểm móc phải giữ nguyên chỗ
- kiem_duyet_dau_vao() và kiem_duyet_dau_ra() trong backend/app/core/bao_mat.py.
- lay_nguoi_dung_hien_tai() trong backend/app/core/xac_thuc.py: thay ruột theo giai đoạn
  (người dùng giả -> JWT nội bộ -> OIDC), mọi nơi khác không đổi.
- nguon_tham_chieu (jsonb) trong bảng luot: chừa cho trích dẫn RAG.

## Cách làm việc
- Trước khi viết mã, nêu các tệp sẽ tạo hoặc sửa và rule nào áp dụng.
- Sau mỗi prompt, chạy đủ TỰ ĐÁNH GIÁ và trả bảng Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT.
- Không báo hoàn thành khi còn dòng CHƯA ĐẠT. Phát hành theo .agents/rules/versioning.md.
```

## Phụ lục 2: models.yaml hợp nhất

Rà soát lần cuối ngày 22/09/2026. Tên model của các nhà cung cấp đám mây và thẻ model local đổi vài tháng một lần:
kiểm tra lại mỗi quý bằng `python scripts/kiem_tra_bo_chay.py` và `python scripts/kiem_tra_nha_cung_cap.py`.

| Tầng | Lựa chọn tham khảo (09/2026) | Giá vào / ra (USD mỗi triệu token) | Ghi chú chọn |
| --- | --- | --- | --- |
| 0 Local | Theo hồ sơ GPU (mục B.2) | 0 (chỉ tốn điện và khấu hao) | Ghi tốc độ token/giây thay cho chi phí |
| 1 Gemini | gemini-3.5-flash-lite | 0,30 / 2,50 | Cân bằng tốt cho lưu lượng dự phòng |
| 2 OpenRouter | openrouter/auto | Theo model được chọn | Không phụ phí định tuyến; đặt cost_tier: low |
| 3 Claude | claude-sonnet-5 | Theo bảng giá hiện hành | Cân bằng tốc độ và chất lượng; claude-haiku-4-5 nếu ưu tiên chi phí |
| 4 OpenAI | gpt-5.6-terra | 2,00 / 12,00 | gpt-5.6-luna (0,20 / 1,20) nếu muốn tầng dự phòng cuối cùng rẻ hơn |

```yaml
# config/models.yaml
# Rà soát lần cuối: 22/09/2026 - kiểm tra lại mỗi quý
# Sau khi sửa: python scripts/kiem_tra_bo_chay.py && python scripts/kiem_tra_nha_cung_cap.py

che_do_mac_dinh: local_truoc          # ghi đè bằng biến CHE_DO_DINH_TUYEN

bo_chay:
  loai: ${LOAI_BO_CHAY}                # ollama | lmstudio
  dia_chi: ${DIA_CHI_BO_CHAY}          # http://host.docker.internal:11434/v1
  timeout_giay: 120
  ho_so: ${HO_SO_GPU}                  # gpu6 | gpu8 | gpu12 | gpu16 | gpu24

ho_so_gpu:
  gpu6:
    so_dong_thoi: 1
    bac:
      - {bac: 1, ten: chinh, model: "qwen3.5:4b-q4_K_M", num_ctx: 8192,  keep_alive: 30m, nhiet_do: 0.3}
      - {bac: 2, ten: nho,   model: "qwen3.5:2b-q4_K_M", num_ctx: 4096,  keep_alive: 30m, nhiet_do: 0.3}
  gpu8:
    so_dong_thoi: 1
    bac:
      - {bac: 1, ten: chinh, model: "qwen3.5:4b-q8_0",   num_ctx: 16384, keep_alive: 30m, nhiet_do: 0.3}
      - {bac: 2, ten: nho,   model: "qwen3.5:2b-q8_0",   num_ctx: 8192,  keep_alive: 30m, nhiet_do: 0.3}
  gpu12:
    so_dong_thoi: 1
    bac:
      - {bac: 1, ten: chinh, model: "qwen3.5:9b-q4_K_M", num_ctx: 16384, keep_alive: 30m, nhiet_do: 0.3}
      - {bac: 2, ten: nho,   model: "qwen3.5:4b-q4_K_M", num_ctx: 8192,  keep_alive: 30m, nhiet_do: 0.3}
  gpu16:
    so_dong_thoi: 2
    bac:
      - {bac: 1, ten: chinh, model: "qwen3.5:9b-q4_K_M", num_ctx: 32768, keep_alive: 30m, nhiet_do: 0.3}
      - {bac: 2, ten: nho,   model: "qwen3.5:2b-q8_0",   num_ctx: 8192,  keep_alive: 30m, nhiet_do: 0.3}
  gpu24:
    so_dong_thoi: 1
    bac:
      - {bac: 1, ten: chinh, model: "qwen3.5:27b-q4_K_M", num_ctx: 16384, keep_alive: 30m, nhiet_do: 0.3}
      - {bac: 2, ten: nho,   model: "qwen3.5:9b-q4_K_M",  num_ctx: 16384, keep_alive: 30m, nhiet_do: 0.3}

chuoi_dam_may:                         # thứ tự này quyết định thứ tự thử
  - tang: 1
    ten: gemini
    model: gemini/gemini-3.5-flash-lite
    api_key_env: GOOGLE_API_KEY
    gia_vao_usd_moi_trieu: 0.30
    gia_ra_usd_moi_trieu: 2.50
    cua_so_ngu_canh: 1000000
    timeout_giay: 60
  - tang: 2
    ten: openrouter_auto
    model: openrouter/auto
    api_key_env: OPENROUTER_API_KEY
    tham_so_them: {cost_tier: low}
    gia_vao_usd_moi_trieu: 0.50        # ước tính thô, model thực dùng đọc từ phản hồi
    gia_ra_usd_moi_trieu: 3.00
    cua_so_ngu_canh: 128000
    timeout_giay: 90
    ghi_chu: "Không tiền định - chỉ dùng làm dự phòng"
  - tang: 3
    ten: claude
    model: anthropic/claude-sonnet-5
    api_key_env: ANTHROPIC_API_KEY
    gia_vao_usd_moi_trieu: null        # điền theo bảng giá hiện hành
    gia_ra_usd_moi_trieu: null
    cua_so_ngu_canh: 200000
    timeout_giay: 90
  - tang: 4
    ten: openai
    model: openai/gpt-5.6-terra
    api_key_env: OPENAI_API_KEY
    gia_vao_usd_moi_trieu: 2.00
    gia_ra_usd_moi_trieu: 12.00
    cua_so_ngu_canh: 400000
    timeout_giay: 90

# Model nhúng (từ Giai đoạn 6) KHÔNG khai báo ở đây mà ở config/rag.yaml:
#   model_nhung: bge-m3 (tên logic, MỘT model cho mỗi chỉ mục), so_chieu: 1024,
#   the_nhung_theo_ho_so: gpu6/gpu8 -> bge-m3-cpu (num_gpu 0, chạy trên RAM), hồ sơ khác -> bge-m3.
#   Mất model nhúng thì lùi về tìm theo từ khoá, không rơi sang model nhúng khác.

cai_dat_chung:
  so_lan_thu_lai_moi_tang: 2           # đám mây: nhân đôi giãn cách, có nhiễu ngẫu nhiên
  so_lan_thu_lai_moi_bac: 1            # local
  giay_gian_cach_dau: 0.5
  gioi_han_token_ra: 1024
  nguong_hang_doi_ha_cap: 3            # hàng đợi dài hơn thì dùng bậc 2
  ngu_canh_du_phong_token: 512         # chừa cho câu trả lời
  he_so_an_toan_token: 1.15
  nguong_ty_le_roi_tang: 0.20          # cảnh báo khi hơn 20% lượt không do tầng đầu chuỗi phục vụ
```

## Phụ lục 3: Sự kiện phát theo dòng và mã lỗi

Sự kiện Server-Sent Events của POST /chat/stream. Mỗi sự kiện là một dòng `event:` và một dòng `data:` chứa JSON.
Header bắt buộc: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

| Sự kiện | Dữ liệu | Khi nào phát |
| --- | --- | --- |
| hang_doi | vi_tri, uoc_luong_giay | Ngay khi yêu cầu vào hàng đợi của tầng local; cập nhật khi vị trí đổi |
| bat_dau | hoi_thoai_id, nguon, tang, model, da_cat_ngu_canh, so_luot_bi_cat | Khi tầng phục vụ đã được chọn và trả mảnh đầu tiên |
| manh | noi_dung | Từng mẩu văn bản |
| xong | token_vao, token_ra, chi_phi_usd, toc_do_tok_s, do_tre_ms, nguon, tang, model, trich_dan, nhan_ai | Kết thúc thành công; trich_dan có từ Giai đoạn 6 |
| loi | ma, thong_diep, ma_yeu_cau, phan_da_nhan | Lỗi; nếu đã phát mảnh thì giữ nguyên phần đã nhận, không phát lại từ đầu |

Mọi lỗi HTTP trả JSON dạng `{"loi": {"ma", "thong_diep", "ma_yeu_cau"}}`. Thông điệp viết tiếng Việt dễ hiểu; chi
tiết kỹ thuật chỉ ghi vào nhật ký, không bao giờ trả vết ngăn xếp ra ngoài.

| Mã lỗi | HTTP | Tình huống |
| --- | --- | --- |
| DAU_VAO_KHONG_HOP_LE | 422 | Dữ liệu vào sai kiểu hoặc tin nhắn quá dài |
| NOI_DUNG_BI_CHAN | 422 | Móc kiểm duyệt đầu vào chặn |
| NGU_CANH_QUA_DAI | 422 | Riêng lời nhắc hệ thống cộng tin nhắn mới đã vượt ngân sách token |
| CHUA_XAC_THUC | 401 | Thiếu hoặc sai token |
| KHONG_CO_QUYEN | 403 | Vai trò không đủ quyền |
| KHONG_TIM_THAY | 404 | Hội thoại không tồn tại hoặc không thuộc người dùng hiện tại |
| VUOT_HAN_MUC | 429 | Vượt hạn mức; luôn kèm header Retry-After và nêu rõ vượt loại nào |
| HANG_DOI_DAY | 503 | Hàng đợi local đã đầy; từ chối ngay, không để chờ vô hạn |
| VUOT_NGAN_SACH | 503 | Chi phí đám mây trong ngày đã chạm trần |
| BO_CHAY_KHONG_PHAN_HOI | 503 | Bộ chạy local không phản hồi và chính sách không cho rơi sang đám mây |
| HET_CHUOI_DU_PHONG | 503 | Mọi tầng trong chuỗi đều hỏng; kèm lý do từng tầng trong nhật ký |
| QUA_HAN | 504 | Quá thời gian chờ tổng |
| LOI_HE_THONG | 500 | Lỗi không lường trước |

```batbuoc
Từ chối trả lời vì không đủ căn cứ (RAG, Giai đoạn 6) trả HTTP 200 với nội dung "không tìm thấy căn cứ", KHÔNG trả
mã lỗi. Trả mã lỗi cho tình huống này khiến biểu đồ giám sát báo động giả liên tục.
```

## Phụ lục 4: Danh mục kiểm tra trước khi mở

Chạy `python scripts/kiem_tra_truoc_khi_mo.py` (có từ Giai đoạn 5). Kịch bản kiểm tra tự động những dòng đánh dấu
"Máy", và thoát với mã 1 nếu một dòng bắt buộc không đạt. Những dòng đánh dấu "Người" do người vận hành xác nhận.

| # | Hạng mục | Từ giai đoạn | Kiểm bằng |
| --- | --- | --- | --- |
| 1 | .env không nằm trong Git; không còn bí mật trong mã | 1 | Máy |
| 2 | Mọi model khai báo đã có trên bộ chạy; thẻ model đầy đủ | 1 | Máy |
| 3 | Chỉ một nơi gọi model (goi_mo_hinh / goi_nhung) | 2 | Máy |
| 4 | Câu hỏi NHAY_CAM không tạo lời gọi nào tới đám mây | 2 | Máy |
| 5 | keep_alive nằm ở cấp cao nhất của thân JSON gửi Ollama | 2 | Máy |
| 6 | Trần ngân sách chặn TRƯỚC khi gọi model | 2 | Máy |
| 7 | /health trả nhanh, không chạm CSDL; /ready trả 503 khi CSDL hoặc bộ chạy hỏng | 3 | Máy |
| 8 | Phát theo dòng hoạt động qua nginx (chữ hiện dần) | 4 | Máy |
| 9 | Giao diện không gọi ra Internet (font tự host) | 4 | Máy |
| 10 | Mật khẩu băm bcrypt; JWT hết hạn ngắn | 5 | Máy |
| 11 | Hạn mức 4 lớp hoạt động; 429 có Retry-After | 5 | Máy |
| 12 | Nhật ký không chứa nội dung tin nhắn; mọi dòng có ma_yeu_cau | 5 | Máy |
| 13 | Cổng Ollama không gọi được từ máy khác | 5 | Máy |
| 14 | Dữ liệu cá nhân bị che trước khi vào CSDL và nhật ký | 5 | Máy |
| 15 | /docs trả 404 khi MOI_TRUONG=prod; thiếu APP_SECRET thì từ chối khởi động | 5 | Máy |
| 16 | Bộ câu hỏi vàng đạt ngưỡng trên tầng 0 và mọi tầng đám mây đang bật | 5 | Máy |
| 17 | Tài liệu thiếu siêu dữ liệu hiệu lực bị từ chối nạp | 6 | Máy |
| 18 | Ngưỡng từ chối đã hiệu chuẩn, biên an toàn dương | 6 | Máy |
| 19 | Mọi câu trả lời có nhãn "Nội dung do AI tạo" | 6 | Máy |
| 20 | Không phản hồi nào có trường hop_le hoặc duoc_duyet | 7 | Máy |
| 21 | Chủ sở hữu nghiệp vụ và người có quyền ra lệnh dừng đã được chỉ định bằng văn bản | 1 | Người |
| 22 | Một người chưa từng thấy hệ thống đã dùng thử mười phút; ghi lại chỗ vấp | 4 | Người |
| 23 | Điều kiện dừng (mục A.5) đã được phổ biến cho người vận hành | 5 | Người |
| 24 | Bộ câu hỏi vàng do phòng ban nghiệp vụ soạn và ký xác nhận | 5 | Người |

## Phụ lục 5: Bảng thuật ngữ Anh-Việt

Tài liệu dùng thống nhất các thuật ngữ dưới đây. Cột bên phải là cách viết trong tài liệu; thuật ngữ giữ nguyên tiếng
Anh được viết lại y như cột bên trái.

| English term | Thuật ngữ trong tài liệu |
| --- | --- |
| downgrade (local level) | hạ cấp |
| fall back to the next tier | rơi tầng |
| fallback chain | chuỗi dự phòng |
| hybrid chain | chuỗi lai |
| last-resort tier | tầng dự phòng cuối cùng |
| level (local model) | bậc. Bậc 1 chính / bậc 2 nhỏ; phân biệt với tầng |
| routing mode | chế độ định tuyến |
| tier (cloud fallback) | tầng. Tầng 0 đến 4 |
| context window | cửa sổ ngữ cảnh |
| fine-tuning | tinh chỉnh |
| GPU profile | hồ sơ GPU. gpu6 đến gpu24 |
| inference runtime | bộ chạy |
| KV cache | bộ đệm KV. Khác bộ nhớ đệm câu trả lời |
| model (AI model) | model |
| model tag | thẻ model |
| quantization | lượng tử hoá |
| retrieval-augmented generation | RAG |
| system prompt | lời nhắc hệ thống. Văn bản gửi tới model của sản phẩm |
| token | token |
| tool calling | gọi công cụ |
| warm-up | hâm nóng |
| chunking | cắt đoạn |
| citation | trích dẫn |
| embedding | nhúng (vector nhúng) |
| hybrid retrieval | truy hồi lai |
| keyword coverage gate | cổng phủ từ khoá |
| refusal threshold | ngưỡng từ chối |
| reranking | tái xếp hạng |
| vector database | cơ sở dữ liệu vector |
| endpoint | endpoint |
| health check | kiểm tra sức khoẻ |
| quota / rate limit | hạn mức |
| readiness | sẵn sàng |
| Server-Sent Events | SSE |
| streaming | phát theo dòng |
| AI gateway | cổng AI. Luôn viết đủ "cổng AI" |
| concurrency limit | giới hạn đồng thời |
| container | container |
| Docker Compose profile | profile. Phân biệt với hồ sơ GPU |
| proxy buffering | gom đệm của proxy |
| queue | hàng đợi |
| response cache | bộ nhớ đệm. Redis ở Giai đoạn 9 |
| virtual key | khoá ảo |
| port | cổng. Cổng 8080; phân biệt với cổng AI |
| audit log | nhật ký kiểm toán |
| request ID | mã yêu cầu |
| structured log | nhật ký có cấu trúc |
| moderation hook | móc kiểm duyệt |
| PII masking | che dữ liệu cá nhân |
| prompt injection | tiêm lời nhắc |
| single sign-on (SSO) | đăng nhập một lần |
| autonomy level | mức tự chủ |
| budget cap | trần ngân sách |
| golden question set | bộ câu hỏi vàng |
| regression evaluation | đánh giá hồi quy |
| build metadata | siêu dữ liệu bản dựng |
| pre-release | bản phát hành thử nghiệm |
| release | phát hành |
| version tag | thẻ phiên bản |
| observability | quan sát |
| production environment | môi trường vận hành |
| backend | backend |
| frontend | frontend |
| admin dashboard | bảng quản trị |
| reference model (architecture) | mô hình tham chiếu |
| prompt (task given to the IDE agent) | prompt. Đơn vị giao việc: PROMPT 1 đến PROMPT 55 |
| self-assessment | Tự đánh giá |
| stage-closing prompt | prompt chốt giai đoạn |
| agent | agent |
