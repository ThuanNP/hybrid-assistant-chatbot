"""Xác thực người dùng và phân quyền truy cập hệ thống."""

import logging
import sys
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy import select

from app.config import cau_hinh
from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
from app.llm.chinh_sach import CheDoDinhTuyen

logger = logging.getLogger(__name__)


@dataclass
class NguoiDung:
    """Thông tin người dùng phục vụ xác thực và phân quyền."""

    id: int = 1
    ten_dang_nhap: str = "can_bo"
    ho_ten: str = "Cán bộ kiểm thử"
    vai_tro: str = "nguoi_dung"
    bac: str = "chinh"
    phong_ban: str = "CNTT"
    pham_vi_doc: list[str] = field(default_factory=list)
    che_do_dinh_tuyen: CheDoDinhTuyen | str | None = None


def kiem_tra_an_toan_xac_thuc() -> None:
    """Từ chối khởi động ứng dụng nếu cấu hình bảo mật không an toàn."""
    if cau_hinh.moi_truong == "prod" and cau_hinh.xac_thuc_gia:
        thong_diep = (
            "LỖI CẤU HÌNH BẢO MẬT: XAC_THUC_GIA=true không được phép ở MOI_TRUONG=prod. "
            "Ứng dụng từ chối khởi động."
        )
        logger.critical(thong_diep)
        sys.exit(thong_diep)


async def khoi_tao_nguoi_dung_gia_dev() -> None:
    """Đảm bảo bảng nguoi_dung có bản ghi id=1 khớp người dùng giả ở chế độ dev.

    Chỉ chạy khi XAC_THUC_GIA=true, tạo nếu chưa có để khóa ngoại hoi_thoai.nguoi_id không lỗi.
    Không đặt trong migration theo quy định.
    """
    if not cau_hinh.xac_thuc_gia:
        return

    try:
        maker = lay_sessionmaker_async()
        async with maker() as phien:
            cau_lenh = select(NguoiDungModel).where(NguoiDungModel.id == 1)
            nd_ton_tai = (await phien.scalars(cau_lenh)).first()
            if nd_ton_tai is None:
                logger.info("Chế độ dev: khởi tạo người dùng giả lập id=1 trong bảng nguoi_dung")
                nd_moi = NguoiDungModel(
                    id=1,
                    ten_dang_nhap="can_bo",
                    mat_khau_bam=None,
                    ho_ten="Cán bộ kiểm thử",
                    vai_tro="nguoi_dung",
                    bac="chinh",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
                phien.add(nd_moi)
                await phien.commit()
    except Exception as err:  # noqa: BLE001
        logger.warning("Không thể khởi tạo người dùng giả lập trong cơ sở dữ liệu: %s", err)


async def lay_nguoi_dung_hien_tai() -> NguoiDung:
    """Lấy thông tin người dùng hiện tại phục vụ phân quyền và định tuyến.

    Khi XAC_THUC_GIA=true: Trả về đối tượng NguoiDung giả cố định (id 1, CNTT, nguoi_dung).
    Khi XAC_THUC_GIA=false: Trả về mã lỗi 401 CHUA_XAC_THUC.
    Đây là điểm tích hợp sẽ được thay thế ở Giai đoạn 5 (JWT) và Giai đoạn 8 (SSO).
    """
    if cau_hinh.xac_thuc_gia:
        return NguoiDung()

    raise HTTPException(status_code=401, detail="CHUA_XAC_THUC")
