"""Giám sát tình trạng bộ chạy cục bộ và theo dõi sức khỏe hệ thống.

Thực hiện kiểm tra trạng thái bộ chạy (Ollama / LM Studio), phát hiện lệch
ngữ cảnh cấu hình và theo dõi chu kỳ nạp/giải phóng mô hình trong VRAM.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config import CauHinhHeThong, cau_hinh
from app.core.loi import LoiUngDung
from app.core.nhat_ky import ghi_nhat_ky_chang, lay_ma_yeu_cau
from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.llm.bo_chay_local import (
    ThongTinModelDangNap,
    doc_ngu_canh_thuc_te,
    lay_bo_chay,
)

logger = logging.getLogger(__name__)

# Router cho các API giám sát hệ thống
router = APIRouter(prefix="/api/v1/giam-sat", tags=["giam-sat"])

# Đếm số lần model bậc 1 vắng mặt trong bộ nhớ liên tiếp
_so_lan_bac_1_vang_mat = 0

GHI_CHU_VRAM_DOCKER = (
    "backend chạy trong container Linux trên Docker Desktop nên KHÔNG có nvidia-smi; "
    "người vận hành đối chiếu bằng nvidia-smi chạy trên Windows."
)


class ModelDangNapDTO(BaseModel):
    """Thông tin chi tiết một mô hình đang nạp trong bộ nhớ."""

    ten: str
    kich_thuoc_byte: int | None = None
    kich_thuoc_vram_byte: int | None = None
    dung_luong_vram_gb: float | None = None
    het_han_luc: str | None = None
    so_giay_con_lai: float | None = None


class NguCanhModelDTO(BaseModel):
    """So sánh ngữ cảnh cấu hình và thực tế của một mô hình."""

    bac: str
    model: str
    num_ctx_cau_hinh: int
    num_ctx_thuc_te: int | None = None
    co_lech: bool = False


class ThongTinVramDTO(BaseModel):
    """Ước lượng tình trạng bộ nhớ VRAM của GPU."""

    dung_luong_vram_gb: int | float | None = None
    tong_vram_da_dung_byte: int | None = None
    tong_vram_da_dung_gb: float | None = None
    vram_con_trong_gb: float | None = None
    ghi_chu: str = GHI_CHU_VRAM_DOCKER
    ly_do: str | None = None


class ThongTinBacHoSo(BaseModel):
    """Thông tin cấu hình một bậc mô hình trong hồ sơ GPU."""

    model: str
    num_ctx: int


class PhanHoiGiamSatBoChay(BaseModel):
    """Phản hồi kiểm tra tình trạng bộ chạy cho vai trò quản trị."""

    ho_so_gpu: str
    dung_luong_vram_gb: int
    bac_1: ThongTinBacHoSo
    bac_2: ThongTinBacHoSo
    model_dang_nap: list[ModelDangNapDTO] = Field(default_factory=list)
    ngu_canh: list[NguCanhModelDTO] = Field(default_factory=list)
    co_lech: bool = False
    vram: ThongTinVramDTO


def tinh_so_giay_con_lai(het_han_luc_str: str | None) -> float | None:
    """Tính số giây còn lại cho tới thời điểm hết hạn keep_alive (UTC)."""
    if not het_han_luc_str:
        return None
    try:
        chuoi_chuan = het_han_luc_str.strip()
        if chuoi_chuan.endswith("Z"):
            chuoi_chuan = chuoi_chuan[:-1] + "+00:00"
        chuoi_chuan = re.sub(r"(\.\d{6})\d+", r"\1", chuoi_chuan)
        het_han_dt = datetime.fromisoformat(chuoi_chuan)
        bay_gio = datetime.now(timezone.utc)
        con_lai = (het_han_dt - bay_gio).total_seconds()
        return max(0.0, round(con_lai, 1))
    except (ValueError, TypeError):
        return None


def _tao_model_dto(m: ThongTinModelDangNap) -> ModelDangNapDTO:
    """Chuyển đổi dữ liệu model đang nạp sang đối tượng DTO có số giây còn lại."""
    vram_gb = (
        round(m.kich_thuoc_vram_byte / (1024**3), 2)
        if m.kich_thuoc_vram_byte is not None
        else None
    )
    return ModelDangNapDTO(
        ten=m.ten,
        kich_thuoc_byte=m.kich_thuoc_byte,
        kich_thuoc_vram_byte=m.kich_thuoc_vram_byte,
        dung_luong_vram_gb=vram_gb,
        het_han_luc=m.het_han_luc,
        so_giay_con_lai=tinh_so_giay_con_lai(m.het_han_luc),
    )


def _tinh_uoc_luong_vram(
    dung_luong_tong_gb: int,
    ds_model: list[ThongTinModelDangNap],
    co_loi: bool,
    thong_diep_loi: str | None,
) -> ThongTinVramDTO:
    """Tính toán bộ nhớ VRAM đã dùng và còn trống dựa trên thông tin bộ chạy."""
    if co_loi:
        return ThongTinVramDTO(
            dung_luong_vram_gb=dung_tong_gb if (dung_tong_gb := dung_luong_tong_gb) else None,
            ly_do=thong_diep_loi or "Không thể kết nối tới bộ chạy.",
        )

    cac_vram = [m.kich_thuoc_vram_byte for m in ds_model if m.kich_thuoc_vram_byte is not None]
    if not cac_vram and ds_model:
        return ThongTinVramDTO(
            dung_luong_vram_gb=dung_luong_tong_gb,
            ly_do="Bộ chạy không cung cấp trường thông tin size_vram.",
        )

    tong_bytes = sum(cac_vram)
    da_dung_gb = round(tong_bytes / (1024**3), 2)
    con_trong_gb = round(max(0.0, float(dung_luong_tong_gb) - da_dung_gb), 2)

    return ThongTinVramDTO(
        dung_luong_vram_gb=dung_luong_tong_gb,
        tong_vram_da_dung_byte=tong_bytes,
        tong_vram_da_dung_gb=da_dung_gb,
        vram_con_trong_gb=con_trong_gb,
    )


async def lay_thong_tin_bo_chay(
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> PhanHoiGiamSatBoChay:
    """Thu thập thông tin toàn diện về trạng thái hiện tại của bộ chạy cục bộ."""
    cfg = cau_hinh_he_thong or cau_hinh
    bo_chay = lay_bo_chay(cfg)

    ds_nap_raw: list[ThongTinModelDangNap] = []
    co_loi = False
    ly_do_loi: str | None = None

    try:
        ds_nap_raw = await bo_chay.doc_trang_thai_bo_chay()
    except Exception as err:  # noqa: BLE001
        co_loi = True
        ly_do_loi = f"Không kết nối được bộ chạy: {err}"
        logger.warning("Lỗi đọc trạng thái bộ chạy: %s", err)

    model_dtos = [_tao_model_dto(m) for m in ds_nap_raw]
    vram_dto = _tinh_uoc_luong_vram(cfg.dung_luong_vram_gb, ds_nap_raw, co_loi, ly_do_loi)

    ngu_canh_list: list[NguCanhModelDTO] = []
    co_lech_chung = False

    for b in cfg.bac_local:
        ctx_thuc_te = await doc_ngu_canh_thuc_te(b.model, bo_chay, cfg)
        lech = ctx_thuc_te is not None and ctx_thuc_te != b.num_ctx
        if lech:
            co_lech_chung = True
        ngu_canh_list.append(
            NguCanhModelDTO(
                bac=b.bac,
                model=b.model,
                num_ctx_cau_hinh=b.num_ctx,
                num_ctx_thuc_te=ctx_thuc_te,
                co_lech=lech,
            )
        )

    b1 = cfg.bac_local[0]
    b2 = cfg.bac_local[1]

    return PhanHoiGiamSatBoChay(
        ho_so_gpu=cfg.ho_so_gpu_dang_chon,
        dung_luong_vram_gb=cfg.dung_luong_vram_gb,
        bac_1=ThongTinBacHoSo(model=b1.model, num_ctx=b1.num_ctx),
        bac_2=ThongTinBacHoSo(model=b2.model, num_ctx=b2.num_ctx),
        model_dang_nap=model_dtos,
        ngu_canh=ngu_canh_list,
        co_lech=co_lech_chung,
        vram=vram_dto,
    )


@router.get("/bo-chay", response_model=PhanHoiGiamSatBoChay)
async def lay_trang_thai_bo_chay_endpoint(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiGiamSatBoChay:
    """Endpoint trả về tình trạng bộ chạy cục bộ dành riêng cho vai trò quản trị."""
    ma_yc = lay_ma_yeu_cau()
    if nguoi.vai_tro != "quan_tri":
        raise LoiUngDung(
            ma="KHONG_CO_QUYEN",
            thong_diep="Chỉ quản trị viên mới có quyền xem tình trạng bộ chạy.",
            http=403,
            ma_yeu_cau=ma_yc,
        )
    return await lay_thong_tin_bo_chay()


async def kiem_tra_bo_chay_dinh_ky(
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> None:
    """Thực hiện một lượt kiểm tra định kỳ trạng thái bộ chạy và ghi nhật ký chặng."""
    global _so_lan_bac_1_vang_mat
    cfg = cau_hinh_he_thong or cau_hinh
    bo_chay = lay_bo_chay(cfg)
    b1 = cfg.bac_local[0]

    try:
        ds_nap = await bo_chay.doc_trang_thai_bo_chay()
    except Exception as err:  # noqa: BLE001
        logger.warning("Bộ chạy không trả lời khi kiểm tra định kỳ: %s", err)
        ghi_nhat_ky_chang(
            chang="trang_thai_bo_chay",
            thong_diep=f"Bộ chạy không phản hồi: {err}",
            muc=logging.WARNING,
            model=b1.model,
        )
        return

    b1_da_nap = any(m.ten == b1.model for m in ds_nap)
    if not b1_da_nap:
        _so_lan_bac_1_vang_mat += 1
        if _so_lan_bac_1_vang_mat >= 3:
            logger.warning(
                "Model bậc 1 (%s) không còn trong bộ nhớ 3 lần liên tiếp. "
                "Gợi ý tăng keep_alive (hiện tại: %s).",
                b1.model,
                cfg.local_chung.keep_alive,
            )
    else:
        _so_lan_bac_1_vang_mat = 0

    co_lech_ngu_canh = False
    for b in cfg.bac_local:
        ctx_thuc_te = await doc_ngu_canh_thuc_te(b.model, bo_chay, cfg)
        if ctx_thuc_te is not None and ctx_thuc_te != b.num_ctx:
            co_lech_ngu_canh = True
            logger.warning(
                "Lệch ngữ cảnh model '%s': cấu hình %d khác thực tế %d.",
                b.model,
                b.num_ctx,
                ctx_thuc_te,
            )

    muc_log = (
        logging.WARNING
        if (co_lech_ngu_canh or _so_lan_bac_1_vang_mat >= 3)
        else logging.INFO
    )
    thong_diep = (
        f"Trạng thái bộ chạy: {len(ds_nap)} model đang nạp. "
        f"Bậc 1 nạp: {b1_da_nap}. Lệch ngữ cảnh: {co_lech_ngu_canh}."
    )
    ghi_nhat_ky_chang(
        chang="trang_thai_bo_chay",
        thong_diep=thong_diep,
        muc=muc_log,
        model=b1.model,
        bac_local="chinh",
    )


async def vong_lap_giam_sat_bo_chay(
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    gian_cach_giay: float = 60.0,
) -> None:
    """Vòng lặp tác vụ nền chạy mỗi 60 giây kiểm tra trạng thái bộ chạy."""
    logger.info("Bắt đầu tác vụ nền giám sát bộ chạy (chu kỳ %s giây).", gian_cach_giay)
    while True:
        try:
            await asyncio.sleep(gian_cach_giay)
            await kiem_tra_bo_chay_dinh_ky(cau_hinh_he_thong)
        except asyncio.CancelledError:
            logger.info("Tác vụ nền giám sát bộ chạy đã dừng.")
            break
        except Exception as err:  # noqa: BLE001
            logger.warning("Lỗi không mong muốn trong tác vụ nền giám sát: %s", err)
