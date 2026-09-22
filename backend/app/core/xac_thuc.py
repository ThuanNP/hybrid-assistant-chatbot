"""Xác thực người dùng và phân quyền truy cập hệ thống."""

from dataclasses import dataclass, field

from fastapi import HTTPException

from app.config import cau_hinh
from app.llm.chinh_sach import CheDoDinhTuyen


@dataclass
class NguoiDung:
    """Thông tin người dùng phục vụ xác thực và phân quyền."""

    id: str = "nd_mac_dinh"
    ten_dang_nhap: str = "can_bo"
    vai_tro: str = "chuyen_vien"
    bac: str = "chinh"
    phong_ban: str = "CNTT"
    pham_vi_doc: list[str] = field(default_factory=list)
    che_do_dinh_tuyen: CheDoDinhTuyen | str | None = None


async def lay_nguoi_dung_hien_tai() -> NguoiDung:
    """Lấy thông tin người dùng hiện tại phục vụ phân quyền và định tuyến.

    Khi XAC_THUC_GIA=true, tạm thời trả về đối tượng NguoiDung giả lập.
    PROMPT 12 sẽ hoàn thiện giải mã JWT, trả lỗi 401 và chặn khởi động ở prod.
    """
    if cau_hinh.xac_thuc_gia:
        return NguoiDung()

    raise HTTPException(status_code=401, detail="Chưa xác thực người dùng")
