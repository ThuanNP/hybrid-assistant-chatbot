"""Mô-đun tạo vector nhúng cho câu hỏi và các đoạn tài liệu RAG.

QUY TẮC MỘT MODEL NHÚNG CHO MỖI CHỈ MỤC:
Tài liệu gốc từng đề xuất để lời gọi nhúng rơi từ Gemini sang OpenAI khi tầng 1 lỗi.
KHÔNG làm như vậy: hai model nhúng khác nhau sinh hai không gian vector khác nhau
(thường khác cả số chiều); câu hỏi nhúng bằng model B khi so với đoạn nhúng bằng
model A cho điểm cosine vô nghĩa, truy hồi sai mà không có dấu hiệu nhận biết.
Vì vậy:
- goi_nhung KHÔNG có chuỗi rơi tầng sang nhà cung cấp khác.
- Mỗi tai_lieu lưu model_nhung; truy hồi chỉ so với đoạn có cùng model_nhung với câu hỏi.
- Đổi model nhúng = nạp lại TOÀN BỘ kho bằng scripts/nap_tai_lieu.py --nhung-lai, có thanh tiến độ.
- Model nhúng lỗi -> đặt cờ che_do_truy_hoi = "chi_tu_khoa" và lùi về BM25
  (suy giảm có kiểm soát mức 2 của Module 2).

LỰA CHỌN MẶC ĐỊNH CHẠY LOCAL CHO NHÚNG:
Nhúng mặc định chạy LOCAL (bge-m3 qua Ollama) bất kể CHE_DO_DINH_TUYEN,
vì nội dung tài liệu nội bộ không được rời hạ tầng.
"""

import logging
import uuid
from collections.abc import Iterator
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import DoanModel, TaiLieuModel, lay_sessionmaker_async
from app.llm.router import _doc_cau_hinh_rag, goi_nhung

logger = logging.getLogger(__name__)

__all__ = [
    "KetQuaNhungCauHoi",
    "dat_lai_tat_ca_vector",
    "nhung_cau_hoi",
    "nhung_doan_chua_co_vector",
]


class KetQuaNhungCauHoi(BaseModel):
    """Kết quả nhúng một câu hỏi phục vụ truy hồi."""

    vector: list[float] | None = None
    che_do_truy_hoi: str = "lai"  # "lai" khi thành công, "chi_tu_khoa" khi lỗi
    model_nhung: str = ""
    do_tre_ms: float = 0.0

    def __iter__(self) -> Iterator[Any]:  # type: ignore[override]
        """Hỗ trợ unpack trực tiếp: vector, che_do = await nhung_cau_hoi(...)."""
        return iter((self.vector, self.che_do_truy_hoi))


async def nhung_cau_hoi(
    cau_hoi: str,
    *,
    ma_yeu_cau: str = "",
    **tuy_chon: Any,
) -> KetQuaNhungCauHoi:
    """Tạo vector nhúng cho câu hỏi tra cứu.

    Nếu model nhúng bị lỗi: ghi nhật ký cảnh báo và tự động chuyển
    che_do_truy_hoi = 'chi_tu_khoa' để hệ thống lùi về BM25 (suy giảm mức 2).
    Nếu số chiều vector trả về khác cấu hình (config/rag.yaml): từ chối và lùi về chi_tu_khoa.
    """
    ma_yc = ma_yeu_cau or f"nhung_ch_{uuid.uuid4().hex[:8]}"
    rag_cfg = _doc_cau_hinh_rag()
    so_chieu_mong_doi = int(rag_cfg.get("so_chieu", 1024))
    model_logic = str(rag_cfg.get("model_nhung", "bge-m3"))

    try:
        kq = await goi_nhung([cau_hoi], ma_yeu_cau=ma_yc, **tuy_chon)
        if kq.so_chieu != so_chieu_mong_doi:
            raise ValueError(
                f"Số chiều vector ({kq.so_chieu}) không khớp cấu hình ({so_chieu_mong_doi})"
            )
        vector = kq.vectors[0] if kq.vectors else None
        return KetQuaNhungCauHoi(
            vector=vector,
            che_do_truy_hoi="lai",
            model_nhung=model_logic,
            do_tre_ms=kq.do_tre_ms,
        )
    except Exception as err:
        logger.warning(
            "[%s] Lỗi khi tạo vector nhúng cho câu hỏi: %s. "
            "Kích hoạt suy giảm mức 2: lùi về truy hồi chỉ từ khóa (chi_tu_khoa).",
            ma_yc,
            err,
        )
        return KetQuaNhungCauHoi(
            vector=None,
            che_do_truy_hoi="chi_tu_khoa",
            model_nhung=model_logic,
            do_tre_ms=0.0,
        )


async def dat_lai_tat_ca_vector(session: AsyncSession | None = None) -> int:
    """Đặt lại toàn bộ vector = NULL trong bảng doan khi chạy --nhung-lai.

    Đồng thời cập nhật model_nhung của toàn bộ tài liệu về giá trị cấu hình hiện hành.
    """
    rag_cfg = _doc_cau_hinh_rag()
    model_logic = str(rag_cfg.get("model_nhung", "bge-m3"))

    async def _xu_ly(s: AsyncSession) -> int:
        kq_doan = await s.execute(update(DoanModel).values(vector=None))
        await s.execute(update(TaiLieuModel).values(model_nhung=model_logic))
        return int(getattr(kq_doan, "rowcount", 0) or 0)

    if session is not None:
        return await _xu_ly(session)

    factory = lay_sessionmaker_async()
    async with factory() as phien, phien.begin():
        return await _xu_ly(phien)


async def nhung_doan_chua_co_vector(
    session: AsyncSession | None = None,
    *,
    ma_yeu_cau: str = "nap_nhung_doan",
    tien_do: bool = False,
    kich_thuoc_lo: int | None = None,
    **tuy_chon: Any,
) -> int:
    """Tạo vector nhúng cho toàn bộ các đoạn tài liệu có vector đang NULL.

    Chia lô (mặc định 32 đoạn), kiểm tra số chiều khớp 1024 trước khi ghi vào CSDL.
    Hiển thị thanh tiến độ (tqdm) nếu tien_do=True.
    """
    rag_cfg = _doc_cau_hinh_rag()
    so_chieu_mong_doi = int(rag_cfg.get("so_chieu", 1024))
    lo_size = int(kich_thuoc_lo or rag_cfg.get("kich_thuoc_lo", 32))

    async def _xu_ly_phien(s: AsyncSession) -> int:
        cau_lenh = (
            select(DoanModel)
            .where(DoanModel.vector.is_(None))
            .order_by(DoanModel.id)
        )
        doan_list = list((await s.scalars(cau_lenh)).all())
        tong_so = len(doan_list)
        if tong_so == 0:
            return 0

        pbar = None
        if tien_do:
            try:
                from tqdm import tqdm
                pbar = tqdm(total=tong_so, desc="Nhúng vector đoạn tài liệu", unit="đoạn")
            except ImportError:
                pbar = None

        so_da_nhung = 0
        for i in range(0, tong_so, lo_size):
            nhom = doan_list[i : i + lo_size]
            cac_van_ban = [d.noi_dung for d in nhom]
            ma_yc_lo = f"{ma_yeu_cau}_{i // lo_size + 1}"

            kq = await goi_nhung(cac_van_ban, ma_yeu_cau=ma_yc_lo, **tuy_chon)
            if kq.so_chieu != so_chieu_mong_doi:
                raise ValueError(
                    f"Số chiều vector ({kq.so_chieu}) không khớp cấu hình ({so_chieu_mong_doi}). "
                    "Từ chối ghi vào cơ sở dữ liệu."
                )

            for d, vec in zip(nhom, kq.vectors):
                d.vector = vec

            await s.flush()
            so_da_nhung += len(nhom)
            if pbar:
                pbar.update(len(nhom))

        if pbar:
            pbar.close()

        return so_da_nhung

    if session is not None:
        return await _xu_ly_phien(session)

    factory = lay_sessionmaker_async()
    async with factory() as phien, phien.begin():
        return await _xu_ly_phien(phien)
