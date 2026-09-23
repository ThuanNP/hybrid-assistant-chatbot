"""Xác thực người dùng, quản lý phiên và phân quyền truy cập hệ thống.

Cung cấp các hàm băm và xác minh mật khẩu bcrypt, tạo và xác thực JWT,
quản lý refresh token trong CSDL, và các dependency FastAPI phân quyền.
"""

import hashlib
import logging
import re
import secrets
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from app.config import cau_hinh
from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
from app.core.loi import LoiUngDung
from app.core.nhat_ky import lay_ma_yeu_cau
from app.llm.chinh_sach import CheDoDinhTuyen, nap_cau_hinh_chinh_sach

logger = logging.getLogger(__name__)

# Hằng số cấu hình JWT và xác thực
THUAT_TOAN_JWT = "HS256"
THOI_HAN_ACCESS_TOKEN = timedelta(minutes=15)
THOI_HAN_REFRESH_TOKEN = timedelta(hours=8)
BIEU_THUC_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Context băm mật khẩu bcrypt qua passlib
_bo_bam_mat_khau = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class NguoiDung:
    """Thông tin người dùng phục vụ xác thực và phân quyền trong hệ thống."""

    id: int = 1
    email: str = "can_bo@vidu.com"
    ho_ten: str = "Cán bộ kiểm thử"
    vai_tro: str = "nguoi_dung"  # quan_tri | nguoi_dung | chi_doc
    bac: str = "free"  # free | pro
    phong_ban: str = "CNTT"
    pham_vi_doc: list[str] = field(default_factory=list)
    che_do_dinh_tuyen: CheDoDinhTuyen | str | None = None


def chuan_hoa_email(email_tho: str) -> str:
    """Loại bỏ khoảng trắng thừa hai đầu và chuyển địa chỉ email về chữ thường."""
    return email_tho.strip().lower()


def kiem_tra_dinh_dang_email(email: str) -> bool:
    """Kiểm tra địa chỉ email có đúng định dạng tiêu chuẩn bằng biểu thức chính quy."""
    return bool(BIEU_THUC_EMAIL.match(email))


def bam_mat_khau(mat_khau: str) -> str:
    """Băm mật khẩu bằng thuật toán bcrypt an toàn."""
    return _bo_bam_mat_khau.hash(mat_khau)


def xac_minh_mat_khau(mat_khau_tho: str, mat_khau_bam: str | None) -> bool:
    """So khớp mật khẩu thô với chuỗi băm bcrypt."""
    if not mat_khau_bam:
        return False
    return _bo_bam_mat_khau.verify(mat_khau_tho, mat_khau_bam)


def bam_refresh_token(token_tho: str) -> str:
    """Băm refresh token bằng SHA-256 để lưu trữ an toàn trong cơ sở dữ liệu."""
    return hashlib.sha256(token_tho.encode("utf-8")).hexdigest()


def tao_access_token(nguoi: NguoiDung) -> str:
    """Phát JSON Web Token (JWT) ngắn hạn có thời hạn 15 phút được ký bằng APP_SECRET."""
    khoa_bi_mat = cau_hinh.app_secret or "khoa-bi-mat-dev-khong-dung-trong-van-hanh"
    thoi_diem_tao = datetime.now(timezone.utc)
    thoi_diem_het_han = thoi_diem_tao + THOI_HAN_ACCESS_TOKEN

    tai_lieu = {
        "sub": str(nguoi.id),
        "email": nguoi.email,
        "ho_ten": nguoi.ho_ten,
        "vai_tro": nguoi.vai_tro,
        "bac": nguoi.bac,
        "phong_ban": nguoi.phong_ban,
        "exp": int(thoi_diem_het_han.timestamp()),
        "iat": int(thoi_diem_tao.timestamp()),
    }
    return jwt.encode(tai_lieu, khoa_bi_mat, algorithm=THUAT_TOAN_JWT)


def tao_refresh_token() -> tuple[str, str, datetime]:
    """Tạo refresh token ngẫu nhiên 48 byte an toàn, trả về token thô, băm và hạn dùng 8 giờ."""
    token_tho = secrets.token_urlsafe(48)
    token_bam = bam_refresh_token(token_tho)
    het_han_luc = datetime.now(timezone.utc) + THOI_HAN_REFRESH_TOKEN
    return token_tho, token_bam, het_han_luc


def kiem_tra_an_toan_xac_thuc() -> None:
    """Từ chối khởi động ứng dụng nếu cấu hình bảo mật không an toàn."""
    if cau_hinh.moi_truong == "prod":
        if cau_hinh.xac_thuc_gia:
            thong_diep = (
                "LỖI CẤU HÌNH BẢO MẬT: XAC_THUC_GIA=true không được phép ở MOI_TRUONG=prod. "
                "Ứng dụng từ chối khởi động."
            )
            logger.critical(thong_diep)
            sys.exit(thong_diep)

        secret = (cau_hinh.app_secret or "").strip()
        cac_gia_tri_khong_hop_le = {
            "",
            "dan-khoa-that-vao-day",
            "secret",
            "changeme",
            "khoa-bi-mat-dev-khong-dung-trong-van-hanh",
            "12345678901234567890123456789012",
        }
        if not secret or len(secret) < 32 or secret in cac_gia_tri_khong_hop_le:
            thong_diep = (
                "LỖI CẤU HÌNH BẢO MẬT: APP_SECRET trong môi trường prod bắt buộc phải có, "
                "độ dài tối thiểu 32 ký tự và không được sử dụng giá trị mẫu mặc định."
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
        async with maker() as phien, phien.begin():
            cau_lenh = select(NguoiDungModel).where(NguoiDungModel.id == 1)
            nd_ton_tai = (await phien.scalars(cau_lenh)).first()
            if nd_ton_tai is None:
                logger.info("Chế độ dev: khởi tạo người dùng giả lập id=1 trong bảng nguoi_dung")
                nd_moi = NguoiDungModel(
                    id=1,
                    email="can_bo@vidu.com",
                    mat_khau_bam=None,
                    ho_ten="Cán bộ kiểm thử",
                    vai_tro="nguoi_dung",
                    bac="free",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
                phien.add(nd_moi)
    except Exception as err:  # noqa: BLE001
        logger.warning("Không thể khởi tạo người dùng giả lập trong cơ sở dữ liệu: %s", err)


def _xac_dinh_che_do_theo_phong_ban(phong_ban: str) -> CheDoDinhTuyen | None:
    """Tra cứu chế độ định tuyến cục bộ nếu phòng ban thuộc danh sách phong_ban_chi_local."""
    cs_dl = nap_cau_hinh_chinh_sach()
    if phong_ban in cs_dl.phong_ban_chi_local:
        return CheDoDinhTuyen.CHI_LOCAL
    return None


async def lay_nguoi_dung_hien_tai(request: Request) -> NguoiDung:
    """Lấy thông tin người dùng hiện tại phục vụ phân quyền và định tuyến.

    Ghi chú: Đây là nơi Giai đoạn 8 thay bằng OIDC; mọi nơi khác chỉ nhận NguoiDung.
    """
    if cau_hinh.xac_thuc_gia:
        che_do_dev = _xac_dinh_che_do_theo_phong_ban("CNTT")
        return NguoiDung(che_do_dinh_tuyen=che_do_dev)

    ma_yc = lay_ma_yeu_cau()

    if request is None:
        raise LoiUngDung(
            ma="CHUA_XAC_THUC",
            thong_diep="Yêu cầu chưa được xác thực danh tính.",
            http=401,
            ma_yeu_cau=ma_yc,
        )

    tieu_de_auth = request.headers.get("Authorization")
    if not tieu_de_auth or not tieu_de_auth.startswith("Bearer "):
        raise LoiUngDung(
            ma="CHUA_XAC_THUC",
            thong_diep="Thiếu hoặc sai định dạng tiêu đề Authorization.",
            http=401,
            ma_yeu_cau=ma_yc,
        )

    token = tieu_de_auth.split(" ", 1)[1].strip()
    khoa_bi_mat = cau_hinh.app_secret or "khoa-bi-mat-dev-khong-dung-trong-van-hanh"

    try:
        tai_lieu = jwt.decode(token, khoa_bi_mat, algorithms=[THUAT_TOAN_JWT])
        nguoi_id_str = tai_lieu.get("sub")
        if not nguoi_id_str:
            raise LoiUngDung(
                ma="CHUA_XAC_THUC",
                thong_diep="Mã xác thực không hợp lệ.",
                http=401,
                ma_yeu_cau=ma_yc,
            )
        nguoi_id = int(nguoi_id_str)
    except (JWTError, ValueError) as err:
        logger.debug("Giải mã token JWT thất bại: %s", err)
        raise LoiUngDung(
            ma="CHUA_XAC_THUC",
            thong_diep="Mã xác thực không hợp lệ hoặc đã hết hạn.",
            http=401,
            ma_yeu_cau=ma_yc,
        ) from err

    maker = lay_sessionmaker_async()
    async with maker() as phien:
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.id == nguoi_id)
        nd = (await phien.scalars(cau_lenh)).first()

        if nd is None or not nd.dang_hoat_dong:
            raise LoiUngDung(
                ma="CHUA_XAC_THUC",
                thong_diep="Tài khoản không tồn tại hoặc đã bị khóa.",
                http=401,
                ma_yeu_cau=ma_yc,
            )

        che_do = _xac_dinh_che_do_theo_phong_ban(nd.phong_ban)

        return NguoiDung(
            id=nd.id,
            email=nd.email,
            ho_ten=nd.ho_ten,
            vai_tro=nd.vai_tro,
            bac=nd.bac or "free",
            phong_ban=nd.phong_ban,
            che_do_dinh_tuyen=che_do,
        )


def can_vai_tro(
    *cac_vai_tro_cho_phep: str,
) -> Callable[[NguoiDung], Coroutine[Any, Any, NguoiDung]]:
    """Tạo dependency kiểm tra người dùng có một trong các vai trò được phép."""

    async def _kiem_tra(
        nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
    ) -> NguoiDung:
        if nguoi.vai_tro not in cac_vai_tro_cho_phep:
            raise LoiUngDung(
                ma="KHONG_CO_QUYEN",
                thong_diep="Người dùng không có quyền thực hiện hành động này.",
                http=403,
                ma_yeu_cau=lay_ma_yeu_cau(),
            )
        return nguoi

    return _kiem_tra
