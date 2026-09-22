"""Xác thực người dùng và phân quyền truy cập hệ thống."""

from dataclasses import dataclass, field

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


# TODO: Cài đặt giải mã JWT và chế độ xác thực giả lập dev
