# Quy chuẩn định dạng Markdown

Quy tắc này quy định chuẩn định dạng áp dụng cho mọi tệp tài liệu Markdown
trong toàn bộ workspace.

## 1. Kiểm tra linter trước khi báo hoàn thành

- Mọi tệp `.md` sau khi tạo hoặc chỉnh sửa bắt buộc phải chạy kiểm tra bằng
  `markdownlint-cli2` và đạt 0 lỗi trước khi báo hoàn thành.

```bash
# ĐÚNG: Chạy lệnh linter kiểm tra tài liệu
npx --yes markdownlint-cli2 "AGENTS.md" ".agents/rules/*.md"

# SAI (CẤM): Báo hoàn thành công việc mà chưa chạy kiểm tra linter
# (Gây sót lỗi MD013, MD022, MD031, MD040 trong tài liệu)
```

## 2. Giới hạn độ dài dòng văn xuôi tối đa 100 ký tự

- Đoạn văn xuôi không được vượt quá 100 ký tự trên một dòng (chủ động ngắt dòng).
- Bảng, khối mã và tiêu đề được miễn trừ giới hạn độ dài theo cấu hình MD013.

````markdown
<!-- ĐÚNG: Văn xuôi được ngắt dòng hợp lý (< 100 ký tự/dòng) -->
Hệ thống trợ lý AI hỗ trợ tra cứu thông tin nội bộ
cho cán bộ công nhân viên nhanh chóng và chính xác.

<!-- SAI (CẤM): Dòng văn xuôi quá dài vượt quá 100 ký tự trên một hàng -->
Hệ thống trợ lý AI hỗ trợ tra cứu thông tin nội bộ cho cán bộ công nhân viên ngành điện lực trên một dòng rất dài vượt quá giới hạn một trăm ký tự.
````

## 3. Khối mã phải khai báo nhãn ngôn ngữ

- Mọi khối mã fenced bắt buộc phải có nhãn ngôn ngữ rõ ràng (ví dụ: `python`,
  `typescript`, `bash`, `json`, `sql`, `text`). Tuyệt đối không để khối mã trần.

````markdown
<!-- ĐÚNG: Có nhãn ngôn ngữ rõ ràng -->
```python
def chao_mung() -> str:
    return "Xin chao"
```

<!-- SAI (CẤM): Khối mã trần không khai báo ngôn ngữ (vi phạm MD040) -->
```
def chao_mung() -> str:
    return "Xin chao"
```
````

## 4. Cấm tắt rule bằng comment rải rác

- Không sử dụng các bình luận tắt rule rải rác trong tệp tài liệu.
- Mọi điều chỉnh hoặc ngoại lệ quy tắc phải được khai báo tập trung trong
  `.markdownlint.json` hoặc `.markdownlint-cli2.jsonc`.

````markdown
<!-- ĐÚNG: Viết tài liệu tuân thủ chuẩn mà không cần comment tắt rule -->
Hệ thống tuân thủ định dạng chuẩn.

<!-- SAI (CẤM): Dùng comment tắt rule tùy tiện rải rác trong nội dung -->
<!-- markdownlint-disable MD013 -->
Đoạn văn bản cố tình viết dài để né tránh kiểm tra linter.
<!-- markdownlint-enable MD013 -->
````

## Điều CẤM

- CẤM báo hoàn thành tác vụ khi lệnh kiểm tra `markdownlint-cli2` vẫn còn báo lỗi.
- CẤM viết các dòng văn xuôi dài vượt quá 100 ký tự mà không bẻ dòng.
- CẤM sử dụng khối mã trần không có nhãn định danh ngôn ngữ.
- CẤM chèn các comment `markdownlint-disable` rải rác trong các tệp tài liệu.
