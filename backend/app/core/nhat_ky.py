"""Cấu hình ghi nhật ký có cấu trúc và quản lý định danh yêu cầu xuyên suốt."""

import contextvars
import logging
import uuid

logger = logging.getLogger(__name__)

# Biến ngữ cảnh lưu mã định danh yêu cầu cho từng tác vụ / luồng yêu cầu
_ma_yeu_cau_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "ma_yeu_cau", default=""
)


def sinh_ma_yeu_cau() -> str:
    """Sinh chuỗi định danh duy nhất gồm 12 ký tự cho mỗi yêu cầu."""
    return uuid.uuid4().hex[:12]


def lay_ma_yeu_cau() -> str:
    """Lấy mã yêu cầu hiện tại từ contextvars; nếu chưa có thì tự sinh mã mới."""
    ma = _ma_yeu_cau_var.get()
    if not ma:
        ma = sinh_ma_yeu_cau()
        _ma_yeu_cau_var.set(ma)
    return ma


def dat_ma_yeu_cau(ma: str) -> None:
    """Gán mã yêu cầu vào biến ngữ cảnh contextvars."""
    _ma_yeu_cau_var.set(ma)
