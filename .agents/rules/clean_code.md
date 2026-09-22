# Quy chuẩn mã sạch (Clean Code)

Quy tắc này quy định các chuẩn mực viết mã áp dụng cho toàn bộ mã nguồn backend
và frontend trong workspace.

## 1. Hàm đơn nhiệm và giới hạn độ dài

- Mỗi hàm chỉ làm đúng một việc duy nhất, rõ ràng và có mục đích cụ thể.
- Độ dài tối đa của một hàm vào khoảng 40 dòng logic. Nếu dài hơn, phải tách
  thành các hàm con bổ trợ.

```python
# ĐÚNG: Hàm ngắn gọn, làm một việc rõ ràng (< 40 dòng)
def kiem_tra_han_muc(nguoi_dung_id: str, chi_phi: float) -> bool:
    han_muc_hien_tai = lay_han_muc_nguoi_dung(nguoi_dung_id)
    return han_muc_hien_tai >= chi_phi

# SAI (CẤM): Hàm ôm đồm nhiều việc, quá dài (> 40 dòng logic phức tạp)
def xu_ly_chat_va_kiem_tra_roi_luu_csdl(yeu_cau: dict) -> dict:
    # 50+ dòng trộn lẫn xác thực, trừ tiền, gọi API mô hình, định dạng JSON và ghi CSDL
    ...
```

## 2. Không lặp mã (DRY - Don't Repeat Yourself)

- Gom logic nghiệp vụ và các phép biến đổi dữ liệu trùng lặp về một hàm
  hoặc lớp dùng chung.

```python
# ĐÚNG: Tái sử dụng hàm tiện ích
def chuan_hoa_so_dien_thoai(sdt: str) -> str:
    return sdt.strip().replace(" ", "").replace("-", "")

sdt_khach = chuan_hoa_so_dien_thoai(raw_khach)
sdt_lien_he = chuan_hoa_so_dien_thoai(raw_lien_he)

# SAI (CẤM): Lặp lại đoạn mã xử lý ở nhiều nơi
sdt_khach = raw_khach.strip().replace(" ", "").replace("-", "")
# ... ở một tệp khác lại viết:
sdt_lien_he = raw_lien_he.strip().replace(" ", "").replace("-", "")
```

## 3. Trả sớm thay vì lồng `if` (Guard Clauses / Early Return)

- Kiểm tra các điều kiện biên và thoát sớm ngay đầu hàm để giữ cấu trúc mã phẳng.

```python
# ĐÚNG: Trả sớm, mã phẳng và dễ theo dõi luồng logic
def lay_thong_tin_cong_to(ma_khach_hang: str | None) -> dict:
    if not ma_khach_hang:
        return {}
    if not kiem_tra_hop_le(ma_khach_hang):
        return {}
    return truy_van_cong_to(ma_khach_hang)

# SAI (CẤM): Lồng nhiều tầng if-else hình mũi tên (Arrow anti-pattern)
def lay_thong_tin_cong_to(ma_khach_hang: str | None) -> dict:
    if ma_khach_hang:
        if kiem_tra_hop_le(ma_khach_hang):
            return truy_van_cong_to(ma_khach_hang)
        else:
            return {}
    else:
        return {}
```

## 4. Không nuốt ngoại lệ

- Phải bắt đúng loại ngoại lệ cụ thể, ghi log hoặc ném tiếp; tuyệt đối không dùng
  khối `except` rỗng để ỉm đi lỗi phát sinh.

```python
# ĐÚNG: Bắt ngoại lệ cụ thể và ghi log hoặc re-raise
try:
    ket_qua = ket_noi_dich_vu_llm(tham_so)
except TimeoutError as err:
    logger.error("Dịch vụ LLM quá thời gian phản hồi: %s", err)
    raise HTTPException(status_code=504, detail="Dịch vụ LLM quá thời gian phản hồi")

# SAI (CẤM): Nuốt ngoại lệ âm thầm bằng except rỗng
try:
    ket_qua = ket_noi_dich_vu_llm(tham_so)
except Exception:
    pass  # Cực kỳ nguy hiểm, che giấu lỗi thực tế
```

## 5. Không để mã chết hay print gỡ lỗi

- Không lưu lại các đoạn mã bị chú thích (commented-out code), các biến không dùng.
- Không dùng lệnh `print()` hoặc `console.log()` trong mã nguồn sản phẩm; phải dùng
  hệ thống logging chuyên dụng có cấu trúc.

```python
# ĐÚNG: Dùng logger chuyên dụng
logger.info("Khởi tạo tiến trình xử lý yêu cầu %s", ma_yeu_cau)

# SAI (CẤM): Để lại print gỡ lỗi hoặc mã chết bị comment
print(f"DEBUG: dang xu ly ma {ma_yeu_cau}")
# res = goi_api_cu(ma_yeu_cau)
# if res.status == 200:
#     do_something()
```

## 6. Chú thích giải thích VÌ SAO, không lặp lại mã LÀM GÌ

- Chú thích phải nêu rõ lý do kỹ thuật, trường hợp ngoại lệ hoặc ràng buộc nghiệp vụ.
- Không viết chú thích dịch nghĩa từng dòng mã một cách thừa thãi.

```python
# ĐÚNG: Giải thích nguyên nhân hoặc bối cảnh đặc thù
# Cần trễ 500ms để đảm bảo GPU giải phóng bộ nhớ đệm trước khi gọi model tiếp theo
time.sleep(0.5)

# SAI (CẤM): Chú thích lặp lại hành động hiển nhiên của mã
# Tạm dừng 0.5 giây
time.sleep(0.5)
```

## Điều CẤM

- CẤM viết hàm dài quá 40 dòng logic mà không phân rã thành các hàm nhỏ hơn.
- CẤM lặp lại đoạn mã logic giống nhau từ 2 lần trở lên thay vì trừu tượng hoá.
- CẤM lồng ghép câu lệnh `if-else` quá 3 tầng sâu.
- CẤM nuốt ngoại lệ bằng câu lệnh `pass` trong khối `except`.
- CẤM để lại mã nguồn chết, biến không sử dụng hoặc câu lệnh `print()` / `console.log()`.
- CẤM viết chú thích hiển nhiên, chỉ lặp lại nội dung đã thể hiện ở câu lệnh.
