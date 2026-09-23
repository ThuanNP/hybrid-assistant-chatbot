"""Định dạng và xử lý sự kiện phát dòng Server-Sent Events (SSE).

Mô-đun quản lý các mô hình dữ liệu sự kiện SSE, định dạng chuỗi sự kiện
tuân thủ chuẩn text/event-stream, điều phối tác vụ phát dòng, quản lý ngữ cảnh
từ cơ sở dữ liệu và lưu vết các lượt hội thoại.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from pydantic import BaseModel, Field

from app.chat.hoi_thoai import (
    doc_phien_ban_loi_nhac,
    lay_danh_sach_luot,
    lay_hoi_thoai,
    luu_cap_luot_hoi_thoai,
    tao_hoi_thoai,
    tu_dat_tieu_de,
)
from app.chat.ngu_canh import dung_ngu_canh
from app.config import cau_hinh
from app.core.bao_mat import kiem_duyet_dau_ra, kiem_duyet_dau_vao
from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
from app.core.loi import (
    LOI_DONG,
    THONG_DIEP_LOI,
    LoiUngDung,
    chuyen_doi_loi_sang_loi_ung_dung,
)
from app.core.nhat_ky import lay_ma_yeu_cau
from app.core.thoi_gian import MUI_GIO_VN
from app.core.xac_thuc import NguoiDung
from app.llm.chinh_sach import nhan_cua_hoi_thoai, xac_dinh_chuoi
from app.llm.router import KetQuaGoi, ManhPhatRa, goi_mo_hinh_theo_dong

logger = logging.getLogger(__name__)


class YeuCauChatStream(BaseModel):
    """Dữ liệu yêu cầu gửi tới endpoint phát dòng chat SSE."""

    hoi_thoai_id: int | None = None
    noi_dung: str = Field(min_length=1)


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
    ma_yeu_cau: str = ""
    # True khi tầng phục vụ khác tầng đầu của chuỗi thực tế hoặc do bậc nho trả lời
    ha_cap: bool = False


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

    Tuân thủ quy tắc kỹ thuật 12 trong AGENTS.md: Trần tự chủ L2,
    chỉ gắn nhãn nhận diện mô hình và thời điểm sinh, không có trường hợp lệ.
    """
    moc_thoi_gian = (thoi_diem or datetime.now(timezone.utc)).astimezone(MUI_GIO_VN)
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
                ma_yeu_cau=ma_yeu_cau,
                ha_cap=kq.ha_cap if kq else False,
            ),
        )

    noi_dung_loi = manh.noi_dung or phan_da_nhan
    return dong_goi_su_kien(
        "loi",
        SuKienLoi(
            ma=LOI_DONG,
            thong_diep=THONG_DIEP_LOI[LOI_DONG],
            ma_yeu_cau=ma_yeu_cau,
            phan_da_nhan=noi_dung_loi,
        ),
    )


def _tao_su_kien_loi_ngoai_le(
    muc: Exception, ma_yeu_cau: str, phan_da_nhan: str
) -> str:
    """Tạo sự kiện lỗi SSE từ ngoại lệ hệ thống hoặc lỗi nghiệp vụ đã chuẩn hóa."""
    loi_ud = chuyen_doi_loi_sang_loi_ung_dung(muc, ma_yeu_cau)
    return dong_goi_su_kien(
        "loi",
        SuKienLoi(
            ma=loi_ud.ma,
            thong_diep=loi_ud.thong_diep,
            ma_yeu_cau=ma_yeu_cau,
            phan_da_nhan=phan_da_nhan,
        ),
    )


async def _tien_trinh_san_xuat(
    hang_doi: asyncio.Queue[ManhPhatRa | Exception | None],
    yeu_cau: YeuCauChatStream,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
    hoi_thoai_id_hop: list[int | None],
) -> None:
    """Tác vụ nền thực hiện chuỗi xác định chính sách, ngữ cảnh và gọi mô hình theo dòng."""
    hoi_thoai_id: int | None = None
    noi_dung_tro_ly = ""
    noi_dung_nguoi_dung = yeu_cau.noi_dung
    maker = lay_sessionmaker_async()
    nhan_du_lieu_str: str | None = None
    kq_hoan_thanh: KetQuaGoi | None = None
    da_luu_db = False
    # Nội dung đã bị móc kiểm duyệt từ chối thì không được lưu, kể cả ở nhánh lỗi
    bi_chan = False

    try:
        # 0. Móc kiểm duyệt đầu vào, gọi trước khi tạo hội thoại và dựng ngữ cảnh
        kd_dau_vao = await kiem_duyet_dau_vao(yeu_cau.noi_dung, nguoi)
        if not kd_dau_vao.cho_qua:
            bi_chan = True
            raise LoiUngDung(
                ma="NOI_DUNG_BI_CHAN",
                thong_diep=kd_dau_vao.ly_do
                or "Nội dung vi phạm chính sách kiểm duyệt.",
                http=422,
                ma_yeu_cau=ma_yeu_cau,
            )
        if kd_dau_vao.noi_dung_thay_the is not None:
            noi_dung_nguoi_dung = kd_dau_vao.noi_dung_thay_the

        # 1. Mở hội thoại của chính người dùng (hoặc tạo mới) và đọc lịch sử theo thời gian
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

            if yeu_cau.hoi_thoai_id is None:
                ht = await tao_hoi_thoai(phien_doc, nguoi_id=nguoi.id)
                await phien_doc.commit()
                hoi_thoai_id = ht.id
                hoi_thoai_id_hop[0] = hoi_thoai_id
                la_luot_dau = True
                lich_su_tin_nhan: list[dict[str, str]] = []
            else:
                # Hội thoại không tồn tại, đã xoá hoặc thuộc người khác đều trả cùng một lỗi
                ht = await lay_hoi_thoai(phien_doc, yeu_cau.hoi_thoai_id, nguoi_id=nguoi.id)
                if ht is None:
                    raise LoiUngDung(
                        ma="KHONG_TIM_THAY",
                        thong_diep="Không tìm thấy cuộc hội thoại.",
                        http=404,
                        ma_yeu_cau=ma_yeu_cau,
                    )
                hoi_thoai_id = ht.id
                hoi_thoai_id_hop[0] = hoi_thoai_id
                cac_luot = await lay_danh_sach_luot(phien_doc, hoi_thoai_id)
                la_luot_dau = len(cac_luot) == 0
                lich_su_tin_nhan = []
                for luot in cac_luot:
                    if luot.vai_tro == "nguoi_dung":
                        vai_tro_role = "user"
                    elif luot.vai_tro == "tro_ly":
                        vai_tro_role = "assistant"
                    else:
                        vai_tro_role = "system"
                    lich_su_tin_nhan.append({"role": vai_tro_role, "content": luot.noi_dung})

        # 2. Xác định nhãn dữ liệu, chuỗi định tuyến và dựng ngữ cảnh
        nhan = nhan_cua_hoi_thoai(
            lich_su=lich_su_tin_nhan, tin_nhan_moi=noi_dung_nguoi_dung
        )
        nhan_du_lieu_str = nhan.value
        che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cau_hinh.che_do_dinh_tuyen
        kq_chuoi = xac_dinh_chuoi(
            nguoi, nhan, che_do=che_do, cau_hinh_he_thong=cau_hinh
        )
        kq_ngu_canh = dung_ngu_canh(
            lich_su_tin_nhan,
            noi_dung_nguoi_dung,
            kq_chuoi.chuoi,
            ma_yeu_cau=ma_yeu_cau,
        )

        # 3. Phát phản hồi theo dòng và gom nội dung trợ lý
        kq_hoan_thanh: KetQuaGoi | None = None
        async for manh in goi_mo_hinh_theo_dong(
            kq_ngu_canh.danh_sach,
            nguoi=nguoi,
            ma_yeu_cau=ma_yeu_cau,
            nhan_du_lieu=nhan,
            da_cat_ngu_canh=kq_ngu_canh.da_cat,
            so_luot_bi_cat=kq_ngu_canh.so_luot_bi_cat,
        ):
            if manh.loai == "manh":
                noi_dung_tro_ly += manh.noi_dung
            elif manh.loai == "xong":
                kq_hoan_thanh = manh.ket_qua
            await hang_doi.put(manh)

        # 3b. Móc kiểm duyệt đầu ra trên toàn văn trước khi lưu CSDL
        kd_dau_ra = await kiem_duyet_dau_ra(noi_dung_tro_ly, nguoi)
        if not kd_dau_ra.cho_qua:
            bi_chan = True
            raise LoiUngDung(
                ma="NOI_DUNG_BI_CHAN",
                thong_diep=kd_dau_ra.ly_do or "Nội dung vi phạm chính sách kiểm duyệt.",
                http=422,
                ma_yeu_cau=ma_yeu_cau,
            )
        if kd_dau_ra.noi_dung_thay_the is not None:
            noi_dung_tro_ly = kd_dau_ra.noi_dung_thay_the

        # 4. Lưu cả lượt người dùng và lượt trả lời trong MỘT giao dịch duy nhất
        phien_ban_prompt = doc_phien_ban_loi_nhac()
        da_luu_db = False
        if hoi_thoai_id is not None:

            async def _luu_db() -> None:
                async with maker() as phien_luu, phien_luu.begin():
                    await luu_cap_luot_hoi_thoai(
                        phien_luu,
                        hoi_thoai_id=hoi_thoai_id,
                        noi_dung_nguoi=noi_dung_nguoi_dung,
                        noi_dung_tro_ly=noi_dung_tro_ly,
                        kq_goi=kq_hoan_thanh,
                        ma_yeu_cau=ma_yeu_cau,
                        nhan_du_lieu=nhan.value,
                        phien_ban_prompt=phien_ban_prompt,
                    )

            await asyncio.shield(_luu_db())
            da_luu_db = True

        # 5. Tự đặt tiêu đề chạy nền sau lượt trả lời ĐẦU TIÊN
        if la_luot_dau and hoi_thoai_id is not None:
            asyncio.create_task(
                tu_dat_tieu_de(
                    hoi_thoai_id=hoi_thoai_id,
                    noi_dung_nguoi=noi_dung_nguoi_dung,
                    noi_dung_tro_ly=noi_dung_tro_ly,
                    nguoi=nguoi,
                )
            )

        await hang_doi.put(None)
    except asyncio.CancelledError:
        logger.info(
            "[%s] Tiến trình phát dòng bị huỷ, kiểm tra lưu CSDL...", ma_yeu_cau
        )
        if hoi_thoai_id is not None and not da_luu_db:
            try:
                pb_prompt = doc_phien_ban_loi_nhac()

                async def _luu_khi_huy() -> None:
                    async with maker() as phien_huy, phien_huy.begin():
                        await luu_cap_luot_hoi_thoai(
                            phien_huy,
                            hoi_thoai_id=hoi_thoai_id,
                            noi_dung_nguoi=noi_dung_nguoi_dung,
                            noi_dung_tro_ly=noi_dung_tro_ly,
                            kq_goi=kq_hoan_thanh,
                            ma_yeu_cau=ma_yeu_cau,
                            nhan_du_lieu=nhan_du_lieu_str,
                            phien_ban_prompt=pb_prompt,
                        )

                await asyncio.shield(_luu_khi_huy())
            except Exception as e_huy:  # noqa: BLE001
                logger.error(
                    "[%s] Không thể lưu lượt dở dang khi bị huỷ: %s",
                    ma_yeu_cau,
                    e_huy,
                )
        raise
    except Exception as err:  # noqa: BLE001
        logger.warning(
            "[%s] ket_thuc_do_loi: Tiến trình phát dòng gián đoạn: %s",
            ma_yeu_cau,
            err,
        )
        if hoi_thoai_id is not None and not da_luu_db and not bi_chan:
            try:
                pb_prompt = doc_phien_ban_loi_nhac()
                async with maker() as phien_loi, phien_loi.begin():
                    await luu_cap_luot_hoi_thoai(
                        phien_loi,
                        hoi_thoai_id=hoi_thoai_id,
                        noi_dung_nguoi=noi_dung_nguoi_dung,
                        noi_dung_tro_ly=noi_dung_tro_ly,
                        kq_goi=None,
                        ma_yeu_cau=ma_yeu_cau,
                        nhan_du_lieu=nhan_du_lieu_str,
                        phien_ban_prompt=pb_prompt,
                    )
            except Exception as e_luu:  # noqa: BLE001
                logger.error(
                    "[%s] Không thể lưu lượt dở dang khi bị lỗi: %s",
                    ma_yeu_cau,
                    e_luu,
                )
        await hang_doi.put(err)


async def tao_luong_su_kien(
    yeu_cau: YeuCauChatStream,
    request: Request,
    nguoi: NguoiDung,
) -> AsyncIterator[str]:
    """Khởi tạo và kiểm soát luồng sự kiện SSE trả về cho người dùng."""
    ma_yeu_cau = lay_ma_yeu_cau()
    phan_da_nhan = ""
    dang_trong_hang_doi = False
    hoi_thoai_id_hop: list[int | None] = [yeu_cau.hoi_thoai_id]
    hang_doi: asyncio.Queue[ManhPhatRa | Exception | None] = asyncio.Queue()
    tac_vu = asyncio.create_task(
        _tien_trinh_san_xuat(hang_doi, yeu_cau, nguoi, ma_yeu_cau, hoi_thoai_id_hop)
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

            yield _tao_su_kien_tu_manh(
                muc, hoi_thoai_id_hop[0], phan_da_nhan, ma_yeu_cau
            )

            if muc.loai == "loi":
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
            except Exception as err:  # noqa: BLE001
                logger.debug("[%s] Lỗi huỷ tác vụ: %s", ma_yeu_cau, err)
