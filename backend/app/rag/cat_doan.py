"""Mô-đun cắt đoạn văn bản theo cấu trúc phân cấp và độ dài token cho kho tri thức RAG.

Tuân thủ:
- Quy tắc kỹ thuật số 11 trong AGENTS.md (dùng dem_token).
- Quy chuẩn clean_code.md, naming.md, type_safety.md.
"""

import re
from dataclasses import dataclass

from app.llm.dem_token import dem_token


@dataclass
class DoanCat:
    """Đoạn văn bản sau khi được cắt theo cấu trúc và độ dài."""

    thu_tu: int
    tieu_de_muc: str
    duong_dan_muc: str
    noi_dung: str
    so_token: int
    noi_dung_nhung: str


# Regex nhận diện dòng mục lục (tiêu đề kết thúc bằng số trang, có hoặc không có dấu chấm dẫn)
_RE_MUC_LUC = re.compile(
    r"^(?:#+\s*)?(?:Chương|Mục|Điều|Khoản|Phần)\s+[IVXLCDM\d]+[.:\s]+.+?(?:\.{2,}|\s{2,}|\s+)\d{1,3}\s*$",
    re.IGNORECASE,
)

# Regex nhận diện tiêu đề cấu trúc văn bản pháp quy và hành chính
_RE_QUYET_DINH = re.compile(r"^(?:#+\s*)?(QUYẾT\s+ĐỊNH\b.*)$", re.IGNORECASE)
_RE_QUY_DINH = re.compile(
    r"^(?:#+\s*)?(QUY\s+ĐỊNH\b.*|BAN\s+HÀNH\s+KÈM\s+THEO.*)$", re.IGNORECASE
)
_RE_CHUONG = re.compile(
    r"^(?:#+\s*)?(CHƯƠNG\s+[IVXLCDM\d]+)(?:[:.\s-]+(.*))?$", re.IGNORECASE
)
_RE_MUC = re.compile(
    r"^(?:#+\s*)?(MỤC\s+\d+)(?:[:.\s-]+(.*))?$", re.IGNORECASE
)
_RE_DIEU = re.compile(
    r"^(?:#+\s*)?(ĐIỀU\s+\d+)(?:[:.\s-]+(.*))?$", re.IGNORECASE
)
_RE_KHOAN = re.compile(
    r"^(?:#+\s*)?(KHOẢN\s+\d+)(?:[:.\s-]+(.*))?$", re.IGNORECASE
)
_RE_MARKDOWN_HEADER = re.compile(r"^(#{1,6})\s+(.+)$")


def kiem_tra_dong_muc_luc(dong: str) -> bool:
    """Kiểm tra một dòng có phải là dòng mục lục kết thúc bằng số trang hay không."""
    van_ban = dong.strip()
    if not van_ban:
        return False
    return bool(_RE_MUC_LUC.match(van_ban))


def nhan_dien_tieu_de(dong: str) -> tuple[int, str, str] | None:
    """Nhận diện tiêu đề và trả về (cấp_độ, nhãn_ngắn, tiêu_đề_đầy_đủ)."""
    van_ban = dong.strip()
    if not van_ban or kiem_tra_dong_muc_luc(van_ban):
        return None

    # 1. Tiêu đề Markdown thuần tuý (# -> cấp 1, ## -> cấp 2...)
    khop_md = _RE_MARKDOWN_HEADER.match(van_ban)
    if khop_md:
        cap = len(khop_md.group(1))
        tieu_de = khop_md.group(2).strip()
        # Kiểm tra xem tiêu đề Markdown có lồng Điều/Khoản/Chương bên trong không
        kq_con = nhan_dien_tieu_de(tieu_de)
        if kq_con:
            return kq_con
        return cap, tieu_de, tieu_de

    return _nhan_dien_tieu_de_phap_quy(van_ban)


def _chuan_hoa_nhan(nhan: str) -> str:
    """Chuẩn hoá nhãn ngắn cho đường dẫn phân cấp (ví dụ: CHƯƠNG II -> Chương II, ĐIỀU 5 -> Điều 5)."""
    phan = nhan.strip().split(maxsplit=1)
    if len(phan) == 2:
        return f"{phan[0].capitalize()} {phan[1]}"
    return nhan.strip().capitalize()


def _nhan_dien_tieu_de_phap_quy(van_ban: str) -> tuple[int, str, str] | None:
    """Nhận diện các tiêu đề văn bản quy phạm pháp luật (Chương, Mục, Điều, Khoản)."""
    # Quyết định (Cấp 1)
    if _RE_QUYET_DINH.match(van_ban):
        return 1, "Quyết định", van_ban

    # Quy định kèm theo (Cấp 1)
    if _RE_QUY_DINH.match(van_ban):
        return 1, "Quy định", van_ban

    # Chương (Cấp 2)
    khop_chuong = _RE_CHUONG.match(van_ban)
    if khop_chuong:
        nhan_ngan = _chuan_hoa_nhan(khop_chuong.group(1))
        return 2, nhan_ngan, van_ban

    # Mục (Cấp 3)
    khop_muc = _RE_MUC.match(van_ban)
    if khop_muc:
        nhan_ngan = _chuan_hoa_nhan(khop_muc.group(1))
        return 3, nhan_ngan, van_ban

    # Điều (Cấp 4)
    khop_dieu = _RE_DIEU.match(van_ban)
    if khop_dieu:
        nhan_ngan = _chuan_hoa_nhan(khop_dieu.group(1))
        return 4, nhan_ngan, van_ban

    # Khoản (Cấp 5)
    khop_khoan = _RE_KHOAN.match(van_ban)
    if khop_khoan:
        nhan_ngan = _chuan_hoa_nhan(khop_khoan.group(1))
        return 5, nhan_ngan, van_ban

    return None


def xay_dung_duong_dan_muc(ngan_xep: dict[int, str]) -> str:
    """Xây dựng chuỗi đường dẫn phân cấp mục từ ngăn xếp các cấp độ hiện tại."""
    cac_cap_sap_xep = sorted(ngan_xep.keys())
    cac_nhan = [ngan_xep[c] for c in cac_cap_sap_xep if ngan_xep[c]]
    return " > ".join(cac_nhan) if cac_nhan else "Phần mở đầu"


def tach_khoi_van_ban(van_ban: str) -> list[str]:
    """Tách văn bản thành các khối đoạn văn hoặc bảng biểu hoàn chỉnh."""
    cac_dong = van_ban.split("\n")
    cac_khoi: list[str] = []
    khoi_hien_tai: list[str] = []
    trong_bang = False

    for dong in cac_dong:
        dong_strip = dong.strip()
        la_dong_bang = dong_strip.startswith("|") and dong_strip.endswith("|")

        if la_dong_bang:
            if not trong_bang and khoi_hien_tai:
                cac_khoi.append("\n".join(khoi_hien_tai).strip())
                khoi_hien_tai = []
            trong_bang = True
            khoi_hien_tai.append(dong)
            continue

        if trong_bang:
            # Kết thúc bảng
            trong_bang = False
            cac_khoi.append("\n".join(khoi_hien_tai).strip())
            khoi_hien_tai = []

        if not dong_strip:
            if khoi_hien_tai:
                cac_khoi.append("\n".join(khoi_hien_tai).strip())
                khoi_hien_tai = []
        else:
            khoi_hien_tai.append(dong)

    if khoi_hien_tai:
        cac_khoi.append("\n".join(khoi_hien_tai).strip())

    return [k for k in cac_khoi if k]


def _chia_nho_khoi_qua_dai(khoi: str, token_toi_da: int) -> list[str]:
    """Chia nhỏ một khối vượt quá token_toi_da theo từng dòng hoặc câu."""
    dong_list = khoi.split("\n")
    ket_qua: list[str] = []
    dem_tam: list[str] = []

    for d in dong_list:
        if not d.strip():
            continue
        tam_text = "\n".join(dem_tam + [d])
        if dem_tam and dem_token(tam_text) > token_toi_da:
            ket_qua.append("\n".join(dem_tam).strip())
            dem_tam = [d]
        else:
            dem_tam.append(d)

    if dem_tam:
        ket_qua.append("\n".join(dem_tam).strip())
    return ket_qua


def chia_doan_theo_nguong(
    noi_dung: str,
    token_toi_da: int,
) -> list[str]:
    """Chia nhỏ nội dung nếu vượt token_toi_da, bảo toàn bảng biểu không bị cắt giữa hàng."""
    if dem_token(noi_dung) <= token_toi_da:
        return [noi_dung]

    khoi_list = tach_khoi_van_ban(noi_dung)
    cac_doan: list[str] = []
    tich_luy: list[str] = []

    for khoi in khoi_list:
        la_bang = khoi.strip().startswith("|") and khoi.strip().endswith("|")
        token_khoi = dem_token(khoi)

        if token_khoi > token_toi_da and not la_bang:
            # Khối văn bản đơn lẻ vượt ngưỡng: phân tách theo dòng
            if tich_luy:
                cac_doan.append("\n\n".join(tich_luy))
                tich_luy = []
            cac_doan.extend(_chia_nho_khoi_qua_dai(khoi, token_toi_da))
            continue

        tam = "\n\n".join(tich_luy + [khoi]) if tich_luy else khoi
        if tich_luy and dem_token(tam) > token_toi_da:
            cac_doan.append("\n\n".join(tich_luy))
            tich_luy = [khoi]
        else:
            tich_luy.append(khoi)

    if tich_luy:
        cac_doan.append("\n\n".join(tich_luy))

    return cac_doan


def _tao_doan_cat(
    thu_tu: int,
    tieu_de_muc: str,
    duong_dan_muc: str,
    noi_dung: str,
) -> DoanCat:
    """Hàm bổ trợ đóng gói bản ghi DoanCat chuẩn hoá."""
    noi_dung_sach = noi_dung.strip()
    so_tok = dem_token(noi_dung_sach)
    noi_dung_nhung = f"{tieu_de_muc}\n\n{noi_dung_sach}"
    return DoanCat(
        thu_tu=thu_tu,
        tieu_de_muc=tieu_de_muc,
        duong_dan_muc=duong_dan_muc,
        noi_dung=noi_dung_sach,
        so_token=so_tok,
        noi_dung_nhung=noi_dung_nhung,
    )


def cat_doan(van_ban_md: str, token_doan_toi_da: int = 500) -> list[DoanCat]:
    """Cắt văn bản Markdown theo cấu trúc phân cấp pháp quy/tiêu đề và giới hạn token."""
    cac_dong = van_ban_md.splitlines()
    danh_sach_doan: list[DoanCat] = []
    ngan_xep_duong_dan: dict[int, str] = {}

    tieu_de_muc_hien_tai = "Phần mở đầu"
    duong_dan_hien_tai = "Phần mở đầu"
    cap_do_hien_tai: int | None = None
    dong_noi_dung_hien_tai: list[str] = []
    so_thu_tu = 1

    def _dong_doan_hien_tai() -> None:
        nonlocal so_thu_tu
        noi_dung_gop = "\n".join(dong_noi_dung_hien_tai).strip()
        if not noi_dung_gop:
            # Nếu là mục lá (Điều, Khoản) không có dòng thân riêng, tiêu đề chính là nội dung
            if cap_do_hien_tai in (4, 5, 6):
                noi_dung_gop = tieu_de_muc_hien_tai
            else:
                return

        cac_phan_nho = chia_doan_theo_nguong(noi_dung_gop, token_doan_toi_da)
        for phan in cac_phan_nho:
            danh_sach_doan.append(
                _tao_doan_cat(
                    thu_tu=so_thu_tu,
                    tieu_de_muc=tieu_de_muc_hien_tai,
                    duong_dan_muc=duong_dan_hien_tai,
                    noi_dung=phan,
                )
            )
            so_thu_tu += 1
        dong_noi_dung_hien_tai.clear()

    for dong in cac_dong:
        thong_tin_tieu_de = nhan_dien_tieu_de(dong)
        if thong_tin_tieu_de is None:
            dong_noi_dung_hien_tai.append(dong)
            continue

        cap_do, nhan_ngan, tieu_de_day_du = thong_tin_tieu_de

        # Đóng đoạn nội dung đang tích luỹ trước khi bắt đầu mục mới
        _dong_doan_hien_tai()

        # Cập nhật ngăn xếp đường dẫn mục: loại bỏ các cấp con sâu hơn cấp hiện tại
        ngan_xep_duong_dan = {
            c: v for c, v in ngan_xep_duong_dan.items() if c < cap_do
        }
        if cap_do == 2:
            # Bắt đầu chương: loại bỏ cấp 1 để đường dẫn gọn gàng: "Chương II > Điều 5 > Khoản 2"
            ngan_xep_duong_dan.pop(1, None)
        ngan_xep_duong_dan[cap_do] = nhan_ngan

        cap_do_hien_tai = cap_do
        tieu_de_muc_hien_tai = tieu_de_day_du
        duong_dan_hien_tai = xay_dung_duong_dan_muc(ngan_xep_duong_dan)

    # Đóng đoạn cuối cùng
    _dong_doan_hien_tai()

    return danh_sach_doan
