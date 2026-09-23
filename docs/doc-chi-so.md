# Hướng dẫn theo dõi và phân tích chỉ số vận hành (Metrics Guide)

Tài liệu này hướng dẫn cán bộ quản trị và vận hành hệ thống trợ lý AI
nội bộ đọc hiểu các chỉ số kỹ thuật, giám sát tình trạng tài nguyên GPU,
bộ chạy cục bộ (Ollama / LM Studio) và chuỗi định tuyến đám mây.

## 1. Đọc chỉ số thế nào

Hệ thống cung cấp các nhóm chỉ số thông qua API `/api/v1/chi-so` và
giao diện quản trị bộ chạy `/quan-tri/bo-chay` (API `/api/v1/giam-sat/bo-chay`).
Dưới đây là các tình huống vận hành điển hình và cách nhận diện:

### 1.1. Chỉ số cho biết cần tăng `keep_alive`

- **Tỷ lệ chờ nạp (`ty_le_cho_nap`) cao**: Trong nhóm chỉ số `thoi_gian_nap_ms`,
  nếu tỷ lệ lượt yêu cầu phải chờ nạp mô hình vượt quá 20% - 30%, điều đó
  cho thấy mô hình thường xuyên bị giải phóng khỏi VRAM giữa các câu hỏi.
- **Cảnh báo liên tiếp từ tác vụ nền**: Nhật ký ghi cảnh báo:
  `Model bậc 1 (...) không còn trong bộ nhớ 3 lần liên tiếp. Gợi ý tăng keep_alive`.
- **Thời gian còn lại (`so_giay_con_lai`) thường xuyên về 0**: Người dùng gặp
  độ trễ ban đầu lớn (5 - 15 giây) cho mỗi câu hỏi do Ollama phải nạp lại
  mô hình từ ổ đĩa vào VRAM.
- **Hành động xử lý**: Tăng giá trị `keep_alive` trong mục `local_chung`
  tại `config/models.yaml` (ví dụ từ `30m` lên `60m` hoặc `2h`).

### 1.2. Chỉ số cho biết cần giảm `num_ctx` hoặc đổi `HO_SO_GPU`

- **VRAM còn trống (`vram_con_trong_gb`) tiến sát 0**: Khi VRAM thực tế
  hoặc ước tính bị chiếm dụng gần hết, bộ chạy có nguy cơ sập hoặc tràn sang RAM.
- **Xuất hiện lỗi tràn bộ nhớ (503 hoặc Out of Memory)**: Bộ chạy trả mã lỗi 503
  khi tiếp nhận ngữ cảnh vượt quá khả năng cấp phát của GPU.
- **Tỷ lệ cắt ngữ cảnh (`ty_le_cat_ngu_canh`) tăng cao**: Lịch sử hội thoại
  bị cắt liên tục khiến mô hình mất ngữ cảnh của các lượt trao đổi trước.
- **Cờ lệch ngữ cảnh (`co_lech = true`)**: Kích thước ngữ cảnh thực tế
  (`num_ctx_thuc_te`) nhỏ hơn cấu hình (`num_ctx_cau_hinh`), do bộ chạy
  tự động ép giảm context để vừa vặn với dung lượng VRAM còn lại.
- **Hành động xử lý**:
  - Giảm `num_ctx` của bậc chính hoặc bậc nhỏ trong `config/models.yaml`.
  - Nếu máy trạm có VRAM hạn chế (dưới 8 GB), chuyển biến `HO_SO_GPU` từ `gpu8`
    về `gpu6`.
  - Nếu câu hỏi dài bị cắt nhiều và phần cứng máy chủ cho phép, nâng `HO_SO_GPU`
    lên `gpu12`, `gpu16` hoặc `gpu24`.

### 1.3. Chỉ số cho biết cần hạ `SO_LUONG_DONG_THOI`

- **Độ dài hàng đợi (`do_dai_hang_doi`) tăng nhưng GPU bị nghẽn**: Hàng đợi
  có nhiều yêu cầu đang chờ (`dang_cho > 0`), thời gian chờ trung vị tăng cao.
- **Tốc độ sinh token (`toc_do_tok_s`) tụt dốc nghiêm trọng**: Tốc độ xử lý
  của mô hình local giảm xuống dưới 10 tok/s do tài nguyên tính toán (Compute Core)
  của GPU bị chia sẻ cho quá nhiều luồng song song.
- **Xuất hiện lượt bị từ chối hàng đợi**: Chỉ số `so_bi_tu_choi_1_gio > 0`
  (vượt quá ngưỡng `do_dai_hang_doi_toi_da`).
- **Hành động xử lý**: Giảm giá trị `SO_LUONG_DONG_THOI` trong `.env`
  (hoặc `num_parallel` trong hồ sơ GPU của `config/models.yaml`) về mức 1 hoặc 2
  để dồn năng lực tính toán xử lý tuần tự dứt điểm từng lượt hội thoại.

### 1.4. Chỉ số cho biết tầng đám mây đang phải chịu tải quá lớn

- **Tỷ lệ rơi tầng (`ty_le_roi_tang_dam_may`) vượt ngưỡng**: Vượt ngưỡng
  `nguong_ty_le_roi_tang` (mặc định 20%), nghĩa là hơn 20% số câu hỏi
  phải chuyển tiếp ra ngoài Internet để xử lý.
- **Tốc độ tiêu hao ngân sách ngày (`phan_tram_da_dung`) tăng đột biến**:
  Chi phí USD trong ngày chạm hoặc vượt `nguong_canh_bao_ngan_sach` (80%)
  ngay trong ca làm việc buổi sáng.
- **Tỷ lệ hạ cấp local (`ty_le_ha_cap_local`) hoặc lỗi local tăng vọt**:
  Bộ chạy local bị gián đoạn hoặc quá tải, kích hoạt cơ chế hạ cấp đẩy các
  yêu cầu thông thường ra chuỗi đám mây (Gemini -> OpenRouter -> Claude -> OpenAI).
- **Hành động xử lý**:
  - Kiểm tra trạng thái tiến trình Ollama/LM Studio tại máy chủ host.
  - Đối chiếu nhật ký chặng `chang=trang_thai_bo_chay` để xác định nguyên nhân
    bộ chạy bị treo hoặc ngắt kết nối.
  - Rà soát các truy vấn nhạy cảm bị từ chối (dữ liệu `NHAY_CAM` luôn được bảo vệ,
    không bao giờ rơi ra đám mây theo Quy tắc tuyệt đối 2).

## 2. Bảng tổng hợp đối chiếu chỉ số

| Chỉ số / Hiện tượng | Ngưỡng cảnh báo | Nguyên nhân cốt lõi | Hành động đề xuất |
| :--- | :--- | :--- | :--- |
| `ty_le_cho_nap` | > 20% | Model bị giải phóng quá sớm | Tăng `keep_alive` lên 60m hoặc 2h |
| `co_lech` | `true` | VRAM không đủ cho `num_ctx` | Giảm `num_ctx` hoặc hạ `HO_SO_GPU` |
| `toc_do_tok_s` | < 10 tok/s | Tranh chấp nhân xử lý GPU | Giảm `SO_LUONG_DONG_THOI` |
| `ty_le_roi_tang` | > 20% | Local quá tải hoặc bị lỗi | Kiểm tra bộ chạy local, khởi động lại |
| `phan_tram_da_dung` | > 80% | Gọi đám mây quá nhiều | Tối ưu hóa chuỗi local, giám sát hạn mức |

## 3. Quy trình kiểm tra định kỳ cho quản trị viên

1. **Hàng ngày**: Truy cập giao diện `/quan-tri/bo-chay` kiểm tra trạng thái
   model đang nạp, dung lượng VRAM còn trống và cờ lệch ngữ cảnh.
2. **Hàng tuần**: Đánh giá báo cáo chi phí `/api/v1/chi-phi` và tỷ lệ rơi tầng
   trong 7 ngày gần nhất để cân đối ngân sách mô hình đám mây.
3. **Khi bảo trì**: Đối chiếu VRAM đo bằng `nvidia-smi` trên hệ điều hành host
   với số liệu ước tính hiển thị trên giao diện quản trị.
