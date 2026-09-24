"""Mô-đun kiểm tra ngưỡng từ chối RAG và xử lý phản hồi có kiểm soát.

Căn cứ thiết kế:
- Sau tái xếp hạng, nếu điểm cao nhất nhỏ hơn nguong_tu_choi (config/rag.yaml),
  hệ thống từ chối trả lời và TUYỆT ĐỐI KHÔNG gọi mô hình sinh văn bản (goi_mo_hinh).
- Phản hồi từ chối trả về mã HTTP 200 (không phải mã lỗi 4xx/5xx) để không làm
  phát cảnh báo giả trên các biểu đồ giám sát tỷ lệ lỗi hệ thống.
- Ghi nhận lượt vào CSDL với tu_choi = true và diem_cao_nhat phục vụ phân tích.
"""

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.hoi_thoai import luu_cap_luot_hoi_thoai
from app.core.csdl import LuotModel
from app.llm.router import _doc_cau_hinh_rag
from app.rag.schemas import DanhSachUngVien, KetQuaTuChoi, UngVien

logger = logging.getLogger(__name__)

__all__ = [
    "doc_loi_nhac_tu_choi",
    "ghi_luot_tu_choi",
    "kiem_tra_nguong",
    "lay_diem_cao_nhat",
]

# Đường dẫn mặc định tới tệp lời nhắc từ chối
_DUONG_DAN_TU_CHOI_MAC_DINH = (
    Path(__file__).resolve().parents[3] / "prompts" / "tu_choi.md"
)

# Câu trả lời từ chối dự phòng khi tệp prompt không tồn tại
_CAU_TRA_LOI_DU_PHONG = (
    "Trợ lý nội bộ chưa tìm thấy căn cứ trong kho tài liệu hiện hành cho câu hỏi này. "
    "Anh/Chị vui lòng liên hệ bộ phận phụ trách quy trình để được hướng dẫn."
)
_PHIEN_BAN_DU_PHONG = "2026-09-24.1"


def doc_loi_nhac_tu_choi(duong_dan: Path | None = None) -> tuple[str, str]:
    """Đọc nội dung thông điệp từ chối và phiên bản từ prompts/tu_choi.md.

    Trả về:
    - cau_tra_loi: Nội dung câu trả lời mẫu cho người dùng.
    - phien_ban: Phiên bản của tệp prompt.
    """
    tep = duong_dan or _DUONG_DAN_TU_CHOI_MAC_DINH
    if not tep.exists():
        return _CAU_TRA_LOI_DU_PHONG, _PHIEN_BAN_DU_PHONG

    try:
        toan_bo = tep.read_text(encoding="utf-8").strip()
        cac_dong = toan_bo.splitlines()
        phien_ban = _PHIEN_BAN_DU_PHONG
        dong_noi_dung: list[str] = []

        for dong in cac_dong:
            dong_strip = dong.strip()
            if dong_strip.startswith("phien_ban:"):
                phien_ban = dong_strip.split(":", 1)[1].strip()
            elif dong_strip:
                dong_noi_dung.append(dong_strip)

        cau_tra_loi = " ".join(dong_noi_dung) if dong_noi_dung else _CAU_TRA_LOI_DU_PHONG
        return cau_tra_loi, phien_ban
    except Exception as err:  # noqa: BLE001
        logger.warning("Không thể đọc tệp prompt từ chối từ %s: %s", tep, err)
        return _CAU_TRA_LOI_DU_PHONG, _PHIEN_BAN_DU_PHONG


def lay_diem_cao_nhat(danh_sach_ung_vien: list[UngVien] | DanhSachUngVien) -> float:
    """Xác định điểm số tái xếp hạng cao nhất trong danh sách ứng viên."""
    if not danh_sach_ung_vien:
        return 0.0

    cac_diem = [
        float(uv.diem_tai_xep_hang or 0.0)
        for uv in danh_sach_ung_vien
        if uv.diem_tai_xep_hang is not None
    ]
    return max(cac_diem) if cac_diem else 0.0


def kiem_tra_nguong(
    danh_sach_ung_vien: list[UngVien] | DanhSachUngVien,
    *,
    nguong_tu_choi: float | None = None,
    cau_hinh_rag: dict[str, Any] | None = None,
    duong_dan_prompt: Path | None = None,
) -> KetQuaTuChoi | None:
    """Kiểm tra điểm tái xếp hạng cao nhất có đạt ngưỡng từ chối hay không.

    Nếu điểm cao nhất < nguong_tu_choi:
    - Trả về đối tượng KetQuaTuChoi (ma_trang_thai_http = 200).
    - Phía gọi TUYỆT ĐỐI KHÔNG gọi mô hình sinh văn bản.

    Nếu điểm cao nhất >= nguong_tu_choi:
    - Trả về None, cho phép tiếp tục luồng tạo ngữ cảnh và gọi mô hình.
    """
    rag_cfg = cau_hinh_rag or _doc_cau_hinh_rag()
    nguong = (
        float(nguong_tu_choi)
        if nguong_tu_choi is not None
        else float(rag_cfg.get("nguong_tu_choi", 0.16))
    )

    diem_cao_nhat = lay_diem_cao_nhat(danh_sach_ung_vien)

    if diem_cao_nhat < nguong:
        cau_tra_loi, phien_ban = doc_loi_nhac_tu_choi(duong_dan_prompt)
        return KetQuaTuChoi(
            tu_choi=True,
            cau_tra_loi=cau_tra_loi,
            diem_cao_nhat=round(diem_cao_nhat, 4),
            nguong_tu_choi=round(nguong, 4),
            phien_ban_prompt=phien_ban,
            ma_trang_thai_http=200,
        )

    return None


async def ghi_luot_tu_choi(
    phien: AsyncSession,
    hoi_thoai_id: int,
    noi_dung_nguoi: str,
    ket_qua_tu_choi: KetQuaTuChoi,
    ma_yeu_cau: str,
    nhan_du_lieu: str | None = None,
) -> tuple[LuotModel, LuotModel]:
    """Ghi nhận cặp lượt hỏi - từ chối vào CSDL với tu_choi = True và điểm cao nhất."""
    return await luu_cap_luot_hoi_thoai(
        phien,
        hoi_thoai_id=hoi_thoai_id,
        noi_dung_nguoi=noi_dung_nguoi,
        noi_dung_tro_ly=ket_qua_tu_choi.cau_tra_loi,
        kq_goi=None,
        ma_yeu_cau=ma_yeu_cau,
        nhan_du_lieu=nhan_du_lieu,
        phien_ban_prompt=ket_qua_tu_choi.phien_ban_prompt,
        nguon_tham_chieu=[],
        tu_choi=True,
        diem_cao_nhat=ket_qua_tu_choi.diem_cao_nhat,
    )
