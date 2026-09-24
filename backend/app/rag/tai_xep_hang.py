"""Mô-đun tái xếp hạng (Reranker) ứng viên RAG theo năm dấu hiệu đặc thù tiếng Việt."""

import logging
import re
import unicodedata
from typing import Any

from app.llm.router import _doc_cau_hinh_rag
from app.rag.schemas import DanhSachUngVien, UngVien

logger = logging.getLogger(__name__)

__all__ = ["bo_dau_tieng_viet", "tai_xep_hang"]

# Biểu thức chính quy trích xuất chuỗi số, số hiệu văn bản và đơn vị kỹ thuật điện
MAU_SO_HIEU = re.compile(
    r"\b(?:\d+/\d{4}/[a-zA-Z0-9\-]+|\d+(?:[.,]\d+)?\s*(?:kw|kwh|mw|mva|v|kv|a|w|%|ngay|thang|nam)?)\b",
    re.IGNORECASE,
)


def bo_dau_tieng_viet(van_ban: str) -> str:
    """Loại bỏ dấu tiếng Việt để so khớp nhưng giữ nguyên văn bản hiển thị."""
    vb = re.sub(r"[đĐ]", "d", van_ban)
    chuan = unicodedata.normalize("NFKD", vb)
    return "".join(c for c in chuan if not unicodedata.combining(c)).lower()


def _chuan_hoa_so_sanh(chuoi: str) -> str:
    """Chuyển chuỗi về chữ thường và xóa sạch ký tự đặc biệt phục vụ so khớp số hiệu."""
    return re.sub(r"[^a-zA-Z0-9]", "", chuoi).lower()


def _tach_tu(van_ban: str) -> list[str]:
    """Tách danh sách từ (âm tiết) sau khi đã bỏ dấu tiếng Việt."""
    vb_khong_dau = bo_dau_tieng_viet(van_ban)
    return re.findall(r"\b[a-zA-Z0-9_]+\b", vb_khong_dau)


def _lay_bigram_am_tiet(cac_tu: list[str]) -> list[tuple[str, str]]:
    """Tạo tập hợp các cụm hai âm tiết (bigram) liên tiếp."""
    if len(cac_tu) < 2:
        return []
    return [(cac_tu[i], cac_tu[i + 1]) for i in range(len(cac_tu) - 1)]


def _trich_xuat_chuoi_so(van_ban: str) -> list[str]:
    """Trích xuất các số hiệu văn bản, chuỗi số và thông số kỹ thuật."""
    khop = MAU_SO_HIEU.findall(van_ban)
    ket_qua: list[str] = []
    for k in khop:
        k_s = k.strip()
        if any(c.isdigit() for c in k_s):
            ket_qua.append(k_s)
    return ket_qua


def _tinh_he_so_phat_doan_dai(
    so_token: int,
    nguong_chuan: int,
    token_toi_da: int,
    he_so_min: float,
) -> float:
    """Tính hệ số nhân phạt độ dài đoạn (giảm từ 1.00 về he_so_min)."""
    if so_token <= nguong_chuan:
        return 1.00
    khoang = max(1, token_toi_da - nguong_chuan)
    do_vuot = min(khoang, so_token - nguong_chuan)
    he_so = 1.00 - (1.00 - he_so_min) * (do_vuot / khoang)
    return max(he_so_min, min(1.00, he_so))


def _cham_diem_mot_ung_vien(
    cau_hoi: str,
    ung_vien: UngVien,
    trong_so: dict[str, float],
    cong_phu_tu_khoa: float,
    nguong_doan_dai: int,
    token_toi_da: int,
    he_so_min: float,
) -> float:
    """Chấm điểm ứng viên dựa trên 5 dấu hiệu và kiểm tra cổng phủ từ khóa."""
    tu_cau_hoi = _tach_tu(cau_hoi)
    if not tu_cau_hoi:
        return 0.0

    tap_tu_cau_hoi = set(tu_cau_hoi)
    tu_tieu_de = _tach_tu(ung_vien.tieu_de_muc)
    tu_than_doan = _tach_tu(ung_vien.noi_dung)
    tap_tu_doan = set(tu_tieu_de) | set(tu_than_doan)

    # 1. CỔNG PHỦ TỪ KHÓA: Nếu chứa dưới ngưỡng từ câu hỏi thì điểm bằng 0
    tu_trung = tap_tu_cau_hoi & tap_tu_doan
    ty_le_phu = len(tu_trung) / len(tap_tu_cau_hoi)
    if ty_le_phu < cong_phu_tu_khoa:
        return 0.0

    # 2. Dấu hiệu 1: Tỷ lệ cụm hai âm tiết (bigram) khớp
    bigram_cau_hoi = _lay_bigram_am_tiet(tu_cau_hoi)
    bigram_doan = set(_lay_bigram_am_tiet(tu_tieu_de + tu_than_doan))
    if bigram_cau_hoi:
        bigram_khop = sum(1 for bg in bigram_cau_hoi if bg in bigram_doan)
        diem_bigram = (bigram_khop / len(bigram_cau_hoi)) * trong_so.get("bigram", 38.0)
    else:
        diem_bigram = trong_so.get("bigram", 38.0) if tu_cau_hoi[0] in tap_tu_doan else 0.0

    # 3. Dấu hiệu 2: Từ trong câu hỏi xuất hiện ở tieu_de_muc
    tu_tieu_de_set = set(tu_tieu_de)
    tu_tieu_de_khop = sum(1 for t in tap_tu_cau_hoi if t in tu_tieu_de_set)
    diem_tieu_de = (tu_tieu_de_khop / len(tap_tu_cau_hoi)) * trong_so.get("tieu_de_muc", 26.0)

    # 4. Dấu hiệu 3: Trùng khớp chuỗi số và số hiệu văn bản
    so_cau_hoi = _trich_xuat_chuoi_so(cau_hoi)
    if so_cau_hoi:
        chuoi_ghep = f"{ung_vien.ma_tai_lieu} {ung_vien.tieu_de_muc} {ung_vien.noi_dung}"
        chuoi_ghep_chuan = _chuan_hoa_so_sanh(chuoi_ghep)
        so_khop = 0
        for s in so_cau_hoi:
            s_chuan = _chuan_hoa_so_sanh(s)
            if s_chuan and s_chuan in chuoi_ghep_chuan:
                so_khop += 1
        diem_chuoi_so = (so_khop / len(so_cau_hoi)) * trong_so.get("chuoi_so", 20.0)
    else:
        diem_chuoi_so = 0.0

    # 5. Dấu hiệu 4: Từ trong câu hỏi xuất hiện ở thân đoạn
    tu_than_set = set(tu_than_doan)
    tu_than_khop = sum(1 for t in tap_tu_cau_hoi if t in tu_than_set)
    diem_than_doan = (tu_than_khop / len(tap_tu_cau_hoi)) * trong_so.get("than_doan", 16.0)

    # 6. Dấu hiệu 5: Hệ số nhân phạt đoạn dài (0.85 đến 1.00)
    do_dai_token = ung_vien.so_token or len(tu_than_doan)
    he_so_phat = _tinh_he_so_phat_doan_dai(
        do_dai_token, nguong_doan_dai, token_toi_da, he_so_min
    )

    diem_chua_phat = diem_bigram + diem_tieu_de + diem_chuoi_so + diem_than_doan
    return round(diem_chua_phat * he_so_phat, 4)


def tai_xep_hang(
    cau_hoi: str,
    danh_sach_ung_vien: list[UngVien],
    cau_hinh_rag: dict[str, Any] | None = None,
) -> DanhSachUngVien:
    """Tái xếp hạng tối đa 20 ứng viên đầu tiên dựa trên 5 dấu hiệu chất lượng.

    Trả về danh sách ứng viên mới được sắp xếp theo điểm tái xếp hạng giảm dần.
    """
    rag_cfg = cau_hinh_rag or _doc_cau_hinh_rag()
    trong_so_cfg = rag_cfg.get("trong_so_tai_xep_hang", {})
    trong_so = {
        "bigram": float(trong_so_cfg.get("bigram", 38.0)),
        "tieu_de_muc": float(trong_so_cfg.get("tieu_de_muc", 26.0)),
        "chuoi_so": float(trong_so_cfg.get("chuoi_so", 20.0)),
        "than_doan": float(trong_so_cfg.get("than_doan", 16.0)),
    }
    cong_phu = float(rag_cfg.get("cong_phu_tu_khoa", 0.30))
    nguong_dai = int(rag_cfg.get("nguong_doan_dai_bat_dau_phat", 200))
    token_max = int(rag_cfg.get("token_doan_toi_da", 500))
    he_so_min = float(rag_cfg.get("he_so_phat_doan_dai_min", 0.85))

    vb_thay_the = getattr(danh_sach_ung_vien, "van_ban_thay_the", None)

    # Chỉ chấm lại tối đa 20 ứng viên đầu tiên
    ung_vien_top_20 = list(danh_sach_ung_vien[:20])

    for uv in ung_vien_top_20:
        uv.diem_tai_xep_hang = _cham_diem_mot_ung_vien(
            cau_hoi=cau_hoi,
            ung_vien=uv,
            trong_so=trong_so,
            cong_phu_tu_khoa=cong_phu,
            nguong_doan_dai=nguong_dai,
            token_toi_da=token_max,
            he_so_min=he_so_min,
        )

    # Sắp xếp theo điểm tái xếp hạng giảm dần, phụ trợ bằng điểm rrf
    ket_qua_sap_xep = sorted(
        ung_vien_top_20,
        key=lambda x: (x.diem_tai_xep_hang or 0.0, x.diem_rrf),
        reverse=True,
    )

    return DanhSachUngVien(ket_qua_sap_xep, van_ban_thay_the=vb_thay_the)
