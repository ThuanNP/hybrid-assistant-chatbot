# Hướng dẫn Gỡ lỗi và Truy vết Nhật ký Hệ thống

Tài liệu này hướng dẫn cách trích xuất `ma_yeu_cau`, truy vết luồng xử lý qua nhật ký
JSON có cấu trúc, và nhận diện ba lỗi vận hành phổ biến nhất của hệ thống trợ lý AI.

## 1. Cách lấy mã yêu cầu (`ma_yeu_cau`)

Mỗi yêu cầu gửi tới hệ thống đều được cấp một định danh 12 ký tự duy nhất (`ma_yeu_cau`).
Mã này được truyền xuyên suốt qua tất cả các lớp nghiệp vụ và ghi vết trong nhật ký.

### Từ Giao diện Người dùng (Frontend)

- Khi một tin nhắn gặp lỗi xử lý, giao diện hiển thị thông báo lỗi màu đỏ kèm theo mã.
- Nhấp vào biểu tượng **Sao chép** bên cạnh mã yêu cầu để đưa mã vào bộ nhớ đệm
  (clipboard) và gửi cho bộ phận hỗ trợ kỹ thuật CNTT.

### Từ Phản hồi HTTP (API)

- **Header HTTP**: Mọi phản hồi HTTP thành công hoặc thất bại đều có header:
  `X-Ma-Yeu-Cau: <chuoi_12_ky_tu>`.
- **Thân phản hồi lỗi (JSON)**: Khi yêu cầu phát sinh lỗi, API trả về cấu trúc:

```json
{
  "loi": {
    "ma": "BO_CHAY_KHONG_PHAN_HOI",
    "thong_diep": "Mô hình nội bộ không phản hồi, vui lòng thử lại sau.",
    "ma_yeu_cau": "a1b2c3d4e5f6"
  }
}
```

## 2. Cách lọc và truy vết nhật ký theo `ma_yeu_cau`

Toàn bộ nhật ký ứng dụng được chuẩn hóa dưới dạng JSON một dòng chứa 22 trường cố định.

### Lọc nhật ký trong môi trường Docker Compose

Sử dụng lệnh `grep` kết hợp với `jq` để định dạng các dòng nhật ký của một yêu cầu:

```bash
# Lọc toàn bộ 7 chặng xử lý của một mã yêu cầu cụ thể
docker compose logs backend | grep "a1b2c3d4e5f6" | jq .
```

### Lọc theo từng chặng xử lý cụ thể

```bash
# Chỉ lọc chặng gọi mô hình của yêu cầu
docker compose logs backend | grep "a1b2c3d4e5f6" | grep "goi_mo_hinh" | jq .
```

## 3. Ba lỗi vận hành thường gặp nhất và cách nhận biết

### Lỗi 1: Rơi tầng liên tục sang đám mây

- **Biểu hiện**: Chi phí đám mây tăng bất thường, độ trễ phản hồi thay đổi.
- **Cách nhận biết trong nhật ký**:
  - Trường `roi_tang` trong bảng `luot_goi` hoặc nhật ký có giá trị `true`.
  - Trường `danh_sach_tang_da_hong` trong chặng `goi_mo_hinh` chứa danh sách các tầng
    bị lỗi trước đó (ví dụ: `[0]` - tầng local bị hỏng).
  - Tầng phục vụ thực tế `tang > 0` trong khi nhãn dữ liệu là thông thường.
- **Nguyên nhân**: Bộ chạy local (Ollama) bị quá tải hàng đợi, tiến trình bị tắt,
  hoặc card GPU bị tràn VRAM.
- **Biện pháp xử lý**:
  - Kiểm tra trạng thái bộ chạy bằng lệnh `docker compose logs ollama` hoặc kịch bản
    `python scripts/kiem_tra_bo_chay.py`.
  - Khởi động lại dịch vụ bộ chạy mô hình nội bộ.

### Lỗi 2: Nạp model nguội (Cold Load) làm tăng độ trễ

- **Biểu hiện**: Yêu cầu đầu tiên sau một khoảng thời gian không có hoạt động phản hồi
  rất chậm (mất từ 5 đến 30 giây để sinh chữ đầu tiên).
- **Cách nhận biết trong nhật ký**:
  - Trường `thoi_gian_nap_ms` tại chặng `goi_mo_hinh` hoặc trong bảng `luot` có giá trị
    dương lớn (ví dụ: `12500.0` tương ứng 12.5 giây).
  - Tỷ lệ `ty_le_cho_nap` tại endpoint `/api/v1/chi-so` vượt quá 0.2 (trên 20% yêu cầu
    phải chờ nạp lại model).
- **Nguyên nhân**: Tham số `keep_alive` trong cấu hình quá ngắn khiến bộ chạy giải phóng
  mô hình khỏi VRAM sau một khoảng thời gian nhàn rỗi.
- **Biện pháp xử lý**:
  - Tăng thời gian `keep_alive` trong cấu hình `config/models.yaml` (ví dụ: từ `5m`
    thành `60m` hoặc `-1` để giữ mô hình vĩnh viễn trên GPU chuyên dụng).

### Lỗi 3: Cắt ngữ cảnh hội thoại thường xuyên

- **Biểu hiện**: Trợ lý trả lời quên các thông tin đã trao đổi ở đầu phiên hội thoại
  dù người dùng vẫn đang nói tiếp trong cùng một chủ đề.
- **Cách nhận biết trong nhật ký**:
  - Trường `da_cat_ngu_canh` tại chặng `dung_ngu_canh` có giá trị `true`.
  - Thông báo nhật ký ghi nhận số lượt bị lược bớt `so_luot_bi_cat > 0`.
  - Chỉ số `ty_le_cat_ngu_canh` tại `/api/v1/chi-so` tăng cao trên toàn hệ thống.
- **Nguyên nhân**: Cuộc hội thoại có nhiều lượt trao đổi dài khiến tổng số token vượt
  quá ngân sách ngữ cảnh cho phép của mô hình (`num_ctx`).
- **Biện pháp xử lý**:
  - Xem xét nâng cấp hồ sơ GPU (`HO_SO_GPU`) để sử dụng mức `num_ctx` lớn hơn (ví dụ
    từ `gpu8: 16384` lên hồ sơ cao hơn).
  - Khuyến nghị cán bộ chủ động tách các nghiệp vụ mới thành cuộc hội thoại riêng biệt.
