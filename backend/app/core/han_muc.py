"""Quản lý và kiểm soát 4 lớp hạn mức (Rate Limiting).

Tuân thủ nghiêm ngặt các quy định:
1. AGENTS.md:
   - 4 lớp hạn mức kiểm tra đúng thứ tự chi phí thấp trước, cao sau:
     a) Theo IP: HAN_MUC_IP_PHUT (mặc định 20), áp dụng cả với /dang-nhap.
     b) Theo người dùng mỗi giờ: HAN_MUC_MOI_NGUOI_GIO (mặc định 60); bac = pro nhân HE_SO_BAC_PRO.
     c) Theo ngày: tổng token sinh ra HAN_MUC_TOKEN_NGAY (mặc định 100.000) và chi phí đám mây theo bậc.
     d) Tối đa MỘT yêu cầu đang chạy cho mỗi người tại một thời điểm, giải phóng trong finally.
   - Ghi nhật ký kiểm toán nhat_ky_kiem_toan mỗi lần vượt hạn mức.
   - Trả HTTP 429, mã VUOT_HAN_MUC, header Retry-After tính đúng số giây.
2. naming.md, clean_code.md, type_safety.md:
   - Tên hàm snake_case, hàm < 40 dòng logic, type hints đầy đủ cho pyright.
"""

import asyncio
import ipaddress
import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import cau_hinh
from app.core.csdl import (
    HanMucDemModel,
    LuotGoiModel,
    NhatKyKiemToanModel,
    lay_sessionmaker_async,
)
from app.core.loi import LoiVuotHanMuc
from app.core.thoi_gian import hom_nay_vn, khoang_ngay_vn
from app.core.xac_thuc import NguoiDung

logger = logging.getLogger(__name__)

# Quản lý yêu cầu đang chạy trong tiến trình (Lớp d)
# LƯU Ý QUY MÔ: Dùng từ điển trong bộ nhớ tiến trình kèm asyncio.Lock() áp dụng cho
# mô hình một bản sao backend hiện tại. Khi triển khai nhiều bản sao (horizontal scaling)
# hoặc vượt vài nghìn req/phút thì chuyển sang Redis Distributed Lock (Giai đoạn 9).
_KHOA_TIEN_TRINH = asyncio.Lock()
_CAC_YEU_CAU_DANG_CHAY: set[int] = set()


def _la_proxy_tin_cay(dia_chi: str) -> bool:
    """Kết nối trực tiếp đến từ loopback hoặc mạng nội bộ Docker (nginx của frontend)."""
    try:
        ip = ipaddress.ip_address(dia_chi)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private


def lay_ip_yeu_cau(request: Request) -> str:
    """Xác định IP của client cho hạn mức lớp a.

    Chỉ tin tiêu đề proxy khi kết nối trực tiếp đến từ proxy nội bộ: X-Real-IP do nginx của
    frontend ghi đè bằng $remote_addr, hoặc phần tử CUỐI của X-Forwarded-For (do proxy gần
    nhất thêm vào). Phần tử đầu của X-Forwarded-For do phía gọi tự đặt nên không dùng.
    """
    ip_ket_noi = request.client.host if request.client and request.client.host else "127.0.0.1"
    if not _la_proxy_tin_cay(ip_ket_noi):
        return ip_ket_noi
    x_real_ip = request.headers.get("x-real-ip", "").strip()
    if x_real_ip:
        return x_real_ip
    x_forwarded_for = request.headers.get("x-forwarded-for", "")
    phan_tu_cuoi = x_forwarded_for.split(",")[-1].strip()
    return phan_tu_cuoi or ip_ket_noi


async def ghi_nhat_ky_kiem_toan_han_muc(
    nguoi_id: int | None,
    loai_han_muc: str,
    thong_diep: str,
    ma_yeu_cau: str,
    chi_tiet_phu: dict[str, int | float | str] | None = None,
) -> None:
    """Ghi một bản ghi nhật ký kiểm toán khi người dùng hoặc IP vượt hạn mức."""
    chi_tiet: dict[str, int | float | str] = {
        "loai": loai_han_muc,
        "thong_diep": thong_diep,
    }
    if chi_tiet_phu:
        chi_tiet.update(chi_tiet_phu)

    try:
        maker = lay_sessionmaker_async()
        async with maker() as phien, phien.begin():
            kiem_toan = NhatKyKiemToanModel(
                nguoi_id=nguoi_id,
                hanh_dong="vuot_han_muc",
                chi_tiet=chi_tiet,
                ma_yeu_cau=ma_yeu_cau,
            )
            phien.add(kiem_toan)
    except Exception as err:  # noqa: BLE001
        logger.error("[%s] Ghi nhật ký kiểm toán vượt hạn mức thất bại: %s", ma_yeu_cau, err)


async def kiem_tra_han_muc_ip(
    ip: str,
    ma_yeu_cau: str,
    phien: AsyncSession | None = None,
) -> None:
    """Lớp a: Kiểm tra hạn mức theo IP mỗi phút (chi phí thấp nhất, không chạm DB người dùng)."""
    gioi_han = cau_hinh.han_muc_ip_phut
    khoa = f"ip:{ip}"
    bay_gio = datetime.now(timezone.utc)
    moc_thoi_gian = bay_gio - timedelta(seconds=60)

    if phien is not None:
        await _thuc_hien_kiem_tra_ip(phien, khoa, moc_thoi_gian, bay_gio, gioi_han, ip, ma_yeu_cau)
        return

    maker = lay_sessionmaker_async()
    async with maker() as phien_moi, phien_moi.begin():
        await _thuc_hien_kiem_tra_ip(
            phien_moi, khoa, moc_thoi_gian, bay_gio, gioi_han, ip, ma_yeu_cau
        )


async def _thuc_hien_kiem_tra_ip(
    phien: AsyncSession,
    khoa: str,
    moc_thoi_gian: datetime,
    bay_gio: datetime,
    gioi_han: int,
    ip: str,
    ma_yeu_cau: str,
) -> None:
    """Truy vấn đếm lượt theo IP và xác định thời gian chờ Retry-After."""
    cau_lenh_dem = select(func.count(HanMucDemModel.id)).where(
        HanMucDemModel.khoa == khoa,
        HanMucDemModel.thoi_diem >= moc_thoi_gian,
    )
    so_luong = int((await phien.scalars(cau_lenh_dem)).first() or 0)

    if so_luong >= gioi_han:
        cau_lenh_cu_nhat = (
            select(HanMucDemModel.thoi_diem)
            .where(
                HanMucDemModel.khoa == khoa,
                HanMucDemModel.thoi_diem >= moc_thoi_gian,
            )
            .order_by(HanMucDemModel.thoi_diem.asc())
            .limit(1)
        )
        t_cu_nhat = (await phien.scalars(cau_lenh_cu_nhat)).first()
        so_giay_cho = 60
        if t_cu_nhat:
            do_lech = (t_cu_nhat + timedelta(seconds=60) - bay_gio).total_seconds()
            so_giay_cho = max(1, math.ceil(do_lech))

        thong_diep = (
            f"Địa chỉ IP đã gửi quá {gioi_han} yêu cầu trong 1 phút, "
            f"vui lòng thử lại sau {so_giay_cho} giây."
        )
        await ghi_nhat_ky_kiem_toan_han_muc(
            nguoi_id=None,
            loai_han_muc="ip_phut",
            thong_diep=thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet_phu={"ip": ip, "so_giay_cho": so_giay_cho},
        )
        raise LoiVuotHanMuc(
            thong_diep=thong_diep,
            so_giay_cho=so_giay_cho,
            loai_han_muc="ip_phut",
            ma_yeu_cau=ma_yeu_cau,
        )

    phien.add(HanMucDemModel(khoa=khoa, thoi_diem=bay_gio))


async def kiem_tra_han_muc_nguoi_gio(
    nguoi: NguoiDung,
    phien: AsyncSession,
    ma_yeu_cau: str,
) -> None:
    """Lớp b: Kiểm tra hạn mức theo người dùng mỗi giờ kèm hệ số nhân cho bậc pro."""
    he_so = cau_hinh.he_so_bac_pro if nguoi.bac == "pro" else 1.0
    gioi_han = int(cau_hinh.han_muc_moi_nguoi_gio * he_so)
    khoa = f"user:{nguoi.id}"
    bay_gio = datetime.now(timezone.utc)
    moc_thoi_gian = bay_gio - timedelta(seconds=3600)

    cau_lenh_dem = select(func.count(HanMucDemModel.id)).where(
        HanMucDemModel.khoa == khoa,
        HanMucDemModel.thoi_diem >= moc_thoi_gian,
    )
    so_luong = int((await phien.scalars(cau_lenh_dem)).first() or 0)

    if so_luong >= gioi_han:
        cau_lenh_cu_nhat = (
            select(HanMucDemModel.thoi_diem)
            .where(
                HanMucDemModel.khoa == khoa,
                HanMucDemModel.thoi_diem >= moc_thoi_gian,
            )
            .order_by(HanMucDemModel.thoi_diem.asc())
            .limit(1)
        )
        t_cu_nhat = (await phien.scalars(cau_lenh_cu_nhat)).first()
        so_giay_cho = 3600
        if t_cu_nhat:
            do_lech = (t_cu_nhat + timedelta(seconds=3600) - bay_gio).total_seconds()
            so_giay_cho = max(1, math.ceil(do_lech))

        so_phut_cho = max(1, math.ceil(so_giay_cho / 60))
        thong_diep = (
            f"Anh/Chị đã dùng hết {gioi_han} lượt hỏi trong giờ này, "
            f"vui lòng thử lại sau {so_phut_cho} phút."
        )
        await ghi_nhat_ky_kiem_toan_han_muc(
            nguoi_id=nguoi.id,
            loai_han_muc="nguoi_dung_gio",
            thong_diep=thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet_phu={"so_giay_cho": so_giay_cho, "bac": nguoi.bac},
        )
        raise LoiVuotHanMuc(
            thong_diep=thong_diep,
            so_giay_cho=so_giay_cho,
            loai_han_muc="nguoi_dung_gio",
            ma_yeu_cau=ma_yeu_cau,
        )

    phien.add(HanMucDemModel(khoa=khoa, thoi_diem=bay_gio))


async def kiem_tra_han_muc_ngay(
    nguoi: NguoiDung,
    phien: AsyncSession,
    ma_yeu_cau: str,
) -> None:
    """Lớp c: Kiểm tra tổng token sinh ra và chi phí đám mây theo bậc trong ngày (từ luot_goi)."""
    tu, den = khoang_ngay_vn(hom_nay_vn())
    bay_gio = datetime.now(timezone.utc)
    so_giay_cho = max(1, math.ceil((den - bay_gio).total_seconds()))

    cau_lenh_tong = select(
        func.coalesce(func.sum(LuotGoiModel.token_ra), 0),
        func.coalesce(func.sum(LuotGoiModel.chi_phi_usd), 0.0),
    ).where(
        LuotGoiModel.nguoi_id == str(nguoi.id),
        LuotGoiModel.thoi_diem >= tu,
        LuotGoiModel.thoi_diem < den,
        LuotGoiModel.thanh_cong.is_(True),
    )
    ket_qua = (await phien.execute(cau_lenh_tong)).first()
    tong_token_ra = int(ket_qua[0]) if ket_qua else 0
    tong_chi_phi_usd = float(ket_qua[1]) if ket_qua else 0.0

    # 1. Kiểm tra hạn mức token sinh ra trong ngày
    if tong_token_ra >= cau_hinh.han_muc_token_ngay:
        thong_diep = (
            f"Anh/Chị đã dùng hết hạn mức {cau_hinh.han_muc_token_ngay:,} "
            f"token sinh ra trong ngày hôm nay, vui lòng quay lại vào ngày mai."
        )
        await ghi_nhat_ky_kiem_toan_han_muc(
            nguoi_id=nguoi.id,
            loai_han_muc="token_ngay",
            thong_diep=thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet_phu={"tong_token_ra": tong_token_ra, "so_giay_cho": so_giay_cho},
        )
        raise LoiVuotHanMuc(
            thong_diep=thong_diep,
            so_giay_cho=so_giay_cho,
            loai_han_muc="token_ngay",
            ma_yeu_cau=ma_yeu_cau,
        )

    # 2. Kiểm tra hạn mức chi phí đám mây trong ngày theo bậc
    han_muc_chi_phi = (
        cau_hinh.han_muc_chi_phi_ngay_pro_usd
        if nguoi.bac == "pro"
        else cau_hinh.han_muc_chi_phi_ngay_free_usd
    )
    if tong_chi_phi_usd >= han_muc_chi_phi:
        thong_diep = (
            f"Anh/Chị đã dùng hết hạn mức chi phí đám mây ${han_muc_chi_phi:.2f} USD "
            f"trong ngày hôm nay, vui lòng quay lại vào ngày mai."
        )
        await ghi_nhat_ky_kiem_toan_han_muc(
            nguoi_id=nguoi.id,
            loai_han_muc="chi_phi_ngay",
            thong_diep=thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet_phu={"tong_chi_phi_usd": tong_chi_phi_usd, "so_giay_cho": so_giay_cho},
        )
        raise LoiVuotHanMuc(
            thong_diep=thong_diep,
            so_giay_cho=so_giay_cho,
            loai_han_muc="chi_phi_ngay",
            ma_yeu_cau=ma_yeu_cau,
        )


async def chiem_khe_yeu_cau(nguoi_id: int, ma_yeu_cau: str) -> None:
    """Lớp d: Chiếm khe xử lý độc quyền cho người dùng (tối đa 1 yêu cầu đồng thời)."""
    async with _KHOA_TIEN_TRINH:
        if nguoi_id in _CAC_YEU_CAU_DANG_CHAY:
            thong_diep = (
                "Anh/Chị đang có một yêu cầu khác đang được xử lý, "
                "vui lòng chờ yêu cầu đó hoàn thành."
            )
            await ghi_nhat_ky_kiem_toan_han_muc(
                nguoi_id=nguoi_id,
                loai_han_muc="dong_thoi",
                thong_diep=thong_diep,
                ma_yeu_cau=ma_yeu_cau,
                chi_tiet_phu={"so_giay_cho": 5},
            )
            raise LoiVuotHanMuc(
                thong_diep=thong_diep,
                so_giay_cho=5,
                loai_han_muc="dong_thoi",
                ma_yeu_cau=ma_yeu_cau,
            )
        _CAC_YEU_CAU_DANG_CHAY.add(nguoi_id)


async def giai_phong_khe_yeu_cau(nguoi_id: int) -> None:
    """Lớp d: Giải phóng khe xử lý của người dùng khi hoàn tất, gặp lỗi hoặc ngắt kết nối."""
    async with _KHOA_TIEN_TRINH:
        _CAC_YEU_CAU_DANG_CHAY.discard(nguoi_id)


def kiem_tra_dang_chay(nguoi_id: int) -> bool:
    """Kiểm tra người dùng hiện có yêu cầu nào đang xử lý hay không."""
    return nguoi_id in _CAC_YEU_CAU_DANG_CHAY


@asynccontextmanager
async def giu_khe_yeu_cau(nguoi_id: int, ma_yeu_cau: str) -> AsyncIterator[None]:
    """Context manager giữ khe xử lý độc quyền và luôn giải phóng trong finally."""
    await chiem_khe_yeu_cau(nguoi_id, ma_yeu_cau)
    try:
        yield
    finally:
        await giai_phong_khe_yeu_cau(nguoi_id)


async def kiem_tra_toan_bo_han_muc_chat(
    request: Request,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
) -> None:
    """Kiểm tra tuần tự 4 lớp hạn mức trước khi bắt đầu phiên chat hoặc stream."""
    ip = lay_ip_yeu_cau(request)
    maker = lay_sessionmaker_async()

    # 1. Lớp a: Theo IP (60 giây)
    await kiem_tra_han_muc_ip(ip, ma_yeu_cau)

    # 2. Lớp b & Lớp c: Theo người dùng giờ và token/chi phí ngày (mở giao dịch CSDL)
    async with maker() as phien, phien.begin():
        await kiem_tra_han_muc_nguoi_gio(nguoi, phien, ma_yeu_cau)
        await kiem_tra_han_muc_ngay(nguoi, phien, ma_yeu_cau)

    # 3. Lớp d: Tối đa 1 yêu cầu đang chạy
    await chiem_khe_yeu_cau(nguoi.id, ma_yeu_cau)


async def lay_thong_tin_han_muc_nguoi_dung(
    nguoi_id: int,
    bac: str,
    phien: AsyncSession,
) -> tuple[int, int, float, int, bool]:
    """Tính toán các chỉ số hạn mức người dùng phục vụ endpoint GET /api/v1/toi."""
    bay_gio = datetime.now(timezone.utc)
    moc_gio = bay_gio - timedelta(seconds=3600)
    tu, den = khoang_ngay_vn(hom_nay_vn())

    # Đã dùng trong giờ
    cau_lenh_gio = select(func.count(HanMucDemModel.id)).where(
        HanMucDemModel.khoa == f"user:{nguoi_id}",
        HanMucDemModel.thoi_diem >= moc_gio,
    )
    da_dung_gio = int((await phien.scalars(cau_lenh_gio)).first() or 0)

    # Hạn mức còn lại trong giờ
    he_so = cau_hinh.he_so_bac_pro if bac == "pro" else 1.0
    gioi_han_gio = int(cau_hinh.han_muc_moi_nguoi_gio * he_so)
    han_muc_con_lai = max(0, gioi_han_gio - da_dung_gio)

    # Token sinh ra và chi phí hôm nay
    cau_lenh_ngay = select(
        func.coalesce(func.sum(LuotGoiModel.token_ra), 0),
        func.coalesce(func.sum(LuotGoiModel.chi_phi_usd), 0.0),
    ).where(
        LuotGoiModel.nguoi_id == str(nguoi_id),
        LuotGoiModel.thoi_diem >= tu,
        LuotGoiModel.thoi_diem < den,
        LuotGoiModel.thanh_cong.is_(True),
    )
    kq_ngay = (await phien.execute(cau_lenh_ngay)).first()
    token_hom_nay = int(kq_ngay[0]) if kq_ngay else 0
    chi_phi_usd = float(kq_ngay[1]) if kq_ngay else 0.0

    dang_chay = kiem_tra_dang_chay(nguoi_id)

    return da_dung_gio, token_hom_nay, chi_phi_usd, han_muc_con_lai, dang_chay
