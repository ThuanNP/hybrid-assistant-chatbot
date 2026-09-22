"""Định dạng và xử lý sự kiện phát dòng Server-Sent Events (SSE).

Mô-đun quản lý các mô hình dữ liệu sự kiện SSE, định dạng chuỗi sự kiện
tuân thủ chuẩn text/event-stream, điều phối tác vụ phát dòng và giám sát
kết nối của máy khách để giải phóng tài nguyên kịp thời.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from app.chat.ngu_canh import dung_ngu_canh
from app.config import cau_hinh
from app.core.xac_thuc import NguoiDung
from app.llm.chinh_sach import nhan_cua_hoi_thoai, xac_dinh_chuoi
from app.llm.router import ManhPhatRa, goi_mo_hinh_theo_dong

logger = logging.getLogger(__name__)


class YeuCauChatStream(BaseModel):
    """Dữ liệu yêu cầu gửi tới endpoint phát dòng chat SSE."""

    hoi_thoai_id: int | None = None
    noi_dung: str


class SuKienHangDoi(BaseModel):
    """Sự kiện thông báo yêu cầu đang trong hàng đợi xử lý cục bộ."""

    vi_tri: int
    uoc_luong_giay: float | None = None


class SuKienBatDau(BaseModel):
    """Sự kiện đánh dấu bắt đầu luồng phát từ tầng mô hình phục vụ."""

    hoi_thoai_id: int | None = None
    nguon: str
    tang: int
    model: str
    da_cat_ngu_canh: bool = False
    so_luot_bi_cat: int = 0


class SuKienManh(BaseModel):
    """Sự kiện chứa từng mẩu văn bản được sinh ra từ mô hình."""

    noi_dung: str


class SuKienXong(BaseModel):
    """Sự kiện kết thúc luồng phát kèm theo đầy đủ siêu dữ liệu kỹ thuật."""

    token_vao: int = 0
    token_ra: int = 0
    chi_phi_usd: float = 0.0
    toc_do_tok_s: float = 0.0
    do_tre_ms: float = 0.0
    nguon: str
    tang: int
    bac_local: str | None = None
    model: str
    nhan_ai: str


class SuKienLoi(BaseModel):
    """Sự kiện thông báo lỗi phát sinh kèm phần dữ liệu đã nhận trước đó."""

    ma: str
    thong_diep: str
    ma_yeu_cau: str
    phan_da_nhan: str = ""


def sinh_ma_yeu_cau() -> str:
    """Sinh chuỗi định danh duy nhất gồm 12 ký tự cho mỗi yêu cầu."""
    return uuid.uuid4().hex[:12]


def tao_nhan_ai(model: str, thoi_diem: datetime | None = None) -> str:
    """Tạo nhãn nguồn gốc câu trả lời hiển thị trên giao diện người dùng.

    Tuân thủ quy tắc kỹ thuật 8 trong AGENTS.md: Trần tự chủ L2,
    chỉ gắn nhãn nhận diện mô hình và thời điểm sinh, không có trường hợp lệ.
    """
    moc_thoi_gian = thoi_diem or datetime.now(timezone.utc).astimezone()
    chuoi_thoi_gian = moc_thoi_gian.strftime("%d/%m/%Y - %H:%M")
    return f"Nội dung do AI tạo - {model} - {chuoi_thoi_gian}"


def dong_goi_su_kien(ten: str, du_lieu: dict[str, Any] | BaseModel) -> str:
    """Đóng gói tên sự kiện và dữ liệu thành dòng SSE chuẩn.

    Giữ nguyên các ký tự tiếng Việt có dấu qua cấu hình ensure_ascii=False.
    """
    if isinstance(du_lieu, BaseModel):
        du_lieu_dict = du_lieu.model_dump()
    else:
        du_lieu_dict = du_lieu

    chuoi_json = json.dumps(du_lieu_dict, ensure_ascii=False)
    return f"event: {ten}\ndata: {chuoi_json}\n\n"


def _tao_su_kien_tu_manh(
    manh: ManhPhatRa,
    hoi_thoai_id: int | None,
    phan_da_nhan: str,
    ma_yeu_cau: str,
) -> str:
    """Chuyển đổi một ManhPhatRa từ router thành dòng sự kiện SSE chuẩn."""
    if manh.loai == "hang_doi":
        return dong_goi_su_kien(
            "hang_doi",
            SuKienHangDoi(vi_tri=manh.vi_tri or 1, uoc_luong_giay=manh.uoc_luong_giay),
        )
    if manh.loai == "bat_dau":
        return dong_goi_su_kien(
            "bat_dau",
            SuKienBatDau(
                hoi_thoai_id=hoi_thoai_id,
                nguon=str(manh.nguon),
                tang=manh.tang or 0,
                model=str(manh.ten_model),
                da_cat_ngu_canh=manh.da_cat_ngu_canh,
                so_luot_bi_cat=manh.so_luot_bi_cat,
            ),
        )
    if manh.loai == "manh":
        return dong_goi_su_kien("manh", SuKienManh(noi_dung=manh.noi_dung))
    if manh.loai == "xong":
        kq = manh.ket_qua
        ten_model = kq.ten_model if kq else (manh.ten_model or "khong_ro")
        return dong_goi_su_kien(
            "xong",
            SuKienXong(
                token_vao=kq.token_vao if kq else 0,
                token_ra=kq.token_ra if kq else 0,
                chi_phi_usd=kq.chi_phi_usd if kq else 0.0,
                toc_do_tok_s=kq.toc_do_tok_s if kq else 0.0,
                do_tre_ms=kq.do_tre_ms if kq else 0.0,
                nguon=kq.nguon if kq else (manh.nguon or "local"),
                tang=kq.tang if kq else (manh.tang or 0),
                bac_local=kq.bac_local if kq else manh.bac_local,
                model=ten_model,
                nhan_ai=tao_nhan_ai(ten_model),
            ),
        )

    noi_dung_loi = manh.noi_dung or phan_da_nhan
    return dong_goi_su_kien(
        "loi",
        SuKienLoi(
            ma="LOI_DONG",
            thong_diep="Quá trình sinh phản hồi bị gián đoạn",
            ma_yeu_cau=ma_yeu_cau,
            phan_da_nhan=noi_dung_loi,
        ),
    )


def _tao_su_kien_loi_ngoai_le(muc: Exception, ma_yeu_cau: str, phan_da_nhan: str) -> str:
    """Tạo sự kiện lỗi SSE từ ngoại lệ hệ thống hoặc lỗi nghiệp vụ."""
    ma_loi = getattr(muc, "ma_loi", muc.__class__.__name__)
    thong_diep = getattr(muc, "thong_diep", str(muc))
    return dong_goi_su_kien(
        "loi",
        SuKienLoi(
            ma=ma_loi,
            thong_diep=thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            phan_da_nhan=phan_da_nhan,
        ),
    )


async def _tien_trinh_san_xuat(
    hang_doi: asyncio.Queue[ManhPhatRa | Exception | None],
    yeu_cau: YeuCauChatStream,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
) -> None:
    """Tác vụ nền thực hiện chuỗi xác định chính sách, ngữ cảnh và gọi mô hình theo dòng."""
    try:
        nhan = nhan_cua_hoi_thoai(lich_su=[], tin_nhan_moi=yeu_cau.noi_dung)
        che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cau_hinh.che_do_dinh_tuyen
        kq_chuoi = xac_dinh_chuoi(nguoi, nhan, che_do=che_do, cau_hinh_he_thong=cau_hinh)
        kq_ngu_canh = dung_ngu_canh(
            [],
            yeu_cau.noi_dung,
            kq_chuoi.chuoi,
            ma_yeu_cau=ma_yeu_cau,
        )
        async for manh in goi_mo_hinh_theo_dong(
            kq_ngu_canh.danh_sach,
            nguoi=nguoi,
            ma_yeu_cau=ma_yeu_cau,
            nhan_du_lieu=nhan,
            da_cat_ngu_canh=kq_ngu_canh.da_cat,
            so_luot_bi_cat=kq_ngu_canh.so_luot_bi_cat,
        ):
            await hang_doi.put(manh)
        await hang_doi.put(None)
    except asyncio.CancelledError:
        raise
    except Exception as err:  # noqa: BLE001 - Bắt mọi ngoại lệ để đóng gói sự kiện lỗi SSE
        logger.warning("[%s] Lỗi trong tiến trình phát dòng: %s", ma_yeu_cau, err)
        await hang_doi.put(err)


async def tao_luong_su_kien(
    yeu_cau: YeuCauChatStream,
    request: Request,
    nguoi: NguoiDung,
) -> AsyncIterator[str]:
    """Khởi tạo và kiểm soát luồng sự kiện SSE trả về cho người dùng."""
    ma_yeu_cau = sinh_ma_yeu_cau()
    phan_da_nhan = ""
    dang_trong_hang_doi = False
    hang_doi: asyncio.Queue[ManhPhatRa | Exception | None] = asyncio.Queue()
    tac_vu = asyncio.create_task(
        _tien_trinh_san_xuat(hang_doi, yeu_cau, nguoi, ma_yeu_cau)
    )

    try:
        while True:
            if await request.is_disconnected():
                logger.info("[%s] nguoi_dung_huy", ma_yeu_cau)
                break

            try:
                muc = await asyncio.wait_for(hang_doi.get(), timeout=15.0)
            except asyncio.TimeoutError:
                if dang_trong_hang_doi:
                    yield ": ping\n\n"
                continue

            if muc is None:
                break

            if isinstance(muc, Exception):
                yield _tao_su_kien_loi_ngoai_le(muc, ma_yeu_cau, phan_da_nhan)
                break

            if muc.loai == "hang_doi":
                dang_trong_hang_doi = True
            elif muc.loai in ("bat_dau", "manh"):
                dang_trong_hang_doi = False
                if muc.loai == "manh":
                    phan_da_nhan += muc.noi_dung

            yield _tao_su_kien_tu_manh(muc, yeu_cau.hoi_thoai_id, phan_da_nhan, ma_yeu_cau)

            if muc.loai in ("xong", "loi"):
                break

    except asyncio.CancelledError:
        logger.info("[%s] nguoi_dung_huy", ma_yeu_cau)
        raise
    finally:
        if not tac_vu.done():
            tac_vu.cancel()
            try:
                await tac_vu
            except asyncio.CancelledError:
                pass
            except Exception as err:  # noqa: BLE001 - Ghi nhật ký gỡ lỗi nếu có sự cố khi huỷ
                logger.debug("[%s] Lỗi huỷ tác vụ: %s", ma_yeu_cau, err)
