"""Tiện ích đếm số lượng token cho các mô hình ngôn ngữ."""

import tiktoken

# Sử dụng bộ mã hoá cl100k_base thống nhất toàn hệ thống.
# GHI CHÚ QUAN TRỌNG: Đây là con số ƯỚC LƯỢNG vì model local (như Qwen) và từng
# nhà cung cấp đám mây (Gemini, Claude, OpenAI) sử dụng bộ tách từ (tokenizer) khác nhau.
# Đặc biệt đối với tiếng Việt, mỗi từ/chữ thường tiêu tốn khoảng 1 đến 3 token.
# Do đó, khi tính toán ngân sách ngữ cảnh thực tế, hệ thống sẽ áp dụng hệ số an toàn
# he_so_an_toan_token (khai báo trong cấu hình cai_dat_chung của config/models.yaml),
# tuyệt đối không ghi cứng hệ số an toàn trong mã nguồn.
_BO_MA_HOA = tiktoken.get_encoding("cl100k_base")


def dem_token(van_ban: str) -> int:
    """Đếm số lượng token ước lượng cho chuỗi văn bản đầu vào.

    Tham số:
        van_ban: Chuỗi ký tự cần tính số lượng token.

    Trả về:
        Số lượng token ước lượng (kiểu int). Trả về 0 nếu văn bản rỗng.
    """
    if not van_ban:
        return 0
    return len(_BO_MA_HOA.encode(van_ban, disallowed_special=()))
