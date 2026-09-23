"""Điểm nhập chính khởi chạy ứng dụng FastAPI và hệ thống định tuyến API."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import tomllib
from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.chat.hoi_thoai import (
    doc_phien_ban_loi_nhac,
    lay_danh_sach_hoi_thoai,
    lay_danh_sach_luot,
    lay_hoi_thoai,
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
from app.config import CauHinhBacLocal, cau_hinh
from app.core.bao_mat import kiem_duyet_dau_ra, kiem_duyet_dau_vao
from app.core.csdl import (
    HoiThoaiModel,
    NguoiDungModel,
    lay_sessionmaker_async,
)
from app.core.loi import (
    LoiUngDung,
    dang_ky_bo_bat_loi,
)
from app.core.nhat_ky import (
    dat_ma_yeu_cau,
    lay_ma_yeu_cau,
    sinh_ma_yeu_cau,
)
from app.core.xac_thuc import (
    NguoiDung,
    khoi_tao_nguoi_dung_gia_dev,
    kiem_tra_an_toan_xac_thuc,
    lay_nguoi_dung_hien_tai,
)
from app.hang_doi.dieu_phoi import TrangThaiHangDoi, dieu_phoi_mac_dinh
from app.llm.bo_chay_local import kiem_tra_khi_khoi_dong, lay_bo_chay
from app.llm.chi_phi import bao_cao_chi_phi
from app.llm.chinh_sach import NhanDuLieu, nhan_cua_hoi_thoai, xac_dinh_chuoi
from app.llm.router import KetQuaGoi, goi_mo_hinh

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
    await khoi_tao_nguoi_dung_gia_dev()
    tac_vu = asyncio.create_task(kiem_tra_khi_khoi_dong())
    tac_vu.add_done_callback(_ghi_loi_tac_vu_nen)
    yield
    tac_vu.cancel()


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

# Đăng ký bộ bắt lỗi toàn cục chuẩn hóa định dạng lỗi
dang_ky_bo_bat_loi(app)

# Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cau_hinh.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def middleware_ma_yeu_cau(request: Request, call_next: Any) -> Response:
    """Middleware gắn mã yêu cầu ma_yeu_cau 12 ký tự xuyên suốt mỗi chu trình HTTP."""
    ma_yc = request.headers.get("X-Ma-Yeu-Cau")
    if not ma_yc or not ma_yc.strip():
        ma_yc = sinh_ma_yeu_cau()
    else:
        ma_yc = ma_yc.strip()[:50]

    dat_ma_yeu_cau(ma_yc)
    phan_hoi: Response = await call_next(request)
    phan_hoi.headers["X-Ma-Yeu-Cau"] = ma_yc
    return phan_hoi


# ---------------------------------------------------------------------------
# Lược đồ Pydantic cho các API nghiệp vụ
# ---------------------------------------------------------------------------


class YeuCauChat(BaseModel):
    """Dữ liệu yêu cầu cho endpoint chat không phát dòng."""

    hoi_thoai_id: int | None = None
    noi_dung: str = Field(min_length=1, description="Nội dung câu hỏi của người dùng")


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


class ItemHoiThoai(BaseModel):
    """Thông tin tóm tắt một cuộc hội thoại trong danh sách."""

    id: int
    tieu_de: str
    tao_luc: datetime
    cap_nhat_luc: datetime


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
# Endpoint nghiệp vụ trò chuyện (/api/v1/chat)
# ---------------------------------------------------------------------------


@app.post("/api/v1/chat/stream")
async def chat_stream(
    yeu_cau: YeuCauChatStream,
    request: Request,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> StreamingResponse:
    """Endpoint phát phản hồi hội thoại theo dòng (SSE) qua chuỗi định tuyến lai."""
    return StreamingResponse(
        tao_luong_su_kien(yeu_cau, request, nguoi),
        media_type="text/event-stream",
        headers=HEADER_SSE,
    )


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
                        ten_dang_nhap=f"can_bo_{nguoi.id}",
                        ho_ten="Cán bộ kiểm thử",
                        vai_tro="nguoi_dung",
                        bac="chinh",
                        phong_ban="CNTT",
                        dang_hoat_dong=True,
                    )
                )
                await phien_doc.flush()

        if yeu_cau_id is None:
            ht = await tao_hoi_thoai(phien_doc, nguoi_id=nguoi.id)
            await phien_doc.commit()
            return ht.id, [], True

        ht = await lay_hoi_thoai(phien_doc, yeu_cau_id)
        if ht is None:
            if cau_hinh.xac_thuc_gia:
                ht = HoiThoaiModel(
                    id=yeu_cau_id,
                    nguoi_id=nguoi.id,
                    tieu_de="Cuộc trò chuyện mới",
                    da_xoa=False,
                )
                phien_doc.add(ht)
                await phien_doc.commit()
                return ht.id, [], True
            raise LoiUngDung(
                ma="KHONG_TIM_THAY",
                thong_diep="Không tìm thấy cuộc hội thoại.",
                http=404,
                ma_yeu_cau=ma_yeu_cau,
            )

        if ht.nguoi_id != nguoi.id:
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
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> PhanHoiChat:
    """Endpoint xử lý hội thoại không phát theo dòng cho tích hợp máy với máy."""
    ma_yc = lay_ma_yeu_cau()

    # 1. Móc kiểm duyệt đầu vào (gọi trước khi dựng ngữ cảnh)
    kd_vao = await kiem_duyet_dau_vao(yeu_cau.noi_dung, nguoi)
    if not kd_vao.cho_qua:
        raise LoiUngDung(
            ma="NOI_DUNG_BI_CHAN",
            thong_diep=kd_vao.ly_do or "Nội dung vi phạm chính sách kiểm duyệt.",
            http=422,
            ma_yeu_cau=ma_yc,
        )
    noi_dung_nguoi_dung = kd_vao.noi_dung_thay_the or yeu_cau.noi_dung

    # 2. Truy vấn hội thoại và lịch sử
    ht_id, lich_su, la_luot_dau = await _chuan_bi_hoi_thoai_dong_bo(
        yeu_cau.hoi_thoai_id, nguoi, ma_yc
    )

    # 3. Xác định nhãn dữ liệu, chuỗi định tuyến và dựng ngữ cảnh
    nhan = nhan_cua_hoi_thoai(lich_su=lich_su, tin_nhan_moi=noi_dung_nguoi_dung)
    che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cau_hinh.che_do_dinh_tuyen
    kq_chuoi = xac_dinh_chuoi(nguoi, nhan, che_do=che_do, cau_hinh_he_thong=cau_hinh)
    kq_ngu_canh = dung_ngu_canh(
        lich_su, noi_dung_nguoi_dung, kq_chuoi.chuoi, ma_yeu_cau=ma_yc
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

    return PhanHoiChat(
        hoi_thoai_id=ht_id,
        noi_dung=noi_dung_tro_ly,
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
    )


# ---------------------------------------------------------------------------
# Endpoint quản lý hội thoại (/api/v1/hoi-thoai)
# ---------------------------------------------------------------------------


@app.get("/api/v1/hoi-thoai", response_model=DanhSachHoiThoai)
async def danh_sach_hoi_thoai_nguoi_dung(
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
    trang: Annotated[int, Query(ge=1)] = 1,
    kich_thuoc: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DanhSachHoiThoai:
    """Lấy danh sách các cuộc hội thoại của người dùng hiện tại, có phân trang."""
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        danh_sach, tong_so = await lay_danh_sach_hoi_thoai(
            phien, nguoi.id, trang=trang, kich_thuoc=kich_thuoc
        )
        items = [
            ItemHoiThoai(
                id=ht.id,
                tieu_de=ht.tieu_de,
                tao_luc=ht.tao_luc,
                cap_nhat_luc=ht.cap_nhat_luc,
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
    """Lấy báo cáo tổng hợp chi phí và tỷ lệ định tuyến sử dụng mô hình."""
    return dict(bao_cao_chi_phi())


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
