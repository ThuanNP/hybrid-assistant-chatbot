# Quy chuẩn đánh số phiên bản ứng dụng (Semantic Versioning)

Quy tắc này quy định chuẩn quản lý phiên bản áp dụng cho toàn bộ các thành phần
backend, frontend và API trong workspace.

## 1. Cấu trúc MAJOR.MINOR.PATCH theo SemVer

- Đánh số phiên bản tuân thủ đặc tả SemVer tại <https://semver.org/>.
- **MAJOR**: Tăng khi có thay đổi phá vỡ tính tương thích ngược.
- **MINOR**: Tăng khi thêm tính năng mới nhưng vẫn tương thích ngược.
- **PATCH**: Tăng khi chỉ sửa lỗi nhỏ, vá bảo mật hoặc tối ưu hoá hiệu năng.
- Khi tăng một số thì toàn bộ các số nằm bên phải phải được đặt về 0.

```text
# ĐÚNG:
1.0.0 -> 1.0.1 (sửa lỗi nhỏ)
1.0.1 -> 1.1.0 (thêm tính năng mới tương thích ngược)
1.1.0 -> 2.0.0 (thay đổi kiến trúc phá vỡ tương thích)

# SAI (CẤM):
1.0.9 -> 1.0.8 (giảm phiên bản)
1.2.3 -> 1.3.3 (tăng MINOR nhưng không đặt PATCH về 0)
```

## 2. Hậu tố thử nghiệm và siêu dữ liệu bản dựng

- Bản thử nghiệm (pre-release) dùng hậu tố `-alpha.N`, `-beta.N`, `-rc.N`.
- Siêu dữ liệu bản dựng (build metadata) dùng tiền tố `+` (ví dụ: `+20260922`, `+sha.5114f85`).

```text
# ĐÚNG:
1.0.0-alpha.1
1.0.0-rc.2
1.0.0+20260922
1.0.0+sha.5114f85

# SAI (CẤM):
1.0.0.alpha1     -- Cấm thiếu dấu gạch nối trước nhãn tiền phát hành
1.0.0_build_2026 -- Cấm dùng dấu gạch dưới thay cho dấu cộng
```

## 3. Giai đoạn phát triển và phát hành chính thức

- Giai đoạn phát triển dùng phiên bản `0.y.z` (mọi thay đổi đều có thể điều chỉnh).
- Phát hành phiên bản `1.0.0` khi hệ thống chạy chính thức cho người dùng thật.

```text
# ĐÚNG:
0.1.0 (giai đoạn đang phát triển ban đầu)
1.0.0 (bản phát hành chính thức đầu tiên cho người dùng)

# SAI (CẤM):
1.0.0 (dùng cho phiên bản thử nghiệm nội bộ chưa ổn định)
0.99.0 (tiếp tục dùng 0.x khi đã đưa vào vận hành chính thức)
```

## 4. Đồng bộ phiên bản giữa backend và frontend

- Cùng một số phiên bản duy nhất cho `backend/pyproject.toml` và `frontend/package.json`.
- Endpoint `/health` bắt buộc trả về trường `phien_ban`.

```json
// ĐÚNG:
// backend/pyproject.toml và frontend/package.json đều có version = "0.1.0"
// Endpoint GET /health trả về:
{
  "trang_thai": "song",
  "phien_ban": "0.1.0"
}

// SAI (CẤM):
// backend có version "0.2.0" trong khi frontend là "0.1.5" (lệch phiên bản)
```

## 5. Định tuyến API và xử lý thay đổi phá vỡ tương thích

- API nghiệp vụ nằm dưới tiền tố `/api/v1/`; các endpoint `/health`, `/ready`,
  `/docs` nằm ở gốc.
- Khi có thay đổi phá vỡ tương thích API, bắt buộc mở `/api/v2/` và duy trì
  `/api/v1/` song song ít nhất một giai đoạn.

```text
# ĐÚNG:
GET /health
GET /api/v1/chat/lich-su
GET /api/v2/chat/lich-su (khi thay đổi cấu trúc dữ liệu trả về)

# SAI (CẤM):
GET /api/v1/health       -- Cấm đặt /health dưới /api/v1/
POST /api/v1/chat        -- Thay đổi phá vỡ cấu trúc input mà không tạo v2
```

## 6. Quy trình phát hành phiên bản mới

- Mỗi lần phát hành: nâng số phiên bản ở cả hai tệp `backend/pyproject.toml`
  và `frontend/package.json`.
- Ghi nhật ký thay đổi trong `CHANGELOG.md` theo ba mục: **Thêm**, **Thay đổi**, **Sửa lỗi**.
- Gắn thẻ git (git tag) có tiền tố `v` theo định dạng `vX.Y.Z`.

```bash
# ĐÚNG:
# 1. Cập nhật version trong backend/pyproject.toml và frontend/package.json
# 2. Cập nhật CHANGELOG.md với mục Thêm, Thay đổi, Sửa lỗi
# 3. Commit và gắn thẻ git:
git tag v1.0.0

# SAI (CẤM):
git tag 1.0.0       # Cấm thiếu tiền tố 'v'
git tag -f v1.0.0   # CẤM ghi đè hoặc sửa thẻ phiên bản đã phát hành
```

## Điều CẤM

- CẤM sửa hay gắn lại thẻ git của phiên bản đã phát hành; nếu có lỗi phải phát hành
  bản PATCH mới.
- CẤM để số phiên bản giữa `backend/pyproject.toml` và `frontend/package.json` lệch nhau.
- CẤM đưa thay đổi phá vỡ tính tương thích vào các bản cập nhật MINOR hoặc PATCH.
- CẤM tăng số MAJOR khi không có thay đổi nào làm phá vỡ tương thích.
