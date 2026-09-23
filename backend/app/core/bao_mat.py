"""Bảo vệ dữ liệu nhạy cảm và các móc kiểm duyệt nội dung."""

from typing import Any

from pydantic import BaseModel, Field


class KetQuaKiemDuyet(BaseModel):
    """Kết quả kiểm tra kiểm duyệt nội dung đầu vào hoặc phản hồi đầu ra."""

    cho_qua: bool = Field(
        default=True, description="Cờ cho phép tiếp tục luồng xử lý hoặc lưu trữ"
    )
    ly_do: str | None = Field(
        default=None, description="Lý do từ chối nếu nội dung vi phạm chính sách"
    )
    noi_dung_thay_the: str | None = Field(
        default=None, description="Nội dung đã được khử nhạy cảm hoặc thay thế an toàn"
    )


async def kiem_duyet_dau_vao(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt nội dung người dùng nhập vào trước khi dựng ngữ cảnh hội thoại.

    Điểm tích hợp kiểm duyệt ở Giai đoạn 5, gắn sẵn tại đây để không phải sửa luồng.
    Giai đoạn hiện tại luôn trả cho_qua=True.
    """
    _ = (noi_dung, nguoi)
    return KetQuaKiemDuyet(cho_qua=True, ly_do=None, noi_dung_thay_the=None)


async def kiem_duyet_dau_ra(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt phản hồi mô hình sinh ra trên toàn văn trước khi lưu CSDL và trả về.

    Điểm tích hợp kiểm duyệt ở Giai đoạn 5, gắn sẵn tại đây để không phải sửa luồng.
    Giai đoạn hiện tại luôn trả cho_qua=True.
    """
    _ = (noi_dung, nguoi)
    return KetQuaKiemDuyet(cho_qua=True, ly_do=None, noi_dung_thay_the=None)
