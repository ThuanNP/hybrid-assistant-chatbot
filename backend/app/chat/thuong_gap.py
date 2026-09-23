"""Mô-đun quản lý và tra cứu câu hỏi thường gặp về cách sử dụng trợ lý nội bộ."""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from app.llm.dem_token import dem_token

logger = logging.getLogger(__name__)

# Thư mục gốc repo và đường dẫn tệp cấu hình
THU_MUC_GOC = Path(__file__).resolve().parents[3]
DUONG_DAN_THUONG_GAP_YAML = THU_MUC_GOC / "config" / "cau_hoi_thuong_gap.yaml"
DUONG_DAN_HUONG_DAN_MD = THU_MUC_GOC / "config" / "huong_dan_su_dung.md"


class MucThuongGap(BaseModel):
    """Cấu trúc dữ liệu một mục câu hỏi thường gặp."""

    ma: str
    nhom: str
    cau_hoi: str
    tra_loi: str
    tu_khoa: list[str] = Field(default_factory=list)

    @field_validator("tu_khoa", mode="before")
    @classmethod
    def chuan_hoa_danh_sach_tu_khoa(cls, ds: Any) -> list[str]:
        """Đảm bảo mọi phần tử trong danh sách từ khóa đều là chuỗi."""
        if not isinstance(ds, list):
            return []
        return [str(item) for item in ds]


class GioiHanThuongGap(BaseModel):
    """Giới hạn số mục và token tối đa khi ghép vào ngữ cảnh."""

    toi_da_muc: int = 3
    toi_da_token: int = 600


class DuLieuThuongGap(BaseModel):
    """Toàn bộ dữ liệu câu hỏi thường gặp nạp từ tệp YAML."""

    phien_ban: str
    gioi_han: GioiHanThuongGap
    muc: list[MucThuongGap]


def bo_dau_tieng_viet(van_ban: str) -> str:
    """Chuyển văn bản tiếng Việt về dạng không dấu, viết thường, tất định."""
    chuoi_chuan = unicodedata.normalize("NFD", van_ban)
    chuoi_khong_dau = "".join(
        ky_tu for ky_tu in chuoi_chuan if unicodedata.category(ky_tu) != "Mn"
    )
    chuoi_khong_dau = chuoi_khong_dau.replace("đ", "d").replace("Đ", "d")
    return chuoi_khong_dau.lower().strip()


# Tập các hư từ tiếng Việt không dấu phổ biến cần bỏ qua khi so khớp từ khóa
TU_DUNG_CHUNG = frozenset({
    "co", "the", "nao", "va", "khong", "thi", "la", "o", "gi", "sao",
    "lam", "cho", "duoc", "mot", "cac", "nhung", "de", "trong", "cung",
    "ra", "nay", "do", "den", "tu", "voi", "ve", "hay", "toi", "minh",
    "anh", "chi", "ban", "cua", "khi", "nhu", "theo", "lai", "se", "da",
    "dang", "roi", "ma", "ai", "dau", "vi", "nen", "neu", "vao", "tai",
    "thoi", "ngay", "gio", "phut", "giay", "chua", "rat", "qua", "can", "phai", "muon", "biet", "xin", "giup",
})


def tach_tu_khoa(van_ban: str) -> set[str]:
    """Tách văn bản thành tập các từ khóa không dấu có ý nghĩa, loại bỏ hư từ."""
    van_ban_khong_dau = bo_dau_tieng_viet(van_ban)
    cac_tu = re.findall(r"\b[a-z0-9_]{2,}\b", van_ban_khong_dau)
    return {tu for tu in cac_tu if tu not in TU_DUNG_CHUNG}


def nap_du_lieu_thuong_gap(
    duong_dan_yaml: Path | None = None,
) -> DuLieuThuongGap:
    """Nạp tệp cấu hình câu hỏi thường gặp từ YAML."""
    duong_dan = duong_dan_yaml or DUONG_DAN_THUONG_GAP_YAML
    if not duong_dan.exists():
        logger.warning("Không tìm thấy tệp câu hỏi thường gặp tại %s", duong_dan)
        return DuLieuThuongGap(
            phien_ban="2026-09-24.1",
            gioi_han=GioiHanThuongGap(),
            muc=[],
        )

    with duong_dan.open("r", encoding="utf-8") as tep:
        du_lieu = yaml.safe_load(tep) or {}

    return DuLieuThuongGap(**du_lieu)


# Nạp tệp một lần duy nhất khi nạp mô-đun
_DU_LIEU_THUONG_GAP: DuLieuThuongGap = nap_du_lieu_thuong_gap()


def lay_du_lieu_thuong_gap() -> DuLieuThuongGap:
    """Trả về đối tượng dữ liệu câu hỏi thường gặp đã nạp."""
    return _DU_LIEU_THUONG_GAP


def chon_muc_lien_quan(
    cau_hoi: str,
    toi_da: int | None = None,
    du_lieu: DuLieuThuongGap | None = None,
) -> list[MucThuongGap]:
    """Chọn các mục có nhiều từ khóa trùng nhất giữa câu hỏi và mục hướng dẫn.

    Xử lý tất định, chữ thường, bỏ dấu, không gọi mô hình nhúng.
    Không có mục nào trùng từ khóa thì trả về danh sách rỗng.
    """
    nguon_du_lieu = du_lieu or _DU_LIEU_THUONG_GAP
    tu_cau_hoi = tach_tu_khoa(cau_hoi)
    if not tu_cau_hoi:
        return []

    gioi_han_muc = toi_da if toi_da is not None else nguon_du_lieu.gioi_han.toi_da_muc
    diem_cac_muc: list[tuple[int, MucThuongGap]] = []

    for muc in nguon_du_lieu.muc:
        tu_muc = tach_tu_khoa(muc.cau_hoi)
        for tk in muc.tu_khoa:
            tu_muc.update(tach_tu_khoa(tk))

        so_tu_trung = len(tu_cau_hoi & tu_muc)
        if so_tu_trung >= 2 or (len(tu_cau_hoi) == 1 and so_tu_trung >= 1):
            diem_cac_muc.append((so_tu_trung, muc))

    if not diem_cac_muc:
        return []

    # Sắp xếp theo số từ trùng giảm dần
    diem_cac_muc.sort(key=lambda cap: cap[0], reverse=True)
    return [muc for _, muc in diem_cac_muc[:gioi_han_muc]]


def dinh_dang_khoi_thuong_gap(
    cac_muc: list[MucThuongGap],
    toi_da_token: int | None = None,
) -> str:
    """Định dạng các mục câu hỏi thường gặp thành khối Markdown bổ trợ cho lời nhắc hệ thống.

    Đảm bảo tổng số token không vượt quá giới hạn toi_da_token.
    """
    if not cac_muc:
        return ""

    gioi_han = (
        toi_da_token
        if toi_da_token is not None
        else _DU_LIEU_THUONG_GAP.gioi_han.toi_da_token
    )

    tieu_de = (
        "## Câu hỏi thường gặp về cách sử dụng trợ lý\n"
        "Quy tắc: Câu hỏi về cách dùng trợ lý thuộc phạm vi được trả lời. "
        "Câu hỏi khớp một mục dưới đây thì trả lời theo nội dung mục đó, "
        "không mô tả chức năng không có trong mục.\n"
    )

    cac_doan_muc: list[str] = []
    for muc in cac_muc:
        doan = f"- Câu hỏi: {muc.cau_hoi}\n  Trả lời: {muc.tra_loi}\n"
        cac_doan_muc.append(doan)

    # Thử ghép toàn bộ và cắt dần từ cuối nếu vượt ngân sách token
    while cac_doan_muc:
        noi_dung = tieu_de + "\n" + "".join(cac_doan_muc)
        if dem_token(noi_dung) <= gioi_han:
            return noi_dung.strip()
        cac_doan_muc.pop()

    return ""


def lay_cau_hoi_thuong_gap_api() -> dict[str, Any]:
    """Trả về dữ liệu câu hỏi thường gặp chuẩn bị cho endpoint API."""
    du_lieu = _DU_LIEU_THUONG_GAP
    danh_sach_muc = [
        {
            "ma": m.ma,
            "nhom": m.nhom,
            "cau_hoi": m.cau_hoi,
            "tra_loi": m.tra_loi,
        }
        for m in du_lieu.muc
    ]
    return {
        "phien_ban": du_lieu.phien_ban,
        "muc": danh_sach_muc,
    }


def lay_huong_dan_su_dung_api() -> dict[str, str]:
    """Trả về phiên bản và nội dung hướng dẫn sử dụng từ config/huong_dan_su_dung.md."""
    noi_dung = ""
    if DUONG_DAN_HUONG_DAN_MD.exists():
        noi_dung = DUONG_DAN_HUONG_DAN_MD.read_text(encoding="utf-8")
    return {
        "phien_ban": _DU_LIEU_THUONG_GAP.phien_ban,
        "noi_dung": noi_dung,
    }
