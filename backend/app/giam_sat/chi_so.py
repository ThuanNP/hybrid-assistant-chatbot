"""Thu thập, tổng hợp và xuất các chỉ số vận hành hệ thống trợ lý AI.

Cung cấp các hàm phân tích số liệu thống kê về tốc độ sinh token, thời gian nạp model,
độ dài hàng đợi, tỷ lệ hạ cấp/rơi tầng và yêu cầu dữ liệu nhạy cảm theo Quy tắc 11.
"""

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import LuotGoiModel, LuotModel
from app.llm.chi_phi import tinh_ty_le_roi_tang


def _tinh_phan_vi(danh_sach: list[float], phan_vi: float) -> float:
    """Tính phân vị từ danh sách số thực (phan_vi từ 0.0 đến 1.0)."""
    if not danh_sach:
        return 0.0
    sap_xep = sorted(danh_sach)
    if len(sap_xep) == 1:
        return round(sap_xep[0], 2)
    k = (len(sap_xep) - 1) * phan_vi
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sap_xep[int(k)], 2)
    gia_tri = sap_xep[f] * (c - k) + sap_xep[c] * (k - f)
    return round(float(gia_tri), 2)


def _tinh_trung_vi(danh_sach: list[float]) -> float:
    """Tính trung vị từ danh sách số thực."""
    if not danh_sach:
        return 0.0
    return round(float(statistics.median(danh_sach)), 2)


async def tong_hop_chi_so_van_hanh(
    phien: AsyncSession,
    so_gio: int = 24,
) -> dict[str, Any]:
    """Tổng hợp 6 nhóm chỉ số vận hành trên cửa sổ thời gian chỉ định.

    Nguồn dữ liệu:
    - Bảng luot: toc_do_tok_s, thoi_gian_nap_ms, do_dai_hang_doi, da_cat_ngu_canh, nhan_du_lieu.
    - Bảng luot_goi: tang, thanh_cong, roi_tang, muc_dich (chỉ xét muc_dich = 'chat').
    """
    den_thoi_diem = datetime.now(timezone.utc)
    tu_thoi_diem = den_thoi_diem - timedelta(hours=so_gio)

    # 1. Truy vấn các lượt trợ lý trong bảng luot
    cau_lenh_luot = (
        select(
            LuotModel.toc_do_tok_s,
            LuotModel.thoi_gian_nap_ms,
            LuotModel.do_dai_hang_doi,
            LuotModel.nguon,
            LuotModel.tang,
            LuotModel.bac_local,
            LuotModel.da_cat_ngu_canh,
            LuotModel.nhan_du_lieu,
        )
        .where(
            LuotModel.tao_luc >= tu_thoi_diem,
            LuotModel.vai_tro == "tro_ly",
        )
    )
    ket_qua_luot = (await phien.execute(cau_lenh_luot)).all()

    # Tách dữ liệu tốc độ local và đám mây
    toc_do_local = [
        float(r.toc_do_tok_s)
        for r in ket_qua_luot
        if r.nguon == "local" and r.toc_do_tok_s > 0
    ]
    toc_do_dam_may = [
        float(r.toc_do_tok_s)
        for r in ket_qua_luot
        if r.nguon == "dam_may" and r.toc_do_tok_s > 0
    ]

    nhom_toc_do = {
        "local": {
            "trung_vi": _tinh_trung_vi(toc_do_local),
            "phan_vi_90": _tinh_phan_vi(toc_do_local, 0.9),
        },
        "dam_may": {
            "trung_vi": _tinh_trung_vi(toc_do_dam_may),
            "phan_vi_90": _tinh_phan_vi(toc_do_dam_may, 0.9),
        },
    }

    # Thời gian nạp model
    luot_local = [r for r in ket_qua_luot if r.nguon == "local"]
    thoi_gian_nap_duong = [
        float(r.thoi_gian_nap_ms)
        for r in luot_local
        if r.thoi_gian_nap_ms > 0
    ]
    ty_le_cho_nap = (
        round(len(thoi_gian_nap_duong) / len(luot_local), 4)
        if luot_local
        else 0.0
    )
    nhom_thoi_gian_nap = {
        "trung_vi": _tinh_trung_vi(thoi_gian_nap_duong),
        "ty_le_cho_nap": ty_le_cho_nap,
    }

    # Độ dài hàng đợi
    danh_sach_hang_doi = [int(r.do_dai_hang_doi or 0) for r in ket_qua_luot]
    nhom_hang_doi = {
        "trung_binh": (
            round(sum(danh_sach_hang_doi) / len(danh_sach_hang_doi), 2)
            if danh_sach_hang_doi
            else 0.0
        ),
        "dinh": max(danh_sach_hang_doi) if danh_sach_hang_doi else 0,
    }

    # 2. Truy vấn bảng luot_goi để tính tỷ lệ rơi tầng
    cau_lenh_lg = (
        select(
            LuotGoiModel.tang,
            LuotGoiModel.thanh_cong,
            LuotGoiModel.roi_tang,
            LuotGoiModel.muc_dich,
        )
        .where(
            LuotGoiModel.thoi_diem >= tu_thoi_diem,
            LuotGoiModel.muc_dich == "chat",
        )
    )
    ket_qua_lg = (await phien.execute(cau_lenh_lg)).all()

    # Tỷ lệ hạ cấp local (bậc nhỏ phục vụ trên tổng lượt local)
    so_luot_bac_nho = sum(
        1 for r in luot_local if str(r.bac_local).lower() in ("nho", "2")
    )
    ty_le_ha_cap_local = (
        round(so_luot_bac_nho / len(luot_local), 4)
        if luot_local
        else 0.0
    )

    # Tỷ lệ rơi ra đám mây (lượt rơi tầng mà tầng được phục vụ > 0)
    tong_luot_chat = len(ket_qua_lg)
    so_luot_roi_dam_may = sum(
        1 for r in ket_qua_lg if r.roi_tang and r.tang > 0
    )
    ty_le_roi_ra_dam_may = (
        round(so_luot_roi_dam_may / tong_luot_chat, 4)
        if tong_luot_chat > 0
        else 0.0
    )

    # Tỷ lệ rơi tầng chung dùng lại tinh_ty_le_roi_tang() từ app.llm.chi_phi
    ty_le_roi_tang_dam_may, _ = tinh_ty_le_roi_tang(gio_gan_nhat=so_gio)

    # 3. Tỷ lệ cắt ngữ cảnh
    so_luot_cat = sum(1 for r in ket_qua_luot if r.da_cat_ngu_canh)
    ty_le_cat_ngu_canh = (
        round(so_luot_cat / len(ket_qua_luot), 4)
        if ket_qua_luot
        else 0.0
    )

    # 4. Số yêu cầu nhạy cảm
    so_yeu_cau_nhay_cam = sum(
        1
        for r in ket_qua_luot
        if r.nhan_du_lieu and str(r.nhan_du_lieu).lower() == "nhay_cam"
    )

    return {
        "cua_so_gio": so_gio,
        "toc_do_tok_s": nhom_toc_do,
        "thoi_gian_nap_ms": nhom_thoi_gian_nap,
        "do_dai_hang_doi": nhom_hang_doi,
        "ty_le_ha_cap_local": ty_le_ha_cap_local,
        "ty_le_roi_ra_dam_may": ty_le_roi_ra_dam_may,
        "ty_le_roi_tang_dam_may": ty_le_roi_tang_dam_may,
        "ty_le_ha_cap_va_roi_tang": {
            "ty_le_ha_cap_local": ty_le_ha_cap_local,
            "ty_le_roi_ra_dam_may": ty_le_roi_ra_dam_may,
            "ty_le_roi_tang_dam_may": ty_le_roi_tang_dam_may,
        },
        "ty_le_cat_ngu_canh": ty_le_cat_ngu_canh,
        "so_yeu_cau_nhay_cam": so_yeu_cau_nhay_cam,
    }
