"""Cấu hình ghi nhật ký JSON một dòng có cấu trúc và quản lý định danh yêu cầu xuyên suốt.

Đảm bảo tuân thủ Quy tắc 4 (không ghi nội dung tin nhắn), Quy tắc 7 (ghi nhận đầy đủ
thông số mô hình), và Quy tắc 10 (ma_yeu_cau truyền xuyên suốt trong mọi bản ghi).
"""

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Biến ngữ cảnh lưu mã định danh yêu cầu cho từng tác vụ / luồng yêu cầu
_ma_yeu_cau_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "ma_yeu_cau", default=""
)

# Danh sách 22 trường cố định bắt buộc có trong mọi dòng nhật ký JSON
CAC_TRUONG_CO_DINH: tuple[str, ...] = (
    "thoi_diem",
    "muc",
    "ma_yeu_cau",
    "nguoi_id",
    "phong_ban",
    "hoi_thoai_id",
    "chang",
    "thong_diep",
    "nguon",
    "tang",
    "bac_local",
    "model",
    "token_vao",
    "token_ra",
    "chi_phi_usd",
    "toc_do_tok_s",
    "thoi_gian_nap_ms",
    "do_dai_hang_doi",
    "do_tre_ms",
    "da_cat_ngu_canh",
    "nhan_du_lieu",
    "danh_sach_tang_da_hong",
)

# 7 chặng chuẩn hóa trong vòng đời xử lý yêu cầu hội thoại
CAC_CHANG_CHUAN: frozenset[str] = frozenset({
    "http_vao",
    "kiem_tra_han_muc",
    "xac_dinh_chuoi",
    "dung_ngu_canh",
    "goi_mo_hinh",
    "luu_hoi_thoai",
    "http_ra",
})


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


class DinhDangNhatKyJson(logging.Formatter):
    """Formatter chuyển đổi mọi bản ghi nhật ký thành JSON một dòng duy nhất.

    Luôn bảo đảm đầy đủ 22 trường cố định, tự động lấy ma_yeu_cau từ contextvars
    nếu bản ghi chưa có, và ghi vết lỗi an toàn không làm vỡ cấu trúc một dòng.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Định dạng bản ghi LogRecord thành chuỗi JSON một dòng."""
        ma_yc = getattr(record, "ma_yeu_cau", None) or lay_ma_yeu_cau()

        # Thời điểm chuẩn ISO 8601 UTC
        thoi_diem_iso = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).isoformat()

        # Lấy thông điệp đã format từ Logger
        thong_diep = record.getMessage()

        # Khởi tạo bản ghi với 22 trường cố định
        ban_ghi: dict[str, Any] = {
            "thoi_diem": thoi_diem_iso,
            "muc": record.levelname,
            "ma_yeu_cau": str(ma_yc),
            "nguoi_id": getattr(record, "nguoi_id", None),
            "phong_ban": getattr(record, "phong_ban", None),
            "hoi_thoai_id": getattr(record, "hoi_thoai_id", None),
            "chang": getattr(record, "chang", None),
            "thong_diep": thong_diep,
            "nguon": getattr(record, "nguon", None),
            "tang": getattr(record, "tang", None),
            "bac_local": getattr(record, "bac_local", None),
            "model": getattr(record, "model", None),
            "token_vao": int(getattr(record, "token_vao", 0) or 0),
            "token_ra": int(getattr(record, "token_ra", 0) or 0),
            "chi_phi_usd": float(getattr(record, "chi_phi_usd", 0.0) or 0.0),
            "toc_do_tok_s": float(getattr(record, "toc_do_tok_s", 0.0) or 0.0),
            "thoi_gian_nap_ms": float(getattr(record, "thoi_gian_nap_ms", 0.0) or 0.0),
            "do_dai_hang_doi": int(getattr(record, "do_dai_hang_doi", 0) or 0),
            "do_tre_ms": float(getattr(record, "do_tre_ms", 0.0) or 0.0),
            "da_cat_ngu_canh": bool(getattr(record, "da_cat_ngu_canh", False)),
            "nhan_du_lieu": getattr(record, "nhan_du_lieu", None),
            "danh_sach_tang_da_hong": getattr(record, "danh_sach_tang_da_hong", []),
        }

        # Nếu có ngoại lệ, ghi vết lỗi vào trường vet_loi (JSON tự escape xuống dòng)
        if record.exc_info:
            ei = record.exc_info
            if ei is True:
                ei = sys.exc_info()
            if isinstance(ei, tuple) and len(ei) == 3 and ei[0] is not None:
                ban_ghi["vet_loi"] = self.formatException(ei)
            elif isinstance(ei, BaseException):
                import traceback
                ban_ghi["vet_loi"] = "".join(
                    traceback.format_exception(type(ei), ei, ei.__traceback__)
                )
            elif isinstance(ei, str):
                ban_ghi["vet_loi"] = ei

        return json.dumps(ban_ghi, ensure_ascii=False)


def ghi_nhat_ky_chang(
    chang: str,
    thong_diep: str,
    *,
    logger_obj: logging.Logger | None = None,
    muc: int = logging.INFO,
    ma_yeu_cau: str | None = None,
    nguoi_id: int | str | None = None,
    phong_ban: str | None = None,
    hoi_thoai_id: int | None = None,
    nguon: str | None = None,
    tang: int | None = None,
    bac_local: str | None = None,
    model: str | None = None,
    token_vao: int = 0,
    token_ra: int = 0,
    chi_phi_usd: float = 0.0,
    toc_do_tok_s: float = 0.0,
    thoi_gian_nap_ms: float = 0.0,
    do_dai_hang_doi: int = 0,
    do_tre_ms: float = 0.0,
    da_cat_ngu_canh: bool = False,
    nhan_du_lieu: str | None = None,
    danh_sach_tang_da_hong: list[int] | None = None,
) -> None:
    """Ghi một dòng nhật ký JSON tại một trong 7 chặng xử lý chuẩn hóa."""
    log = logger_obj or logger
    extra_data = {
        "ma_yeu_cau": ma_yeu_cau or lay_ma_yeu_cau(),
        "nguoi_id": nguoi_id,
        "phong_ban": phong_ban,
        "hoi_thoai_id": hoi_thoai_id,
        "chang": chang,
        "nguon": nguon,
        "tang": tang,
        "bac_local": bac_local,
        "model": model,
        "token_vao": token_vao,
        "token_ra": token_ra,
        "chi_phi_usd": chi_phi_usd,
        "toc_do_tok_s": toc_do_tok_s,
        "thoi_gian_nap_ms": thoi_gian_nap_ms,
        "do_dai_hang_doi": do_dai_hang_doi,
        "do_tre_ms": do_tre_ms,
        "da_cat_ngu_canh": da_cat_ngu_canh,
        "nhan_du_lieu": nhan_du_lieu,
        "danh_sach_tang_da_hong": danh_sach_tang_da_hong or [],
    }
    log.log(muc, thong_diep, extra=extra_data)


def thiet_lap_nhat_ky(muc_mac_dinh: int = logging.INFO) -> None:
    """Thiết lập Formatter JSON một dòng cho toàn bộ hệ thống logging."""
    formatter = DinhDangNhatKyJson()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(muc_mac_dinh)
    # Loại bỏ các handler cũ nếu có để tránh ghi lặp
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)

    # Đồng bộ cấu hình cho loggers của uvicorn
    for ten_log in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        log_uv = logging.getLogger(ten_log)
        log_uv.handlers = [handler]
        log_uv.propagate = False
