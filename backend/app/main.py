"""Điểm nhập chính khởi chạy ứng dụng FastAPI và hệ thống định tuyến API."""

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import tomllib
from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from app.chat.hoi_thoai import (
    SapXepHoiThoai,
    dem_cau_hoi_hom_nay,
    dem_so_luot_hoi,
    doc_phien_ban_loi_nhac,
    lay_danh_sach_hoi_thoai,
    lay_danh_sach_luot,
    lay_hoi_thoai,
    lay_ma_yeu_cau_roi_tang,
    luu_cap_luot_hoi_thoai,
    tao_hoi_thoai,
    tu_dat_tieu_de,
    xoa_mem_hoi_thoai,
)
from app.chat.ngu_canh import (
    dung_ngu_canh,
    tinh_ngan_sach_token,
    uoc_luong_so_luot_giu_duoc,
)
from app.chat.su_kien_sse import (
    YeuCauChatStream,
    tao_luong_su_kien,
    tao_nhan_ai,
)
from app.chat.thuong_gap import (
    lay_cau_hoi_thuong_gap_api,
    lay_huong_dan_su_dung_api,
)
from app.config import CauHinhBacLocal, cau_hinh
from app.core.bao_mat import (
    che_du_lieu_ca_nhan,
    dem_the_da_dung,
    kiem_duyet_dau_ra,
    kiem_duyet_dau_vao,
    kiem_tra_phoi_lo,
)
from app.core.csdl import (
    NguoiDungModel,
    NhatKyKiemToanModel,
    PhienDangNhapModel,
    lay_sessionmaker_async,
)
from app.core.han_muc import (
    giai_phong_khe_yeu_cau,
    kiem_tra_han_muc_ip,
    kiem_tra_toan_bo_han_muc_chat,
    lay_ip_yeu_cau,
    lay_thong_tin_han_muc_nguoi_dung,
)
from app.core.loi import (
    LoiUngDung,
    dang_ky_bo_bat_loi,
)
from app.core.nhat_ky import (
    dat_ma_yeu_cau,
    ghi_nhat_ky_chang,
    lay_ma_yeu_cau,
    sinh_ma_yeu_cau,
    thiet_lap_nhat_ky,
)
from app.core.xac_thuc import (
    NguoiDung,
    bam_refresh_token,
    chuan_hoa_email,
    khoi_tao_nguoi_dung_gia_dev,
    kiem_tra_an_toan_xac_thuc,
    kiem_tra_dinh_dang_email,
    lay_nguoi_dung_hien_tai,
    tao_access_token,
    tao_refresh_token,
    xac_minh_mat_khau,
)
from app.giam_sat.chi_so import tong_hop_chi_so_van_hanh
from app.giam_sat.suc_khoe import router as router_giam_sat
from app.giam_sat.suc_khoe import vong_lap_giam_sat_bo_chay
from app.hang_doi.dieu_phoi import TrangThaiHangDoi, dieu_phoi_mac_dinh
from app.llm.bo_chay_local import kiem_tra_khi_khoi_dong, lay_bo_chay
from app.llm.chi_phi import bao_cao_chi_phi
from app.llm.chinh_sach import (
    CheDoDinhTuyen,
    NhanDuLieu,
    nap_cau_hinh_chinh_sach,
    nhan_cua_hoi_thoai,
    xac_dinh_chuoi,
)
from app.llm.router import KetQuaGoi, goi_mo_hinh

# Khởi tạo định dạng nhật ký JSON một dòng cho toàn ứng dụng
thiet_lap_nhat_ky()

logger = logging.getLogger(__name__)

# Header chuẩn Server-Sent Events ngăn proxy và nginx đệm luồng dữ liệu
HEADER_SSE = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

# Kiểm tra an toàn cấu hình ngay khi nạp module
kiem_tra_an_toan_xac_thuc()

# Đọc số phiên bản từ backend/pyproject.toml theo .agents/rules/versioning.md
DUONG_DAN_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def doc_phien_ban() -> str:
    """Đọc số phiên bản từ backend/pyproject.toml."""
    with DUONG_DAN_PYPROJECT.open("rb") as tep:
        return str(tomllib.load(tep)["project"]["version"])


PHIEN_BAN = doc_phien_ban()

# Mã yêu cầu phía gọi gửi lên: chữ, số, gạch nối, gạch dưới; không nhận ký tự điều khiển
_MAU_MA_YEU_CAU_HOP_LE = re.compile(r"[A-Za-z0-9_-]{8,64}")


def _kiem_tra_cors_prod() -> None:
    """Kiểm tra quy định CORS: môi trường prod cấm tuyệt đối ký tự đại diện '*'."""
    if cau_hinh.moi_truong == "prod":
        for nguon in cau_hinh.cors_origins:
            if "*" in nguon:
                raise ValueError(
                    "Cấu hình CORS không hợp lệ: Môi trường prod cấm sử dụng ký tự '*' trong CORS_ORIGINS"
                )


_kiem_tra_cors_prod()


def _ghi_loi_tac_vu_nen(tac_vu: asyncio.Task[None]) -> None:
    """Ghi nhật ký lỗi của tác vụ nền thay vì để lỗi bị bỏ qua lặng lẽ."""
    if tac_vu.cancelled():
        return
    loi = tac_vu.exception()
    if loi is not None:
        logger.error("Kiểm tra bộ chạy lúc khởi động thất bại: %r", loi)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Kiểm tra an toàn, nạp người dùng dev và hâm nóng bộ chạy nền."""
    kiem_tra_an_toan_xac_thuc()
    kiem_tra_phoi_lo()
    await khoi_tao_nguoi_dung_gia_dev()
    tac_vu = asyncio.create_task(kiem_tra_khi_khoi_dong())
    tac_vu.add_done_callback(_ghi_loi_tac_vu_nen)
    tac_vu_giam_sat = asyncio.create_task(vong_lap_giam_sat_bo_chay())
    yield
    tac_vu.cancel()
    tac_vu_giam_sat.cancel()


# Môi trường prod tắt /docs, /redoc, /openapi.json để không công khai lược đồ API
_LA_PROD = cau_hinh.moi_truong == "prod"
app = FastAPI(
    title="Trợ lý AI nội bộ",
    version=PHIEN_BAN,
    lifespan=lifespan,
    docs_url=None if _LA_PROD else "/docs",
    redoc_url=None if _LA_PROD else "/redoc",
    openapi_url=None if _LA_PROD else "/openapi.json",
)

# Đăng ký router giám sát bộ chạy
app.include_router(router_giam_sat)

# Đăng ký bộ bắt lỗi toàn cục chuẩn hóa định dạng lỗi
dang_ky_bo_bat_loi(app)

# Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cau_hinh.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Cho giao diện khác nguồn đọc được mã yêu cầu và thời gian chờ khi bị giới hạn
    expose_headers=["X-Ma-Yeu-Cau", "Retry-After"],
)


@app.middleware("http")
async def middleware_ma_yeu_cau(request: Request, call_next: Any) -> Response:
    """Middleware gắn mã yêu cầu ma_yeu_cau 12 ký tự xuyên suốt mỗi chu trình HTTP."""
    # Nhận mã do phía gọi gửi để nối chuỗi truy vết, chỉ khi đúng dạng ký tự an toàn
    ma_yc = (request.headers.get("X-Ma-Yeu-Cau") or "").strip()
    if not _MAU_MA_YEU_CAU_HOP_LE.fullmatch(ma_yc):
        ma_yc = sinh_ma_yeu_cau()

    dat_ma_yeu_cau(ma_yc)
    phan_hoi: Response = await call_next(request)
    phan_hoi.headers["X-Ma-Yeu-Cau"] = ma_yc
    return phan_hoi


# ---------------------------------------------------------------------------
# Lược đồ Pydantic cho các API nghiệp vụ và xác thực
# ---------------------------------------------------------------------------


class YeuCauDangNhap(BaseModel):
    """Dữ liệu yêu cầu đăng nhập bằng email và mật khẩu."""

    email: str = Field(min_length=3, description="Địa chỉ email người dùng")
    mat_khau: str = Field(min_length=1, description="Mật khẩu tài khoản")


class ThongTinNguoiDungPhanHoi(BaseModel):
    """Thông tin hồ sơ người dùng trả về trong phiên xác thực."""

    id: int
    email: str
    ho_ten: str
    vai_tro: str
    bac: str
    phong_ban: str
    che_do_dinh_tuyen: str | None = None
    da_dung_trong_gio: int = 0
    token_da_sinh_hom_nay: int = 0
    chi_phi_hom_nay_usd: float = 0.0
    han_muc_con_lai: int = 0
    dang_chay: bool = False


class PhanHoiDangNhap(BaseModel):
    """Kết quả đăng nhập thành công chứa access token và hồ sơ người dùng."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    nguoi_dung: ThongTinNguoiDungPhanHoi


class PhanHoiLamMoiToken(BaseModel):
    """Kết quả làm mới access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class PhanHoiDangXuat(BaseModel):
    """Kết quả đăng xuất và thu hồi phiên làm việc."""

    thanh_cong: bool
    thong_diep: str


class YeuCauChat(BaseModel):
    """Dữ liệu yêu cầu cho endpoint chat không phát dòng."""

    hoi_thoai_id: int | None = None
    noi_dung: str = Field(
        min_length=1,
        max_length=cau_hinh.gioi_han_do_dai_tin_nhan,
        description="Nội dung câu hỏi của người dùng",
    )


class PhanHoiChat(BaseModel):
    """Kết quả phản hồi chat dạng hoàn chỉnh cho tích hợp máy với máy."""

    hoi_thoai_id: int
    noi_dung: str
    nguon: str
    tang: int
    bac_local: str | None = None
    model: str
    token_vao: int
    token_ra: int
    chi_phi_usd: float
    do_tre_ms: float
    toc_do_tok_s: float
    nhan_ai: str
    ma_yeu_cau: str = ""
    ha_cap: bool = False


class ItemHoiThoai(BaseModel):
    """Thông tin tóm tắt một cuộc hội thoại trong danh sách."""

    id: int
    tieu_de: str
    tao_luc: datetime
    cap_nhat_luc: datetime
    so_luot: int = 0


class DanhSachHoiThoai(BaseModel):
    """Phản hồi danh sách cuộc hội thoại có phân trang."""

    danh_sach: list[ItemHoiThoai]
    tong_so: int
    trang: int
    kich_thuoc: int


class ItemLuot(BaseModel):
    """Chi tiết một lượt tin nhắn trong hội thoại."""

    id: int
    vai_tro: str
    noi_dung: str
    nguon: str | None = None
    tang: int | None = None
    bac_local: str | None = None
    model_da_dung: str | None = None
    token_vao: int = 0
    token_ra: int = 0
    chi_phi_usd: float = 0.0
    toc_do_tok_s: float = 0.0
    do_tre_ms: float = 0.0
    da_cat_ngu_canh: bool = False
    so_luot_bi_cat: int = 0
    ma_yeu_cau: str | None = None
    # Chỉ có ở lượt trợ lý: nhãn AI dựng lại từ model và thời điểm, cờ hạ cấp đọc từ luot_goi
    nhan_ai: str | None = None
    ha_cap: bool = False
    tao_luc: datetime


class ChiTietHoiThoai(BaseModel):
    """Toàn bộ thông tin hội thoại kèm các lượt trao đổi theo thứ tự thời gian."""

    id: int
    tieu_de: str
    tao_luc: datetime
    cap_nhat_luc: datetime
    cac_luot: list[ItemLuot]


class PhanHoiXoaHoiThoai(BaseModel):
    """Phản hồi sau khi xoá mềm cuộc hội thoại."""

    thanh_cong: bool
    thong_diep: str


class ThongTinTangDamMay(BaseModel):
    """Thông tin tầng mô hình đám mây công khai (không lộ khoá API)."""

    tang: int
    ten: str
    model: str
    gia_vao_usd_moi_trieu: float
    gia_ra_usd_moi_trieu: float
    cua_so_ngu_canh: int
    kha_dung: bool


class ThongTinModels(BaseModel):
    """Tổng quan cấu hình mô hình hiện hành của hệ thống trợ lý."""

    che_do_dinh_tuyen: str
    ho_so_gpu: str
    bac_local: list[CauHinhBacLocal]
    chuoi_dam_may: list[ThongTinTangDamMay]


class ThongTinBacNguCanh(BaseModel):
    """Thông tin cửa sổ ngữ cảnh cấu hình và thực tế cho một bậc local."""

    bac: str
    model: str
    num_ctx_cau_hinh: int
    num_ctx_thuc_te: int | None = None


class TinhTrangNguCanh(BaseModel):
    """Hiện trạng ngữ cảnh tính toán dựa trên chuỗi mô hình."""

    bac_local: list[ThongTinBacNguCanh]
    ngan_sach_token: int
    so_luot_trung_binh_giu_duoc: int


class ItemCauHoiThuongGap(BaseModel):
    """Chi tiết một mục câu hỏi thường gặp."""

    ma: str
    nhom: str
    cau_hoi: str
    tra_loi: str


class PhanHoiCauHoiThuongGap(BaseModel):
    """Phản hồi danh sách câu hỏi thường gặp."""

    phien_ban: str
    muc: list[ItemCauHoiThuongGap]


class PhanHoiHuongDanSuDung(BaseModel):
    """Phản hồi tài liệu hướng dẫn sử dụng."""

    phien_ban: str
    noi_dung: str


# ---------------------------------------------------------------------------
# Endpoint kiểm tra sức khỏe và trạng thái (ở gốc)
# ---------------------------------------------------------------------------


@app.get("/health")
async def kiem_tra_song() -> dict[str, str]:
    """Chỉ xác nhận tiến trình còn sống; không truy cập cơ sở dữ liệu hay bộ chạy."""
    return {"trang_thai": "song", "phien_ban": PHIEN_BAN}


@app.get("/ready")
async def kiem_tra_san_sang() -> Response:
    """Kiểm tra CSDL và (bộ chạy local HOẶC ít nhất 1 tầng đám mây khả dụng).

    Kiểm tra bộ chạy qua liet_ke_model() bọc asyncio.wait_for 2 giây.
    Tuyệt đối không gọi httpx trực tiếp ngoài bo_chay_local.py và không gọi sinh văn bản.
    """
    csdl_ok = False
    try:
        maker = lay_sessionmaker_async()
        async with maker() as phien:
            await phien.execute(text("SELECT 1"))
            csdl_ok = True
    except Exception as err:  # noqa: BLE001
        logger.warning("Kiểm tra cơ sở dữ liệu thất bại tại /ready: %s", err)
        csdl_ok = False

    bo_chay_ok = False
    try:
        bo_chay = lay_bo_chay(cau_hinh)
        await asyncio.wait_for(bo_chay.liet_ke_model(), timeout=2.0)
        bo_chay_ok = True
    except Exception as err:  # noqa: BLE001
        logger.warning("Kiểm tra bộ chạy local thất bại tại /ready: %s", err)
        bo_chay_ok = False

    dam_may_ok = any(t.kha_dung for t in cau_hinh.chuoi_dam_may)

    thanh_phan = {
        "db": "ok" if csdl_ok else "hong",
        "bo_chay": "ok" if bo_chay_ok else "hong",
        "dam_may": "ok" if dam_may_ok else "hong",
    }

    san_sang = csdl_ok and (bo_chay_ok or dam_may_ok)

    return JSONResponse(
        status_code=200 if san_sang else 503,
        content={
            "trang_thai": "san_sang" if san_sang else "chua_san_sang",
            "phien_ban": PHIEN_BAN,
            "thanh_phan": thanh_phan,
        },
    )


# ---------------------------------------------------------------------------
# Endpoint xác thực và quản lý phiên (/api/v1/)
# ---------------------------------------------------------------------------


@app.post("/api/v1/dang-nhap", response_model=PhanHoiDangNhap)
async def dang_nhap(
    yeu_cau: YeuCauDangNhap,
    request: Request,
    response: Response,
) -> PhanHoiDangNhap:
    """Đăng nhập bằng địa chỉ email và mật khẩu, phát JWT 15 phút và refresh token 8 giờ."""
    ma_yc = lay_ma_yeu_cau()
    # 0. Kiểm tra hạn mức IP (Lớp a) trước tiên, không chạm DB người dùng nếu đã bị chặn
    await kiem_tra_han_muc_ip(lay_ip_yeu_cau(request), ma_yc)

    email_chuan = chuan_hoa_email(yeu_cau.email)

    if not kiem_tra_dinh_dang_email(email_chuan):
        raise LoiUngDung(
            ma="CHUA_XAC_THUC",
            thong_diep="Email hoặc mật khẩu không chính xác.",
            http=401,
            ma_yeu_cau=ma_yc,
        )

    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == email_chuan)
        nd = (await phien.scalars(cau_lenh)).first()

        if (
            nd is None
            or not nd.dang_hoat_dong
            or not xac_minh_mat_khau(yeu_cau.mat_khau, nd.mat_khau_bam)
        ):
            raise LoiUngDung(
                ma="CHUA_XAC_THUC",
                thong_diep="Email hoặc mật khẩu không chính xác.",
                http=401,
                ma_yeu_cau=ma_yc,
            )

        cs_dl = nap_cau_hinh_chinh_sach()
        che_do = (
            CheDoDinhTuyen.CHI_LOCAL
            if nd.phong_ban in cs_dl.phong_ban_chi_local
            else None
        )
        che_do_str = che_do.value if che_do else None

        nguoi_obj = NguoiDung(
            id=nd.id,
            email=nd.email,
            ho_ten=nd.ho_ten,
            vai_tro=nd.vai_tro,
            bac=nd.bac or "free",
            phong_ban=nd.phong_ban,
            che_do_dinh_tuyen=che_do,
        )
        access_token = tao_access_token(nguoi_obj)
        token_tho, token_bam, het_han_luc = tao_refresh_token()

        # Lưu refresh token băm vào bảng phien_dang_nhap
        phien_moi = PhienDangNhapModel(
            nguoi_id=nd.id,
            refresh_token_bam=token_bam,
            het_han_luc=het_han_luc,
            thu_hoi=False,
        )
        phien.add(phien_moi)

        # Ghi nhật ký kiểm toán
        kiem_toan = NhatKyKiemToanModel(
            nguoi_id=nd.id,
            hanh_dong="dang_nhap",
            chi_tiet={"email": nd.email},
            ma_yeu_cau=ma_yc,
        )
        phien.add(kiem_toan)

    # Đặt cookie HttpOnly cho refresh token 8 giờ
    is_prod = cau_hinh.moi_truong == "prod"
    response.set_cookie(
        key="refresh_token",
        value=token_tho,
        httponly=True,
        max_age=8 * 3600,
        expires=8 * 3600,
        path="/api/v1",
        samesite="lax",
        secure=is_prod,
    )

    return PhanHoiDangNhap(
        access_token=access_token,
        token_type="bearer",
        expires_in=900,
        nguoi_dung=ThongTinNguoiDungPhanHoi(
            id=nd.id,
            email=nd.email,
            ho_ten=nd.ho_ten,
            vai_tro=nd.vai_tro,
            bac=nd.bac or "free",
            phong_ban=nd.phong_ban,
            che_do_dinh_tuyen=che_do_str,
        ),
    )


@app.post("/api/v1/lam-moi-token", response_model=PhanHoiLamMoiToken)
async def lam_moi_token(request: Request) -> PhanHoiLamMoiToken:
    """Làm mới access token 15 phút từ refresh token trong cookie HttpOnly."""
    ma_yc = lay_ma_yeu_cau()
    token_tho = request.cookies.get("refresh_token")
    if not token_tho:
        raise LoiUngDung(
            ma="CHUA_XAC_THUC",
            thong_diep="Thiếu refresh token trong yêu cầu.",
            http=401,
            ma_yeu_cau=ma_yc,
        )

    token_bam = bam_refresh_token(token_tho)
    bay_gio = datetime.now(timezone.utc)

    maker = lay_sessionmaker_async()
    async with maker() as phien:
        cau_lenh = select(PhienDangNhapModel).where(
            PhienDangNhapModel.refresh_token_bam == token_bam,
            PhienDangNhapModel.thu_hoi.is_(False),
            PhienDangNhapModel.het_han_luc > bay_gio,
        )
        phien_dn = (await phien.scalars(cau_lenh)).first()

        if phien_dn is None:
            raise LoiUngDung(
                ma="CHUA_XAC_THUC",
                thong_diep="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
                http=401,
                ma_yeu_cau=ma_yc,
            )

        cau_lenh_nd = select(NguoiDungModel).where(NguoiDungModel.id == phien_dn.nguoi_id)
        nd = (await phien.scalars(cau_lenh_nd)).first()

        if nd is None or not nd.dang_hoat_dong:
            raise LoiUngDung(
                ma="CHUA_XAC_THUC",
                thong_diep="Tài khoản không tồn tại hoặc đã bị khóa.",
                http=401,
                ma_yeu_cau=ma_yc,
            )

        cs_dl = nap_cau_hinh_chinh_sach()
        che_do = (
            CheDoDinhTuyen.CHI_LOCAL
            if nd.phong_ban in cs_dl.phong_ban_chi_local
            else None
        )

        nguoi_obj = NguoiDung(
            id=nd.id,
            email=nd.email,
            ho_ten=nd.ho_ten,
            vai_tro=nd.vai_tro,
            bac=nd.bac or "free",
            phong_ban=nd.phong_ban,
            che_do_dinh_tuyen=che_do,
        )
        access_token_moi = tao_access_token(nguoi_obj)

    return PhanHoiLamMoiToken(
        access_token=access_token_moi,
        token_type="bearer",
        expires_in=900,
    )


@app.post("/api/v1/dang-xuat", response_model=PhanHoiDangXuat)
async def dang_xuat(
    request: Request,
    response: Response,
) -> PhanHoiDangXuat:
    """Đăng xuất, thu hồi phiên làm việc trong CSDL và xóa cookie refresh token."""
    ma_yc = lay_ma_yeu_cau()
    token_tho = request.cookies.get("refresh_token")

    if token_tho:
        token_bam = bam_refresh_token(token_tho)
        maker = lay_sessionmaker_async()
        async with maker() as phien, phien.begin():
            cau_lenh = select(PhienDangNhapModel).where(
                PhienDangNhapModel.refresh_token_bam == token_bam,
                PhienDangNhapModel.thu_hoi.is_(False),
            )
            phien_dn = (await phien.scalars(cau_lenh)).first()
            if phien_dn is not None:
                phien_dn.thu_hoi = True
                kiem_toan = NhatKyKiemToanModel(
                    nguoi_id=phien_dn.nguoi_id,
                    hanh_dong="dang_xuat",
                    chi_tiet={},
                    ma_yeu_cau=ma_yc,
                )
                phien.add(kiem_toan)

    response.delete_cookie(key="refresh_token", path="/api/v1")
    return PhanHoiDangXuat(thanh_cong=True, thong_diep="Đã đăng xuất thành công.")


@app.get("/api/v1/toi", response_model=ThongTinNguoiDungPhanHoi)
async def lay_thong_tin_toi(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> ThongTinNguoiDungPhanHoi:
    """Lấy thông tin hồ sơ của người dùng hiện tại kèm số liệu hạn mức."""
    che_do_str = (
        nguoi.che_do_dinh_tuyen.value
        if isinstance(nguoi.che_do_dinh_tuyen, CheDoDinhTuyen)
        else str(nguoi.che_do_dinh_tuyen)
        if nguoi.che_do_dinh_tuyen
        else None
    )
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        da_dung_gio, token_hom_nay, chi_phi_usd, han_muc_con, dang_chay = (
            await lay_thong_tin_han_muc_nguoi_dung(nguoi.id, nguoi.bac, phien)
        )

    return ThongTinNguoiDungPhanHoi(
        id=nguoi.id,
        email=nguoi.email,
        ho_ten=nguoi.ho_ten,
        vai_tro=nguoi.vai_tro,
        bac=nguoi.bac,
        phong_ban=nguoi.phong_ban,
        che_do_dinh_tuyen=che_do_str,
        da_dung_trong_gio=da_dung_gio,
        token_da_sinh_hom_nay=token_hom_nay,
        chi_phi_hom_nay_usd=chi_phi_usd,
        han_muc_con_lai=han_muc_con,
        dang_chay=dang_chay,
    )


# ---------------------------------------------------------------------------
# Endpoint nghiệp vụ trò chuyện (/api/v1/chat)
# ---------------------------------------------------------------------------


@app.post("/api/v1/chat/stream")
async def chat_stream(
    yeu_cau: YeuCauChatStream,
    request: Request,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> StreamingResponse:
    """Endpoint phát phản hồi hội thoại theo dòng (SSE) qua chuỗi định tuyến lai."""
    ma_yc = lay_ma_yeu_cau()

    ghi_nhat_ky_chang(
        chang="http_vao",
        thong_diep=f"Tiếp nhận yêu cầu HTTP chat stream (độ dài: {len(yeu_cau.noi_dung)})",
        ma_yeu_cau=ma_yc,
        nguoi_id=nguoi.id,
        phong_ban=nguoi.phong_ban,
        hoi_thoai_id=yeu_cau.hoi_thoai_id,
    )

    if nguoi.vai_tro == "chi_doc":
        raise LoiUngDung(
            ma="KHONG_CO_QUYEN",
            thong_diep="Tài khoản chỉ đọc không có quyền gửi tin nhắn mới.",
            http=403,
            ma_yeu_cau=ma_yc,
        )

    # Kiểm tra tuần tự 4 lớp hạn mức (chi phí thấp -> cao) và chiếm khe lớp d
    await kiem_tra_toan_bo_han_muc_chat(request, nguoi, ma_yc)
    ghi_nhat_ky_chang(
        chang="kiem_tra_han_muc",
        thong_diep="Kiểm tra hạn mức stream thành công",
        ma_yeu_cau=ma_yc,
        nguoi_id=nguoi.id,
        phong_ban=nguoi.phong_ban,
        hoi_thoai_id=yeu_cau.hoi_thoai_id,
    )

    async def _giai_phong_khe() -> None:
        await giai_phong_khe_yeu_cau(nguoi.id)

    try:
        luong = tao_luong_su_kien(yeu_cau, request, nguoi, on_finish=_giai_phong_khe)
        return StreamingResponse(
            luong,
            media_type="text/event-stream",
            headers=HEADER_SSE,
        )
    except Exception:
        await giai_phong_khe_yeu_cau(nguoi.id)
        raise


async def _chuan_bi_hoi_thoai_dong_bo(
    yeu_cau_id: int | None,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
) -> tuple[int, list[dict[str, str]], bool]:
    """Khởi tạo hoặc tải lịch sử hội thoại chuẩn bị cho lượt chat không phát dòng."""
    maker = lay_sessionmaker_async()
    async with maker() as phien_doc:
        if cau_hinh.xac_thuc_gia:
            nd = await phien_doc.get(NguoiDungModel, nguoi.id)
            if nd is None:
                phien_doc.add(
                    NguoiDungModel(
                        id=nguoi.id,
                        email=f"can_bo_{nguoi.id}@vidu.com",
                        ho_ten="Cán bộ kiểm thử",
                        vai_tro="nguoi_dung",
                        bac="free",
                        phong_ban="CNTT",
                        dang_hoat_dong=True,
                    )
                )
                await phien_doc.flush()

        if yeu_cau_id is None:
            ht = await tao_hoi_thoai(phien_doc, nguoi_id=nguoi.id)
            await phien_doc.commit()
            return ht.id, [], True

        # Không tồn tại, đã xoá hoặc thuộc người khác đều trả cùng một lỗi
        ht = await lay_hoi_thoai(phien_doc, yeu_cau_id, nguoi_id=nguoi.id)
        if ht is None:
            raise LoiUngDung(
                ma="KHONG_TIM_THAY",
                thong_diep="Không tìm thấy cuộc hội thoại.",
                http=404,
                ma_yeu_cau=ma_yeu_cau,
            )

        cac_luot = await lay_danh_sach_luot(phien_doc, ht.id)
        lich_su = [
            {
                "role": (
                    "user"
                    if l.vai_tro == "nguoi_dung"
                    else ("assistant" if l.vai_tro == "tro_ly" else "system")
                ),
                "content": l.noi_dung,
            }
            for l in cac_luot
        ]
        return ht.id, lich_su, len(cac_luot) == 0


@app.post("/api/v1/chat", response_model=PhanHoiChat)
async def chat_dong_bo(
    yeu_cau: YeuCauChat,
    request: Request,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiChat:
    """Endpoint xử lý hội thoại không phát theo dòng cho tích hợp máy với máy."""
    ma_yc = lay_ma_yeu_cau()

    ghi_nhat_ky_chang(
        chang="http_vao",
        thong_diep=f"Tiếp nhận yêu cầu HTTP chat (độ dài: {len(yeu_cau.noi_dung)})",
        ma_yeu_cau=ma_yc,
        nguoi_id=nguoi.id,
        phong_ban=nguoi.phong_ban,
        hoi_thoai_id=yeu_cau.hoi_thoai_id,
    )

    if nguoi.vai_tro == "chi_doc":
        raise LoiUngDung(
            ma="KHONG_CO_QUYEN",
            thong_diep="Tài khoản chỉ đọc không có quyền gửi tin nhắn mới.",
            http=403,
            ma_yeu_cau=ma_yc,
        )

    # Kiểm tra tuần tự 4 lớp hạn mức (chi phí thấp -> cao) và chiếm khe lớp d
    await kiem_tra_toan_bo_han_muc_chat(request, nguoi, ma_yc)
    ghi_nhat_ky_chang(
        chang="kiem_tra_han_muc",
        thong_diep="Kiểm tra hạn mức thành công",
        ma_yeu_cau=ma_yc,
        nguoi_id=nguoi.id,
        phong_ban=nguoi.phong_ban,
        hoi_thoai_id=yeu_cau.hoi_thoai_id,
    )

    try:
        # 1. Móc kiểm duyệt đầu vào (gọi trước khi dựng ngữ cảnh)
        kd_vao = await kiem_duyet_dau_vao(yeu_cau.noi_dung, nguoi)
        if not kd_vao.cho_qua:
            raise LoiUngDung(
                ma="NOI_DUNG_BI_CHAN",
                thong_diep=kd_vao.ly_do or "Nội dung vi phạm chính sách kiểm duyệt.",
                http=422,
                ma_yeu_cau=ma_yc,
            )
        noi_dung_goc = kd_vao.noi_dung_thay_the or yeu_cau.noi_dung

        # 2. Truy vấn hội thoại và lịch sử
        ht_id, lich_su, la_luot_dau = await _chuan_bi_hoi_thoai_dong_bo(
            yeu_cau.hoi_thoai_id, nguoi, ma_yc
        )

        # 3. Gắn nhãn trên bản gốc, rồi che dữ liệu cá nhân: model, CSDL và nhật ký chỉ
        # nhận bản đã che; giá trị thật chỉ được khôi phục trong phản hồi cho người hỏi
        nhan = nhan_cua_hoi_thoai(lich_su=lich_su, tin_nhan_moi=noi_dung_goc)
        kq_che = che_du_lieu_ca_nhan(
            noi_dung_goc,
            so_bat_dau=dem_the_da_dung(tin["content"] for tin in lich_su),
        )
        noi_dung_nguoi_dung = kq_che.van_ban_da_che
        che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cau_hinh.che_do_dinh_tuyen
        kq_chuoi = xac_dinh_chuoi(nguoi, nhan, che_do=che_do, cau_hinh_he_thong=cau_hinh)
        ghi_nhat_ky_chang(
            chang="xac_dinh_chuoi",
            thong_diep=f"Xác định chuỗi định tuyến (nhãn: {nhan.value})",
            ma_yeu_cau=ma_yc,
            nguoi_id=nguoi.id,
            phong_ban=nguoi.phong_ban,
            hoi_thoai_id=ht_id,
            nhan_du_lieu=nhan.value,
        )

        kq_ngu_canh = dung_ngu_canh(
            lich_su, noi_dung_nguoi_dung, kq_chuoi.chuoi, ma_yeu_cau=ma_yc
        )
        ghi_nhat_ky_chang(
            chang="dung_ngu_canh",
            thong_diep="Dựng ngữ cảnh hội thoại",
            ma_yeu_cau=ma_yc,
            nguoi_id=nguoi.id,
            phong_ban=nguoi.phong_ban,
            hoi_thoai_id=ht_id,
            da_cat_ngu_canh=kq_ngu_canh.da_cat,
            nhan_du_lieu=nhan.value,
        )

        # 4. Thực thi gọi mô hình qua router duy nhất
        kq_goi: KetQuaGoi = await goi_mo_hinh(
            kq_ngu_canh.danh_sach,
            nguoi=nguoi,
            ma_yeu_cau=ma_yc,
            nhan_du_lieu=nhan,
            da_cat_ngu_canh=kq_ngu_canh.da_cat,
            so_luot_bi_cat=kq_ngu_canh.so_luot_bi_cat,
        )
        ghi_nhat_ky_chang(
            chang="goi_mo_hinh",
            thong_diep=f"Gọi mô hình hoàn thành: {kq_goi.ten_model}",
            ma_yeu_cau=ma_yc,
            nguoi_id=nguoi.id,
            phong_ban=nguoi.phong_ban,
            hoi_thoai_id=ht_id,
            nguon=str(kq_goi.nguon),
            tang=kq_goi.tang,
            bac_local=kq_goi.bac_local,
            model=kq_goi.ten_model,
            token_vao=kq_goi.token_vao,
            token_ra=kq_goi.token_ra,
            chi_phi_usd=kq_goi.chi_phi_usd,
            toc_do_tok_s=kq_goi.toc_do_tok_s,
            thoi_gian_nap_ms=kq_goi.thoi_gian_nap_ms,
            do_dai_hang_doi=getattr(kq_goi, "do_dai_hang_doi", 0),
            do_tre_ms=kq_goi.do_tre_ms,
            da_cat_ngu_canh=kq_goi.da_cat_ngu_canh,
            nhan_du_lieu=nhan.value,
            danh_sach_tang_da_hong=kq_goi.danh_sach_tang_da_hong,
        )

        # 5. Móc kiểm duyệt đầu ra (gọi trên toàn văn trước khi lưu CSDL)
        kd_ra = await kiem_duyet_dau_ra(kq_goi.noi_dung, nguoi)
        if not kd_ra.cho_qua:
            raise LoiUngDung(
                ma="NOI_DUNG_BI_CHAN",
                thong_diep=kd_ra.ly_do or "Nội dung vi phạm chính sách kiểm duyệt.",
                http=422,
                ma_yeu_cau=ma_yc,
            )
        noi_dung_tro_ly = (
            kd_ra.noi_dung_thay_the
            if kd_ra.noi_dung_thay_the is not None
            else kq_goi.noi_dung
        )

        # 6. Lưu cả lượt người dùng và lượt trợ lý trong MỘT giao dịch duy nhất
        maker = lay_sessionmaker_async()
        async with maker() as phien_luu, phien_luu.begin():
            await luu_cap_luot_hoi_thoai(
                phien_luu,
                hoi_thoai_id=ht_id,
                noi_dung_nguoi=noi_dung_nguoi_dung,
                noi_dung_tro_ly=noi_dung_tro_ly,
                kq_goi=kq_goi,
                ma_yeu_cau=ma_yc,
                nhan_du_lieu=nhan.value,
                phien_ban_prompt=doc_phien_ban_loi_nhac(),
            )
        ghi_nhat_ky_chang(
            chang="luu_hoi_thoai",
            thong_diep="Lưu cặp lượt hội thoại vào cơ sở dữ liệu thành công",
            ma_yeu_cau=ma_yc,
            nguoi_id=nguoi.id,
            phong_ban=nguoi.phong_ban,
            hoi_thoai_id=ht_id,
            nguon=str(kq_goi.nguon),
            tang=kq_goi.tang,
            bac_local=kq_goi.bac_local,
            model=kq_goi.ten_model,
            token_vao=kq_goi.token_vao,
            token_ra=kq_goi.token_ra,
            chi_phi_usd=kq_goi.chi_phi_usd,
            toc_do_tok_s=kq_goi.toc_do_tok_s,
            thoi_gian_nap_ms=kq_goi.thoi_gian_nap_ms,
            do_dai_hang_doi=getattr(kq_goi, "do_dai_hang_doi", 0),
            do_tre_ms=kq_goi.do_tre_ms,
            da_cat_ngu_canh=kq_goi.da_cat_ngu_canh,
            nhan_du_lieu=nhan.value,
            danh_sach_tang_da_hong=kq_goi.danh_sach_tang_da_hong,
        )

        # 7. Tự động sinh tiêu đề chạy nền sau lượt đầu tiên
        if la_luot_dau:
            asyncio.create_task(
                tu_dat_tieu_de(
                    hoi_thoai_id=ht_id,
                    noi_dung_nguoi=noi_dung_nguoi_dung,
                    noi_dung_tro_ly=noi_dung_tro_ly,
                    nguoi=nguoi,
                )
            )

        ghi_nhat_ky_chang(
            chang="http_ra",
            thong_diep="Hoàn tất và phản hồi yêu cầu HTTP",
            ma_yeu_cau=ma_yc,
            nguoi_id=nguoi.id,
            phong_ban=nguoi.phong_ban,
            hoi_thoai_id=ht_id,
            nguon=str(kq_goi.nguon),
            tang=kq_goi.tang,
            bac_local=kq_goi.bac_local,
            model=kq_goi.ten_model,
            token_vao=kq_goi.token_vao,
            token_ra=kq_goi.token_ra,
            chi_phi_usd=kq_goi.chi_phi_usd,
            toc_do_tok_s=kq_goi.toc_do_tok_s,
            thoi_gian_nap_ms=kq_goi.thoi_gian_nap_ms,
            do_dai_hang_doi=getattr(kq_goi, "do_dai_hang_doi", 0),
            do_tre_ms=kq_goi.do_tre_ms,
            da_cat_ngu_canh=kq_goi.da_cat_ngu_canh,
            nhan_du_lieu=nhan.value,
            danh_sach_tang_da_hong=kq_goi.danh_sach_tang_da_hong,
        )

        return PhanHoiChat(
            hoi_thoai_id=ht_id,
            noi_dung=kq_che.restore(noi_dung_tro_ly),
            nguon=str(kq_goi.nguon),
            tang=kq_goi.tang,
            bac_local=kq_goi.bac_local,
            model=kq_goi.ten_model,
            token_vao=kq_goi.token_vao,
            token_ra=kq_goi.token_ra,
            chi_phi_usd=kq_goi.chi_phi_usd,
            do_tre_ms=kq_goi.do_tre_ms,
            toc_do_tok_s=kq_goi.toc_do_tok_s,
            nhan_ai=tao_nhan_ai(kq_goi.ten_model),
            ma_yeu_cau=ma_yc,
            ha_cap=kq_goi.ha_cap,
        )
    finally:
        await giai_phong_khe_yeu_cau(nguoi.id)


# ---------------------------------------------------------------------------
# Endpoint quản lý hội thoại (/api/v1/hoi-thoai)
# ---------------------------------------------------------------------------


@app.get("/api/v1/hoi-thoai", response_model=DanhSachHoiThoai)
async def danh_sach_hoi_thoai_nguoi_dung(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
    trang: Annotated[int, Query(ge=1)] = 1,
    kich_thuoc: Annotated[int, Query(ge=1, le=100)] = 20,
    tu_khoa: Annotated[str | None, Query(max_length=200)] = None,
    tu_ngay: date | None = None,
    den_ngay: date | None = None,
    sap_xep: SapXepHoiThoai = SapXepHoiThoai.MOI_NHAT,
) -> DanhSachHoiThoai:
    """Lấy danh sách hội thoại của người dùng hiện tại theo bộ lọc, có phân trang.

    tong_so là số hội thoại khớp bộ lọc; ngày tính theo giờ Việt Nam.
    """
    if tu_ngay is not None and den_ngay is not None and tu_ngay > den_ngay:
        raise LoiUngDung(
            ma="DAU_VAO_KHONG_HOP_LE",
            thong_diep="Từ ngày phải trước hoặc bằng Đến ngày.",
            http=422,
            ma_yeu_cau=lay_ma_yeu_cau(),
        )
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        danh_sach, tong_so = await lay_danh_sach_hoi_thoai(
            phien,
            nguoi.id,
            trang=trang,
            kich_thuoc=kich_thuoc,
            tu_khoa=tu_khoa,
            tu_ngay=tu_ngay,
            den_ngay=den_ngay,
            sap_xep=sap_xep,
        )
        so_luot = await dem_so_luot_hoi(phien, [ht.id for ht in danh_sach])
        items = [
            ItemHoiThoai(
                id=ht.id,
                tieu_de=ht.tieu_de,
                tao_luc=ht.tao_luc,
                cap_nhat_luc=ht.cap_nhat_luc,
                so_luot=so_luot.get(ht.id, 0),
            )
            for ht in danh_sach
        ]
        return DanhSachHoiThoai(
            danh_sach=items, tong_so=tong_so, trang=trang, kich_thuoc=kich_thuoc
        )


@app.get("/api/v1/hoi-thoai/{hoi_thoai_id}", response_model=ChiTietHoiThoai)
async def xem_chi_tiet_hoi_thoai(
    hoi_thoai_id: int,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> ChiTietHoiThoai:
    """Lấy chi tiết toàn bộ các lượt trao đổi trong một cuộc hội thoại."""
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        ht = await lay_hoi_thoai(phien, hoi_thoai_id, nguoi_id=nguoi.id)
        if ht is None:
            raise LoiUngDung(
                ma="KHONG_TIM_THAY",
                thong_diep="Không tìm thấy cuộc hội thoại.",
                http=404,
                ma_yeu_cau=lay_ma_yeu_cau(),
            )

        cac_luot = await lay_danh_sach_luot(phien, ht.id)
        roi_tang = await lay_ma_yeu_cau_roi_tang(
            phien, [l.ma_yeu_cau for l in cac_luot if l.vai_tro == "tro_ly" and l.ma_yeu_cau]
        )
        items = [
            ItemLuot(
                id=l.id,
                vai_tro=l.vai_tro,
                noi_dung=l.noi_dung,
                nguon=l.nguon,
                tang=l.tang,
                bac_local=l.bac_local,
                model_da_dung=l.model_da_dung,
                token_vao=l.token_vao,
                token_ra=l.token_ra,
                chi_phi_usd=l.chi_phi_usd,
                toc_do_tok_s=l.toc_do_tok_s,
                do_tre_ms=l.do_tre_ms,
                da_cat_ngu_canh=l.da_cat_ngu_canh,
                so_luot_bi_cat=l.so_luot_bi_cat,
                ma_yeu_cau=l.ma_yeu_cau,
                nhan_ai=(
                    tao_nhan_ai(l.model_da_dung, l.tao_luc)
                    if l.vai_tro == "tro_ly" and l.model_da_dung
                    else None
                ),
                ha_cap=l.vai_tro == "tro_ly"
                and (l.bac_local == "nho" or l.ma_yeu_cau in roi_tang),
                tao_luc=l.tao_luc,
            )
            for l in cac_luot
        ]
        return ChiTietHoiThoai(
            id=ht.id,
            tieu_de=ht.tieu_de,
            tao_luc=ht.tao_luc,
            cap_nhat_luc=ht.cap_nhat_luc,
            cac_luot=items,
        )


@app.delete("/api/v1/hoi-thoai/{hoi_thoai_id}", response_model=PhanHoiXoaHoiThoai)
async def xoa_cuoc_hoi_thoai(
    hoi_thoai_id: int,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiXoaHoiThoai:
    """Xóa mềm cuộc hội thoại của người dùng hiện tại."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        thanh_cong = await xoa_mem_hoi_thoai(phien, hoi_thoai_id, nguoi_id=nguoi.id)
        if not thanh_cong:
            raise LoiUngDung(
                ma="KHONG_TIM_THAY",
                thong_diep="Không tìm thấy cuộc hội thoại.",
                http=404,
                ma_yeu_cau=lay_ma_yeu_cau(),
            )
        return PhanHoiXoaHoiThoai(
            thanh_cong=True,
            thong_diep="Đã xoá cuộc hội thoại.",
        )


# ---------------------------------------------------------------------------
# Endpoint thông tin hệ thống và chỉ số vận hành
# ---------------------------------------------------------------------------


@app.get("/api/v1/chi-phi")
async def lay_bao_cao_chi_phi(
    _: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> dict[str, Any]:
    """Lấy báo cáo chi phí, tỷ lệ định tuyến và số câu hỏi trong ngày (giờ Việt Nam)."""
    bao_cao = bao_cao_chi_phi()
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        bao_cao.update(await dem_cau_hoi_hom_nay(phien))
    return bao_cao


@app.get("/api/v1/chi-so")
async def lay_chi_so_van_hanh(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
    gio: Annotated[int, Query(ge=1, le=720)] = 24,
) -> dict[str, Any]:
    """Tổng hợp 6 nhóm chỉ số vận hành (tốc độ, nạp model, hàng đợi, rơi tầng) cho vai trò quan_tri."""
    ma_yc = lay_ma_yeu_cau()
    if nguoi.vai_tro != "quan_tri":
        raise LoiUngDung(
            ma="KHONG_CO_QUYEN",
            thong_diep="Chỉ quản trị viên mới có quyền xem chỉ số vận hành.",
            http=403,
            ma_yeu_cau=ma_yc,
        )

    maker = lay_sessionmaker_async()
    async with maker() as phien:
        return await tong_hop_chi_so_van_hanh(phien, so_gio=gio)


@app.get("/api/v1/models", response_model=ThongTinModels)
async def lay_thong_tin_mo_hinh(
    _: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> ThongTinModels:
    """Trả về chế độ định tuyến, hồ sơ GPU, 2 bậc local và 4 tầng đám mây (không kèm khoá API)."""
    danh_sach_dam_may = [
        ThongTinTangDamMay(
            tang=t.tang,
            ten=t.ten,
            model=t.model,
            gia_vao_usd_moi_trieu=t.gia_vao_usd_moi_trieu,
            gia_ra_usd_moi_trieu=t.gia_ra_usd_moi_trieu,
            cua_so_ngu_canh=t.cua_so_ngu_canh,
            kha_dung=t.kha_dung,
        )
        for t in cau_hinh.chuoi_dam_may
    ]

    return ThongTinModels(
        che_do_dinh_tuyen=cau_hinh.che_do_dinh_tuyen,
        ho_so_gpu=cau_hinh.ho_so_gpu_dang_chon,
        bac_local=cau_hinh.bac_local,
        chuoi_dam_may=danh_sach_dam_may,
    )


@app.get("/api/v1/hang-doi/tinh-trang", response_model=TrangThaiHangDoi)
async def lay_tinh_trang_hang_doi(
    _: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> TrangThaiHangDoi:
    """Ảnh chụp trạng thái vận hành của bộ điều phối hàng đợi local."""
    return dieu_phoi_mac_dinh.trang_thai()


@app.get("/api/v1/ngu-canh/tinh-trang", response_model=TinhTrangNguCanh)
async def lay_tinh_trang_ngu_canh(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> TinhTrangNguCanh:
    """Trả về num_ctx cấu hình và thực tế theo bậc, ngân sách token và số lượt trung bình giữ được."""
    kq_chuoi = xac_dinh_chuoi(
        nguoi, NhanDuLieu.THUONG, che_do=cau_hinh.che_do_dinh_tuyen
    )
    ngan_sach = tinh_ngan_sach_token(kq_chuoi.chuoi, cau_hinh)
    so_luot = uoc_luong_so_luot_giu_duoc(kq_chuoi.chuoi, cau_hinh)

    bo_chay = lay_bo_chay(cau_hinh)
    ds_bac_ngu_canh: list[ThongTinBacNguCanh] = []

    for b in cau_hinh.bac_local:
        ctx_thuc_te: int | None = None
        try:
            ctx_thuc_te = await bo_chay.doc_ngu_canh_thuc_te(b.model)
        except Exception as err:  # noqa: BLE001
            logger.debug("Không đọc được ngữ cảnh thực tế của %s: %s", b.model, err)

        ds_bac_ngu_canh.append(
            ThongTinBacNguCanh(
                bac=b.bac,
                model=b.model,
                num_ctx_cau_hinh=b.num_ctx,
                num_ctx_thuc_te=ctx_thuc_te,
            )
        )

    return TinhTrangNguCanh(
        bac_local=ds_bac_ngu_canh,
        ngan_sach_token=ngan_sach,
        so_luot_trung_binh_giu_duoc=so_luot,
    )


# ---------------------------------------------------------------------------
# Endpoint tài liệu hướng dẫn sử dụng và câu hỏi thường gặp
# ---------------------------------------------------------------------------


@app.get("/api/v1/huong-dan", response_model=PhanHoiHuongDanSuDung)
async def lay_huong_dan_su_dung(
    _: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiHuongDanSuDung:
    """Trả về tài liệu hướng dẫn sử dụng định dạng Markdown cho cán bộ nhân viên."""
    du_lieu = lay_huong_dan_su_dung_api()
    return PhanHoiHuongDanSuDung(**du_lieu)


@app.get("/api/v1/cau-hoi-thuong-gap", response_model=PhanHoiCauHoiThuongGap)
async def lay_cau_hoi_thuong_gap(
    _: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiCauHoiThuongGap:
    """Trả về danh sách 20 mục câu hỏi thường gặp thuộc 5 nhóm chuẩn nghiệp vụ."""
    du_lieu = lay_cau_hoi_thuong_gap_api()
    return PhanHoiCauHoiThuongGap(**du_lieu)

