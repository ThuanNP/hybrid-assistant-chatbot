# Quy chuẩn đặt tên (Naming Rules)

Quy tắc này quy định chuẩn đặt tên áp dụng cho toàn bộ mã nguồn, cơ sở dữ liệu,
cấu hình và tài liệu trong workspace.

## 1. Đặt tên trong mã nguồn Python

- Tên tệp, hàm, phương thức và biến dùng `snake_case` tiếng Việt không dấu.
- Tên lớp (class) dùng `PascalCase`.
- Tên hằng số dùng `UPPER_SNAKE_CASE` (viết hoa toàn bộ).

```python
# ĐÚNG:
# Tệp: nhat_ky.py
HAN_MUC_GOI_MO_HINH = 100

class KetQuaGoi:
    def __init__(self, ma_yeu_cau: str) -> None:
        self.ma_yeu_cau = ma_yeu_cau

def dung_ngu_canh(hoi_thoai_id: str) -> str:
    return "ngu_canh"

# SAI (CẤM):
# Tệp: Nhat_Ky.py hoặc nhật_ký.py
hanMucGoi = 100

class ket_qua_goi:
    def __init__(self, MaYeuCau: str) -> None:
        self.MaYeuCau = MaYeuCau

def DungNguCanh(hoi_thoai_id: str) -> str:
    return "ngu_canh"
```

## 2. Đặt tên trong mã nguồn TypeScript

- Tên tệp dùng `kebab-case` (ví dụ `sse.service.ts`).
- Tên lớp và interface dùng `PascalCase`.
- Tên biến, thuộc tính và hàm dùng `camelCase`.

```typescript
// ĐÚNG:
// Tệp: sse.service.ts
export class ChatStreamService {
  private maYeuCauHienTai: string = "";

  public xuLyDongDuLieu(noiDungChunk: string): void {
    const daNhanDuLieu = true;
  }
}

// SAI (CẤM):
// Tệp: SseService.ts hoặc sse_service.ts
export class chat_stream_service {
  private Ma_Yeu_Cau: string = "";

  public Xu_Ly_Dong_Du_Lieu(noi_dung: string): void {
    const Da_Nhan = true;
  }
}
```

## 3. Đặt tên tệp Markdown và tệp kiểm thử

- Tệp Markdown dùng `kebab-case` không dấu.
- Tệp kiểm thử dùng tiền tố `test_` kết hợp `snake_case`.

```text
# ĐÚNG:
docs/kien-truc-he-thong.md
tests/test_nhat_ky.py
tests/test_router_dinh_tuyen.py

# SAI (CẤM):
docs/kiến_trúc_hệ_thống.md
docs/KienTrucHeThong.md
tests/nhat_ky_test.py
tests/TestNhatKy.py
```

## 4. Đặt tên bảng trong cơ sở dữ liệu

- Tên bảng cơ sở dữ liệu dùng `snake_case` ở dạng số ít, tiếng Việt không dấu.

```sql
-- ĐÚNG:
CREATE TABLE hoi_thoai (
    id VARCHAR(36) PRIMARY KEY,
    tieu_de TEXT NOT NULL
);

CREATE TABLE tin_nhan (
    id VARCHAR(36) PRIMARY KEY,
    hoi_thoai_id VARCHAR(36) NOT NULL
);

-- SAI (CẤM):
CREATE TABLE hoi_thoais (...);      -- Cấm dùng số nhiều tiếng Anh
CREATE TABLE DanhSachTinNhan (...); -- Cấm dùng PascalCase
CREATE TABLE tin-nhan (...);        -- Cấm dùng kebab-case trong SQL
```

## 5. Tính nhất quán khái niệm và cấm ký tự có dấu

- Một khái niệm nghiệp vụ chỉ dùng đúng một từ duy nhất xuyên suốt hệ thống
  (ví dụ: luôn dùng `hoi_thoai`, không dùng lẫn lộn với `conversation` hay `chat_session`).
- Tuyệt đối cấm sử dụng ký tự tiếng Việt có dấu trong mọi tên định danh.

```python
# ĐÚNG:
# Nhất quán một khái niệm hoi_thoai, không dấu
def lay_lich_su_hoi_thoai(hoi_thoai_id: str) -> list:
    return []

# SAI (CẤM):
# Lẫn lộn khái niệm và dùng ký tự có dấu
def lay_lich_su_conversation(cuộc_hội_thoại_id: str) -> list:
    return []
```

## Điều CẤM

- CẤM sử dụng ký tự tiếng Việt có dấu hoặc khoảng trắng trong tên tệp, thư mục,
  biến, hàm, lớp, hằng số và bảng CSDL.
- CẤM dùng lẫn lộn nhiều từ tiếng Anh và tiếng Việt cho cùng một khái niệm nghiệp vụ.
- CẤM đặt tên bảng CSDL ở dạng số nhiều (như `hoi_thoais`, `users`).
- CẤM đặt tên biến, hàm chung chung vô nghĩa như `data`, `temp`, `res`, `handle()`.
- CẤM đặt tên tệp kiểm thử không bắt đầu bằng tiền tố `test_`.
