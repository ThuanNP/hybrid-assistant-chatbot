# QUY ƯỚC NỘI BỘ (không đưa vào tệp Word) — mọi người viết bản nháp PHẢI tuân theo

## 1. Cú pháp bản nháp (bộ chuyển md_sang_docx.py chỉ hiểu các dạng sau)

- `# ` = tiêu đề cấp 1 (PHẦN A/B/C, PHỤ LỤC). `## ` = cấp 2 (A.1, B.2, "Giai đoạn N: <tên>"). `### ` = cấp 3
  ("PROMPT N. <tên>", mục con). `#### ` = cấp 4 (hiếm dùng).
- Đoạn văn thường: một dòng dài hoặc nhiều dòng liền nhau (sẽ nối lại). Cách đoạn bằng MỘT dòng trống.
- In đậm `**...**`, mã nội dòng `` `...` ``. KHÔNG dùng in nghiêng, KHÔNG dùng link markdown, KHÔNG dùng HTML.
- Danh sách: `- ` (dấu chấm tròn) và `1. ` (đánh số). Cấp 2 thụt 2 dấu cách. Không quá 2 cấp.
- Bảng: dạng pipe, dòng thứ 2 là `| --- | --- |`. Trong ô không xuống dòng; dùng "; " để ngăn ý.
- Khối rào (fenced) với nhãn — CHỈ các nhãn sau:
  - ```` ```prompt ```` : nội dung giao việc cho agent (ô nền xám, Consolas). Văn bản thuần, dùng ngoặc kép thẳng `"`.
  - ```` ```danhgia ```` : mục Tự đánh giá hiển thị riêng (ô nền #F0F4F8). Mỗi dòng: lệnh, rồi `# kỳ vọng: ...`.
  - ```` ```batbuoc ```` : hộp BẮT BUỘC (nền vàng nhạt). Văn bản thuần, có thể nhiều đoạn.
  - ```` ```meo ```` : hộp MẸO (nền xanh nhạt).
  - ```` ```bash ````, ```` ```yaml ````, ```` ```text ````, ```` ```nginx ````, ```` ```json ````, ```` ```python ````,
    ```` ```dockerfile ```` : khối mã thông thường.
- Ký tự: tiếng Việt có dấu (UTF-8). Dấu gạch ngang dài "—" chỉ dùng trong văn xuôi, KHÔNG dùng trong tiêu đề
  "Giai đoạn N: ...". Không emoji.

## 2. Khuôn MỘT giai đoạn (bắt buộc, đúng thứ tự)

```text
## Giai đoạn N: <Tên giai đoạn>

<Một câu thao tác Antigravity, văn phong tài liệu gốc. Ví dụ: "Mở workspace business-assistant-chatbot trong
Antigravity, chọn Editor View. Bảo đảm Ollama đang chạy và docker compose up -d đã khởi động db.">

**Mục tiêu giai đoạn.** <1–2 câu>

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| <việc 1> | <việc chưa làm> → Giai đoạn M |
| ... | ... |

**Điều kiện hoàn thành**

- <tiêu chí kiểm được 1>
- ...
- Gắn thẻ git: `git tag giai-doan-N`

### PROMPT k. <Tên>
...
```

Số dòng bảng LÀM/CHƯA LÀM: lấy số lớn hơn của hai cột; ô trống để trống. CHƯA LÀM luôn có "→ Giai đoạn M" (hoặc
"→ ngoài phạm vi tài liệu" cho mục không bao giờ làm).

## 3. Khuôn MỘT prompt (bắt buộc, đúng thứ tự)

```text
### PROMPT k. <Tên ngắn>

**Chế độ:** Editor View · **Đọc Plan:** Có        (hoặc Manager Surface / Không)

**Mục tiêu.** <1–2 câu: vì sao prompt này quan trọng>

**Làm trước.** <tuỳ chọn — chỉ khi Đọc Plan: Có; nêu 1–2 điều phải kiểm trong Implementation Plan>

```prompt
Đọc AGENTS.md trước. <Nội dung giao việc chi tiết, đánh số 1., 2., ... tên tệp, tên hàm, chữ ký hàm, hành vi bắt
buộc, kiểm thử phải viết.>

<Nếu Đọc Plan: Có, dòng cuối trước phần TỰ ĐÁNH GIÁ:> Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. <lệnh> -> kỳ vọng: <kết quả>
2. ...
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- <yêu cầu trả về cụ thể, kiểm được: tệp nào, hành vi nào, con số nào>
- ... (3–6 dòng)

**Tự đánh giá**

```danhgia
<lệnh 1>   # kỳ vọng: ...
<lệnh 2>   # kỳ vọng: ...
```

```batbuoc
<tuỳ chọn: điều không được vi phạm + lý do>
```

```meo
<tuỳ chọn: kinh nghiệm>
```
```

- Mỗi prompt có ĐỦ: Chế độ, Mục tiêu, khối prompt (có đoạn TỰ ĐÁNH GIÁ ở cuối), Agent phải trả về, Tự đánh giá
  (danhgia). BẮT BUỘC và MẸO: có khi có nội dung thật, mỗi giai đoạn nên có ít nhất 2 hộp BẮT BUỘC/MẸO.
- Các bước trong danhgia phải KHỚP với các bước TỰ ĐÁNH GIÁ trong khối prompt.
- Lệnh dùng cú pháp bash (Antigravity trên Windows có Git Bash/WSL); với lệnh chỉ có ở Windows, ghi thêm dạng PowerShell.
- Độ dài khối prompt: 20–60 dòng. Viết cụ thể như tài liệu gốc — tên tệp, tên hàm, trường dữ liệu, mã lỗi.

## 4. Bối cảnh và thương hiệu

- Đơn vị sử dụng: "Doanh nghiệp kinh doanh điện năng" (viết thường khi trong câu: doanh nghiệp kinh doanh điện năng).
- Người dùng: "Cán bộ, công nhân viên của Doanh nghiệp kinh doanh điện năng" — trợ lý NỘI BỘ.
- Tên dự án/workspace/thư mục gốc: `business-assistant-chatbot`. Tên hiển thị giao diện: "Trợ lý nội bộ".
- CẤM: "EVN", "EVNHCMC", "SmartPro", tên bất kỳ tập đoàn/công ty/đơn vị có thật, số hotline thật. Email mẫu
  `@vidu.com`. Tên miền mẫu `tro-ly.vidu.com`. Alias model ở cổng AI: `tro-ly-chat`, `tro-ly-nhung`.
- Không đánh số phiên bản kiểu v0.1, v1.1, v2.0 ở bất kỳ đâu. Gọi "Giai đoạn N". Chỉ ngoại lệ: phiên bản thư viện,
  `prompts/he_thong.md` có dòng "phien_ban: 2026-09-22.1" (dạng ngày), thẻ model.
- Phòng ban mẫu: KINH_DOANH, KY_THUAT, AN_TOAN, CHAM_SOC_KHACH_HANG, CNTT.
- Dữ liệu mẫu đều là dữ liệu GIẢ: mã khách hàng dạng `KH00012345`, SĐT `0900000001`.
- Trần tự chủ L2: AI chỉ tra cứu, diễn giải, soạn thảo; con người ký duyệt. Không có trường "hop_le"/"duoc_duyet".
- Giọng văn trợ lý (prompts/he_thong.md): xưng "Trợ lý nội bộ", gọi "Anh/Chị"; số tiền `1.450.000 đ`, điện năng
  `320 kWh`, thời gian `dd/mm/yyyy - HH:mm`; vượt thẩm quyền thì hướng dẫn liên hệ bộ phận phụ trách.

## 5. Cây thư mục dự án (chốt ở PROMPT 2)

```text
business-assistant-chatbot/
  AGENTS.md  README.md  CHANGELOG.md  .gitignore  .env.example  docker-compose.yml
  backend/
    Dockerfile  pyproject.toml (hoặc requirements.txt)  alembic.ini  alembic/
    app/
      main.py  config.py
      llm/        router.py  bo_chay_local.py  nha_cung_cap_dam_may.py  chinh_sach.py  dem_token.py  chi_phi.py
      chat/       hoi_thoai.py  ngu_canh.py  su_kien_sse.py
      hang_doi/   dieu_phoi.py
      core/       nhat_ky.py  han_muc.py  bao_mat.py  xac_thuc.py  loi.py  csdl.py
      giam_sat/   suc_khoe.py  chi_so.py
      eval/       runner.py  cham_diem.py
      rag/        (Giai đoạn 6) nap_tai_lieu.py  cat_doan.py  nhung.py  truy_hoi.py  tai_xep_hang.py  nguong.py  service.py
      cong_cu/    (Giai đoạn 7) khung.py  may_tinh.py  tra_cuu_nghiep_vu.py
      quan_tri/   (Giai đoạn 8) api.py
    tests/
  frontend/     (Angular workspace, Giai đoạn 4)
    src/app/ core/ (api.service.ts, sse.service.ts, auth/...) features/chat/ features/hoi-thoai/ features/quan-tri/ shared/
    nginx.conf  Dockerfile
  config/       models.yaml  chinh_sach_du_lieu.yaml (Giai đoạn 2)  rag.yaml (Giai đoạn 6)
  prompts/      he_thong.md  cham.md  tieu_de.md
  eval/         bo_cau_hoi.yaml  bo_cau_hoi_rag.yaml  cau_hoi_co_trong_kho.txt  cau_hoi_ngoai_kho.txt
  scripts/      kiem_tra_bo_chay.py  kiem_tra_nha_cung_cap.py  do_toc_do.py  tao_nguoi_dung.py  kiem_tra_phoi_lo.py
                kiem_tra_truoc_khi_mo.py  nap_tai_lieu.py  hieu_chuan_nguong.py
  deploy/       ollama.service (systemd)  nginx-ollama.conf  helm/ (Giai đoạn 10)  keycloak/ (Giai đoạn 8)
                litellm/ (Giai đoạn 9)  giam_sat/ (Giai đoạn 9)
  training/     (Giai đoạn 11)
  docs/         go-loi.md  doc-chi-so.md  ...
  data/mau/     tài liệu mẫu giả cho RAG
```

## 6. Tên hàm/kiểu công khai (chốt)

- `app/llm/router.py`:
  - `async def goi_mo_hinh(tin_nhan: list[dict], *, nguoi: NguoiDung, ma_yeu_cau: str, nhan_du_lieu: NhanDuLieu = NhanDuLieu.THUONG, phat_theo_dong: bool = False, **tuy_chon) -> KetQuaGoi`
  - `async def goi_mo_hinh_theo_dong(...) -> AsyncIterator[ManhPhatRa]`
  - `async def goi_nhung(van_ban: list[str], *, ma_yeu_cau: str) -> KetQuaNhung` (thêm ở Giai đoạn 6)
  - HÀM DUY NHẤT được gọi model. Cấm gọi httpx tới bộ chạy hoặc litellm ở nơi khác.
- `KetQuaGoi`: noi_dung, nguon ("local"|"dam_may"), tang (0 = local, 1..4 = đám mây), bac_local (1|2|None), ten_model,
  token_vao, token_ra, chi_phi_usd, do_tre_ms, thoi_gian_nap_ms, toc_do_tok_s, so_lan_thu, danh_sach_tang_da_hong,
  da_cat_ngu_canh, so_luot_bi_cat.
- `ManhPhatRa`: loai ("manh"|"xong"|"loi"), noi_dung, ket_qua (KetQuaGoi khi xong).
- `app/llm/chinh_sach.py`: `def xac_dinh_chuoi(nguoi, nhan_du_lieu, che_do) -> list[Tang]`; enum
  `CheDoDinhTuyen = chi_local | local_truoc | dam_may_truoc`; enum `NhanDuLieu = THUONG | NHAY_CAM`;
  `def phat_hien_nhay_cam(van_ban) -> bool` (mã khách hàng, SĐT, số công tơ, CCCD).
- `app/llm/bo_chay_local.py`: `async def goi_local(...)`, `async def ham_nong()`, `async def doc_ngu_canh_thuc_te(model)`,
  lớp giao diện `BoChay` với 2 hiện thực `BoChayOllama`, `BoChayLMStudio`.
- `app/llm/nha_cung_cap_dam_may.py`: `async def goi_dam_may(tang, ...)`, phân loại lỗi `LoiTamThoi | LoiVinhVien | LoiDauVao`.
- `app/llm/dem_token.py`: `def dem_token(van_ban: str) -> int` (tiktoken cl100k_base, hệ số an toàn 1.15).
- `app/chat/ngu_canh.py`: `def dung_ngu_canh(lich_su, tin_nhan_moi, chuoi: list[Tang]) -> KetQuaNguCanh(danh_sach, da_cat, so_luot_bi_cat)`.
- `app/hang_doi/dieu_phoi.py`: `class DieuPhoi` với `async def vao_hang(ma_yeu_cau) -> ViTri`, semaphore SO_LUONG_DONG_THOI.
- `app/core/xac_thuc.py`: `async def lay_nguoi_dung_hien_tai(...) -> NguoiDung` (id, ten_dang_nhap, vai_tro, bac, phong_ban, pham_vi_doc, che_do_dinh_tuyen).
  Giai đoạn 3–4 trả người dùng giả cố định khi `XAC_THUC_GIA=true` (chỉ dev); Giai đoạn 5 hiện thực JWT local; Giai đoạn 8 thay ruột OIDC.
- `app/core/bao_mat.py`: `async def kiem_duyet_dau_vao(noi_dung, nguoi) -> KetQuaKiemDuyet`,
  `async def kiem_duyet_dau_ra(noi_dung, nguoi) -> KetQuaKiemDuyet`, `def che_du_lieu_ca_nhan(van_ban) -> KetQuaChe`
  (thẻ đánh số `<SO_DIEN_THOAI_1>`, `<MA_KHACH_HANG_1>`, `restore()`), `def kiem_tra_phoi_lo()`.
- `app/rag/service.py` (Giai đoạn 6): `async def tra_loi_co_can_cu(cau_hoi, nguoi, ma_yeu_cau)`; `truy_hoi_lai(...)`.

## 7. Biến môi trường (chốt tên)

MOI_TRUONG (dev|prod), CHE_DO_DINH_TUYEN (chi_local|local_truoc|dam_may_truoc), LOAI_BO_CHAY (ollama|lmstudio),
DIA_CHI_BO_CHAY (vd http://host.docker.internal:11434/v1), HO_SO_GPU (gpu6|gpu8|gpu12|gpu16|gpu24),
GOOGLE_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, DATABASE_URL, POSTGRES_USER, POSTGRES_PASSWORD,
POSTGRES_DB, APP_SECRET, CORS_ORIGINS, NGAN_SACH_NGAY_USD, HAN_MUC_MOI_NGUOI_GIO, HAN_MUC_IP_PHUT,
HAN_MUC_TOKEN_NGAY, SO_LUONG_DONG_THOI, DO_DAI_HANG_DOI_TOI_DA, TIMEOUT_GIAY, GHI_NOI_DUNG, XAC_THUC_GIA,
(Giai đoạn 8) OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_AUDIENCE, (Giai đoạn 9) REDIS_URL, LITELLM_URL, LITELLM_KEY,
LANGFUSE_*, (Giai đoạn 6) MODEL_NHUNG.

## 8. Cơ sở dữ liệu (chốt tên bảng)

- Giai đoạn 3: `nguoi_dung` (id, ten_dang_nhap, mat_khau_bam, ho_ten, vai_tro, bac, phong_ban, dang_hoat_dong, tao_luc),
  `hoi_thoai` (id, nguoi_id, tieu_de, tao_luc, cap_nhat_luc, da_xoa),
  `luot` (id, hoi_thoai_id, vai_tro he_thong|nguoi_dung|tro_ly, noi_dung (đã che), nguon, tang, bac_local, model_da_dung,
  token_vao, token_ra, chi_phi_usd, toc_do_tok_s, thoi_gian_nap_ms, do_tre_ms, da_cat_ngu_canh, so_luot_bi_cat,
  nhan_du_lieu, nguon_tham_chieu jsonb, phien_ban_loi_nhac, ma_yeu_cau, tao_luc),
  `luot_goi` (thoi_diem, nguoi_id, nguon, tang, model, token_vao, token_ra, chi_phi_usd, do_tre_ms, thanh_cong, ma_yeu_cau).
- Giai đoạn 5: `nhat_ky_kiem_toan`, `han_muc_dem` (cửa sổ trượt).
- Giai đoạn 6: `tai_lieu` (id, ma_tai_lieu, tieu_de, nguon, tinh_trang con_hieu_luc|het_hieu_luc|du_thao, pham_vi_doc text[],
  van_ban_thay_the, ngay_ban_hanh, ngay_het_hieu_luc, model_nhung, cap_nhat_luc), `doan` (id, tai_lieu_id, tieu_de_muc,
  noi_dung, vector vector(1024), tsv tsvector).
- Giai đoạn 8: `phong_ban`, `anh_xa_nhom`.

## 9. Sự kiện SSE (chốt)

`hang_doi {vi_tri, uoc_luong_giay}` · `bat_dau {hoi_thoai_id, nguon, tang, model, da_cat_ngu_canh, so_luot_bi_cat}` ·
`manh {noi_dung}` · `xong {token_vao, token_ra, chi_phi_usd, toc_do_tok_s, do_tre_ms, nguon, tang, model, trich_dan[] (Giai đoạn 6), nhan_ai}` ·
`loi {ma, thong_diep, ma_yeu_cau, phan_da_nhan}`.
Header: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

## 10. Mã lỗi (chốt)

HANG_DOI_DAY (503), QUA_HAN (504), NGU_CANH_QUA_DAI (422), BO_CHAY_KHONG_PHAN_HOI (503), HET_CHUOI_DU_PHONG (503),
VUOT_HAN_MUC (429 + Retry-After), VUOT_NGAN_SACH (503), KHONG_CO_QUYEN (403), CHUA_XAC_THUC (401),
DAU_VAO_KHONG_HOP_LE (422), NOI_DUNG_BI_CHAN (422), KHONG_TIM_THAY (404), LOI_HE_THONG (500).
Mọi lỗi trả `{"loi": {"ma", "thong_diep", "ma_yeu_cau"}}`. Từ chối vì không đủ căn cứ (RAG) = HTTP 200.

## 11. Chuỗi định tuyến (chốt)

- Tầng 0 = LOCAL (bậc 1 "chinh", bậc 2 "nho" theo HO_SO_GPU). Tầng 1 Gemini, 2 OpenRouter/auto, 3 Claude, 4 OpenAI.
- `local_truoc` (mặc định): 0 → 1 → 2 → 3 → 4. `dam_may_truoc`: 1 → 2 → 3 → 4 → 0. `chi_local`: chỉ 0; hết chuỗi thì
  trả câu có kiểm soát "hệ thống đang bận".
- NHAY_CAM (tự phát hiện hoặc phòng ban cấu hình) → luôn `chi_local`, bất kể CHE_DO_DINH_TUYEN. Có kiểm thử khẳng định
  không lời gọi mạng nào tới nhà cung cấp đám mây.
- Local: hạ cấp bậc 1 → bậc 2 khi quá hạn/5xx/hàng đợi > nguong_hang_doi_ha_cap; 4xx do yêu cầu sai thì không hạ cấp.
- Đám mây: lỗi tạm thời (429/5xx/timeout) thử lại rồi rơi tầng; lỗi vĩnh viễn (401/403/404) rơi ngay; lỗi đầu vào (400)
  ném lên, không rơi tầng.
- Streaming: lỗi trước mảnh đầu → rơi tầng êm; lỗi giữa chừng → kết thúc với sự kiện `loi` kèm phần đã nhận, không phát lại.

## 12. Hồ sơ GPU (chốt, Phần B.2 / Phụ lục 2)

| HO_SO_GPU | bậc 1 (chinh) | bậc 2 (nho) | num_ctx b1/b2 | OLLAMA_NUM_PARALLEL |
| --- | --- | --- | --- | --- |
| gpu6 | qwen3.5:4b-q4_K_M | qwen3.5:2b-q4_K_M | 8192 / 4096 | 1 |
| gpu8 | qwen3.5:4b-q8_0 | qwen3.5:2b-q8_0 | 16384 / 8192 | 1 |
| gpu12 | qwen3.5:9b-q4_K_M | qwen3.5:4b-q4_K_M | 16384 / 8192 | 1 |
| gpu16 | qwen3.5:9b-q4_K_M | qwen3.5:2b-q8_0 | 32768 / 8192 | 2 |
| gpu24 | qwen3.5:27b-q4_K_M | qwen3.5:9b-q4_K_M | 16384 / 16384 | 1 |

Model nhúng (Giai đoạn 6): `bge-m3` (1024 chiều, ~1,2 GB VRAM). Luôn kèm câu: thẻ model phải đối chiếu lại bằng
`ollama pull`/thư viện Ollama; kịch bản kiem_tra_bo_chay.py in lệnh kéo còn thiếu.

## 13. Model đám mây (Phụ lục 2, rà soát 22/09/2026 — ghi rõ phải rà lại mỗi quý)

Tầng 1 `gemini/gemini-3.5-flash-lite` (0,30/2,50) · Tầng 2 `openrouter/auto` cost_tier low (ước tính 0,50/3,00) ·
Tầng 3 `anthropic/claude-sonnet-5` (điền theo bảng giá hiện hành) · Tầng 4 `openai/gpt-5.6-terra` (2,00/12,00).
