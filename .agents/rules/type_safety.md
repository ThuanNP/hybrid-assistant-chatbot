# Quy chuẩn an toàn kiểu dữ liệu (Type Safety)

Quy tắc này quy định chuẩn an toàn kiểu dữ liệu áp dụng cho toàn bộ mã nguồn
Python và TypeScript trong workspace.

## 1. Python đầy đủ type hint và kiểm tra bằng pyright

- Mọi tham số hàm, giá trị trả về và thuộc tính lớp trong Python phải có khai báo
  kiểu dữ liệu (type hint) đầy đủ và chính xác.
- Mã nguồn phải vượt qua trình kiểm tra kiểu tĩnh `pyright` mà không có lỗi.

```python
# ĐÚNG: Đầy đủ type hint, tương thích pyright
def tinh_chi_phi_token(so_token: int, don_gia: float) -> float:
    return so_token * don_gia

# SAI (CẤM): Thiếu type hint tham số hoặc giá trị trả về
def tinh_chi_phi_token(so_token, don_gia):
    return so_token * don_gia
```

## 2. TypeScript bật strict mode và cấm kiểu `any`

- Dự án cấu hình TypeScript ở chế độ nghiêm ngặt (`"strict": true`).
- Tuyệt đối cấm sử dụng kiểu `any`; phải sử dụng kiểu dữ liệu cụ thể hoặc dùng
  `unknown` kèm theo kiểm tra kiểu (type guard).

```typescript
// ĐÚNG: Kiểu tường minh, an toàn
interface TinNhanPhanHoi {
  maYeuCau: string;
  noiDung: string;
}

function xuLyPhanHoi(duLieu: TinNhanPhanHoi): string {
  return duLieu.noiDung;
}

// SAI (CẤM): Dùng kiểu any
function xuLyPhanHoi(duLieu: any): any {
  return duLieu.noiDung;
}
```

## 3. Thu hẹp kiểu cho giá trị `Optional` hoặc `None`

- Khi giá trị có thể là `None` (hoặc `undefined`), bắt buộc phải thu hẹp kiểu
  trước khi truy cập thuộc tính hoặc phương thức của đối tượng.
- Trong mã kiểm thử (`tests/`): dùng `assert x is not None`.
- Trong mã ứng dụng nghiệp vụ (`app/`): trả sớm (`early return`) hoặc ném `HTTPException`.

```python
# ĐÚNG trong tests/:
def test_lay_hoi_thoai() -> None:
    hoi_thoai = tim_hoi_thoai_theo_id("ht-123")
    assert hoi_thoai is not None
    assert hoi_thoai.tieu_de == "Hỏi tiền điện"

# ĐÚNG trong app/:
def xem_hoi_thoai(hoi_thoai_id: str) -> ThongTinHoiThoai:
    hoi_thoai = tim_hoi_thoai_theo_id(hoi_thoai_id)
    if hoi_thoai is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hội thoại")
    return hoi_thoai.chuyen_doi_dto()

# SAI (CẤM): Truy cập trực tiếp khi chưa thu hẹp kiểu (gây lỗi phân tích pyright)
def xem_hoi_thoai(hoi_thoai_id: str) -> ThongTinHoiThoai:
    hoi_thoai = tim_hoi_thoai_theo_id(hoi_thoai_id)
    return hoi_thoai.chuyen_doi_dto()  # Lỗi nếu hoi_thoai là None
```

## 4. Không ép kiểu thừa thãi

- Không bọc ép kiểu cưỡng bức khi biến đã có kiểu dữ liệu chuẩn xác.
- Không dùng `# type: ignore` để né tránh việc sửa đúng kiểu dữ liệu.

```python
# ĐÚNG: Tận dụng suy luận kiểu hoặc kiểu đã khai báo chuẩn
def xu_ly_chuoi(van_ban: str) -> str:
    return van_ban.strip()

# SAI (CẤM): Ép kiểu thừa thãi khi biến đã là kiểu str
def xu_ly_chuoi(van_ban: str) -> str:
    return str(van_ban).strip()  # str() là thừa thãi
```

## Điều CẤM

- CẤM bỏ qua type annotation cho tham số hoặc giá trị trả về của hàm trong Python.
- CẤM sử dụng kiểu `any` trong toàn bộ mã nguồn TypeScript.
- CẤM truy cập thuộc tính hoặc phương thức của đối tượng `Optional` khi chưa kiểm tra
  thu hẹp kiểu (bằng `assert is not None`, `if is None`, hoặc kiểm tra tương đương).
- CẤM ép kiểu bừa bãi (`as any`, ép kiểu thừa) hoặc dùng comment tắt kiểm tra kiểu.
