"""Mô-đun kiểm tra và nạp tài liệu vào kho tri thức RAG.

Tuân thủ:
- Quy tắc tuyệt đối 1, 4 trong AGENTS.md.
- Quy chuẩn clean_code.md, naming.md, type_safety.md.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import DoanModel, TaiLieuModel, lay_sessionmaker_async
from app.rag.cat_doan import cat_doan

logger = logging.getLogger(__name__)

# Ký tự có dấu tiếng Việt phục vụ kiểm tra bảng mã
KY_TU_CO_DAU = set(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
)

DINH_DANG_HO_TRO = {".pdf", ".docx", ".html", ".htm", ".md"}

CAC_TRUONG_BAT_BUOC_META = [
    "ma_tai_lieu",
    "tieu_de",
    "loai_van_ban",
    "tinh_trang",
    "pham_vi_doc",
    "ngay_ban_hanh",
    "don_vi_quan_ly",
]


@dataclass
class KetQuaNap:
    """Kết quả xử lý nạp một tệp tài liệu."""

    ten_tep: str
    so_doan: int
    trang_thai: str  # "ĐÃ NẠP" | "BỎ QUA" | "TỪ CHỐI"
    ly_do: str | None = None


def doc_cau_hinh_rag() -> dict[str, Any]:
    """Đọc cấu hình RAG từ tệp config/rag.yaml."""
    duong_dan_goc = Path(__file__).resolve().parent.parent.parent.parent
    tep_cau_hinh = duong_dan_goc / "config" / "rag.yaml"
    if not tep_cau_hinh.exists():
        tep_cau_hinh = Path("/srv/config/rag.yaml")

    if not tep_cau_hinh.exists():
        return {
            "model_nhung": "bge-m3",
            "ky_tu_toi_thieu_moi_trang": 200,
            "ty_le_tu_co_dau_toi_thieu": 0.5,
            "token_doan_toi_da": 500,
        }

    with open(tep_cau_hinh, "r", encoding="utf-8") as f:
        du_lieu = yaml.safe_load(f) or {}
    return {
        "model_nhung": str(du_lieu.get("model_nhung", "bge-m3")),
        "ky_tu_toi_thieu_moi_trang": int(du_lieu.get("ky_tu_toi_thieu_moi_trang", 200)),
        "ty_le_tu_co_dau_toi_thieu": float(du_lieu.get("ty_le_tu_co_dau_toi_thieu", 0.5)),
        "token_doan_toi_da": int(du_lieu.get("token_doan_toi_da", 500)),
    }


def tinh_ty_le_tu_co_dau(van_ban: str) -> float:
    """Tính tỷ lệ các từ có ít nhất một ký tự mang dấu tiếng Việt."""
    cac_tu = re.findall(r"\b\w+\b", van_ban)
    cac_tu_chu = [t for t in cac_tu if any(c.isalpha() for c in t)]
    if not cac_tu_chu:
        return 0.0
    so_tu_co_dau = sum(1 for t in cac_tu_chu if any(c in KY_TU_CO_DAU for c in t))
    return so_tu_co_dau / len(cac_tu_chu)


def kiem_tra_dinh_dang(duong_dan_tep: Path) -> bool:
    """Kiểm tra phần mở rộng tệp có thuộc danh sách hỗ trợ hay không."""
    return duong_dan_tep.suffix.lower() in DINH_DANG_HO_TRO


def kiem_tra_sieu_du_lieu(
    duong_dan_tep: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    """Kiểm tra tệp siêu dữ liệu .meta.yaml đi kèm và xác thực các trường bắt buộc."""
    tep_meta = duong_dan_tep.parent / f"{duong_dan_tep.stem}.meta.yaml"
    if not tep_meta.exists():
        tep_meta = duong_dan_tep.with_suffix(".meta.yaml")
    if not tep_meta.exists():
        return None, "thiếu siêu dữ liệu"

    try:
        with open(tep_meta, "r", encoding="utf-8") as f:
            du_lieu = yaml.safe_load(f)
    except (yaml.YAMLError, OSError, ValueError):
        return None, "thiếu siêu dữ liệu: tệp YAML không hợp lệ"

    if not isinstance(du_lieu, dict):
        return None, "thiếu siêu dữ liệu: nội dung YAML rỗng hoặc sai cấu trúc"

    for truong in CAC_TRUONG_BAT_BUOC_META:
        if truong not in du_lieu or du_lieu[truong] is None or du_lieu[truong] == "":
            return None, f"thiếu siêu dữ liệu: {truong}"

    if du_lieu.get("tinh_trang") == "het_hieu_luc" and not du_lieu.get("van_ban_thay_the"):
        return None, "thiếu siêu dữ liệu: van_ban_thay_the"

    return du_lieu, None


def _doc_tep_docling(duong_dan_tep: Path) -> tuple[str, int]:
    """Đọc tệp PDF, DOCX, HTML bằng Docling khi chạy trong môi trường container."""
    try:
        from docling.datamodel.base_models import InputFormat  # pyright: ignore[reportMissingImports]
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # pyright: ignore[reportMissingImports]
        from docling.document_converter import DocumentConverter, PdfFormatOption  # pyright: ignore[reportMissingImports]
    except ImportError as err:
        raise RuntimeError("Docling chỉ khả dụng trong môi trường container Linux.") from err

    tuy_chon_pdf = PdfPipelineOptions()
    tuy_chon_pdf.do_ocr = False
    tuy_chon_pdf.do_table_structure = True

    bo_chuyen_doi = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=tuy_chon_pdf)
        }
    )

    ket_qua = bo_chuyen_doi.convert(str(duong_dan_tep))
    tai_lieu = ket_qua.document
    so_trang = len(tai_lieu.pages) if hasattr(tai_lieu, "pages") and tai_lieu.pages else 1
    noi_dung_md = tai_lieu.export_to_markdown()
    return noi_dung_md, so_trang


def doc_noi_dung_van_ban(duong_dan_tep: Path) -> tuple[str, int]:
    """Đọc nội dung văn bản và xác định số trang tương ứng."""
    if duong_dan_tep.suffix.lower() == ".md":
        with open(duong_dan_tep, "r", encoding="utf-8") as f:
            noi_dung = f.read()
        return noi_dung, 1
    return _doc_tep_docling(duong_dan_tep)


def kiem_tra_chat_luong_van_ban(
    van_ban: str,
    so_trang: int,
    cau_hinh: dict[str, Any],
) -> str | None:
    """Kiểm tra điều kiện OCR và bảng mã tiếng Việt. Trả về lý do lỗi nếu không đạt."""
    ky_tu_toi_thieu = cau_hinh["ky_tu_toi_thieu_moi_trang"]
    ty_le_toi_thieu = cau_hinh["ty_le_tu_co_dau_toi_thieu"]

    so_ky_tu_tb = len(van_ban.strip()) / max(so_trang, 1)
    if so_ky_tu_tb < ky_tu_toi_thieu:
        return "cần OCR"

    ty_le_co_dau = tinh_ty_le_tu_co_dau(van_ban)
    if ty_le_co_dau < ty_le_toi_thieu:
        return "lớp chữ lỗi, cần OCR"

    return None


async def _luu_csdl_dong_bo(
    session: AsyncSession,
    sieu_du_lieu: dict[str, Any],
    cac_doan: list[Any],
    bam_noi_dung: str,
    model_nhung: str,
) -> KetQuaNap:
    """Ghi hoặc cập nhật tài liệu và các đoạn con vào CSDL trong một giao dịch."""
    ma_tl = sieu_du_lieu["ma_tai_lieu"]
    cau_lenh = select(TaiLieuModel).where(TaiLieuModel.ma_tai_lieu == ma_tl)
    tl_cu = (await session.scalars(cau_lenh)).first()

    if tl_cu and tl_cu.bam_noi_dung == bam_noi_dung:
        return KetQuaNap(
            ten_tep=ma_tl,
            so_doan=len(cac_doan),
            trang_thai="BỎ QUA",
            ly_do="Nội dung không đổi",
        )

    # In cảnh báo vector để NULL theo yêu cầu PROMPT 26
    logger.warning("Cột vector của các đoạn đang để NULL (sẽ tính ở PROMPT 27)")

    if tl_cu:
        await session.execute(delete(DoanModel).where(DoanModel.tai_lieu_id == tl_cu.id))
        _cap_nhat_thuoc_tinh_tai_lieu(tl_cu, sieu_du_lieu, bam_noi_dung, model_nhung)
        tai_lieu_id = tl_cu.id
    else:
        tl_moi = _tao_doi_tuong_tai_lieu(sieu_du_lieu, bam_noi_dung, model_nhung)
        session.add(tl_moi)
        await session.flush()
        tai_lieu_id = tl_moi.id

    for doan in cac_doan:
        session.add(
            DoanModel(
                tai_lieu_id=tai_lieu_id,
                thu_tu=doan.thu_tu,
                tieu_de_muc=doan.tieu_de_muc,
                duong_dan_muc=doan.duong_dan_muc,
                noi_dung=doan.noi_dung,
                so_token=doan.so_token,
                vector=None,
            )
        )

    return KetQuaNap(ten_tep=ma_tl, so_doan=len(cac_doan), trang_thai="ĐÃ NẠP")


def _tao_doi_tuong_tai_lieu(
    sieu_du_lieu: dict[str, Any],
    bam_noi_dung: str,
    model_nhung: str,
) -> TaiLieuModel:
    """Khởi tạo đối tượng TaiLieuModel mới từ siêu dữ liệu."""
    ngay_bh = sieu_du_lieu["ngay_ban_hanh"]
    if isinstance(ngay_bh, str):
        ngay_bh = date.fromisoformat(ngay_bh)

    ngay_hhl = sieu_du_lieu.get("ngay_het_hieu_luc")
    if isinstance(ngay_hhl, str):
        ngay_hhl = date.fromisoformat(ngay_hhl)

    return TaiLieuModel(
        ma_tai_lieu=sieu_du_lieu["ma_tai_lieu"],
        tieu_de=sieu_du_lieu["tieu_de"],
        loai_van_ban=sieu_du_lieu.get("loai_van_ban"),
        tinh_trang=sieu_du_lieu["tinh_trang"],
        pham_vi_doc=sieu_du_lieu["pham_vi_doc"],
        van_ban_thay_the=sieu_du_lieu.get("van_ban_thay_the"),
        ngay_ban_hanh=ngay_bh,
        ngay_het_hieu_luc=ngay_hhl,
        don_vi_quan_ly=sieu_du_lieu.get("don_vi_quan_ly"),
        model_nhung=model_nhung,
        bam_noi_dung=bam_noi_dung,
    )


def _cap_nhat_thuoc_tinh_tai_lieu(
    tl: TaiLieuModel,
    sieu_du_lieu: dict[str, Any],
    bam_noi_dung: str,
    model_nhung: str,
) -> None:
    """Cập nhật các trường thông tin của đối tượng TaiLieuModel đã tồn tại."""
    tl.tieu_de = sieu_du_lieu["tieu_de"]
    tl.loai_van_ban = sieu_du_lieu.get("loai_van_ban")
    tl.tinh_trang = sieu_du_lieu["tinh_trang"]
    tl.pham_vi_doc = sieu_du_lieu["pham_vi_doc"]
    tl.van_ban_thay_the = sieu_du_lieu.get("van_ban_thay_the")
    tl.don_vi_quan_ly = sieu_du_lieu.get("don_vi_quan_ly")
    tl.model_nhung = model_nhung
    tl.bam_noi_dung = bam_noi_dung


def _tinh_bam_noi_dung_tep(duong_dan_tep: Path) -> str:
    """Tính mã băm SHA-256 của tệp tài liệu nhị phân gốc."""
    with open(duong_dan_tep, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


async def nap_mot_tai_lieu(
    duong_dan_tep: Path,
    session: AsyncSession | None = None,
) -> KetQuaNap:
    """Xử lý nạp một tệp tài liệu duy nhất theo thứ tự kiểm tra nghiêm ngặt."""
    ten_tep = duong_dan_tep.name

    # Bước (a): Kiểm tra định dạng hỗ trợ
    if not kiem_tra_dinh_dang(duong_dan_tep):
        return KetQuaNap(ten_tep=ten_tep, so_doan=0, trang_thai="TỪ CHỐI", ly_do="định dạng không hỗ trợ")

    # Bước (b): Kiểm tra tệp siêu dữ liệu .meta.yaml
    sieu_du_lieu, loi_meta = kiem_tra_sieu_du_lieu(duong_dan_tep)
    if sieu_du_lieu is None or loi_meta:
        return KetQuaNap(ten_tep=ten_tep, so_doan=0, trang_thai="TỪ CHỐI", ly_do=loi_meta)

    # Đọc cấu hình ngưỡng
    cau_hinh = doc_cau_hinh_rag()

    # Đọc nội dung tệp
    try:
        van_ban_md, so_trang = doc_noi_dung_van_ban(duong_dan_tep)
    except (RuntimeError, ValueError, OSError, TypeError) as err:
        logger.error("Lỗi khi đọc tệp %s: %s", ten_tep, err)
        return KetQuaNap(ten_tep=ten_tep, so_doan=0, trang_thai="TỪ CHỐI", ly_do="cần OCR")

    # Bước (c) & (d): Kiểm tra chất lượng (lớp chữ và bảng mã)
    loi_chat_luong = kiem_tra_chat_luong_van_ban(van_ban_md, so_trang, cau_hinh)
    if loi_chat_luong:
        return KetQuaNap(ten_tep=ten_tep, so_doan=0, trang_thai="TỪ CHỐI", ly_do=loi_chat_luong)

    # Tính hàm băm nội dung của tệp nhị phân gốc
    bam_noi_dung = _tinh_bam_noi_dung_tep(duong_dan_tep)

    cac_doan = cat_doan(van_ban_md, cau_hinh["token_doan_toi_da"])

    # Lưu vào CSDL trong một giao dịch
    if session is not None:
        kq = await _luu_csdl_dong_bo(session, sieu_du_lieu, cac_doan, bam_noi_dung, cau_hinh["model_nhung"])
        kq.ten_tep = ten_tep
        return kq

    factory = lay_sessionmaker_async()
    async with factory() as phien_moi, phien_moi.begin():
        kq = await _luu_csdl_dong_bo(phien_moi, sieu_du_lieu, cac_doan, bam_noi_dung, cau_hinh["model_nhung"])
        kq.ten_tep = ten_tep
        return kq


async def cap_nhat_het_hieu_luc(
    ma_tai_lieu: str,
    van_ban_thay_the: str,
    session: AsyncSession | None = None,
) -> bool:
    """Đánh dấu tài liệu hết hiệu lực và lưu văn bản thay thế để bảo toàn truy vết."""
    async def _xu_ly(s: AsyncSession) -> bool:
        cau_lenh = select(TaiLieuModel).where(TaiLieuModel.ma_tai_lieu == ma_tai_lieu)
        tl = (await s.scalars(cau_lenh)).first()
        if not tl:
            return False
        tl.tinh_trang = "het_hieu_luc"
        tl.van_ban_thay_the = van_ban_thay_the
        tl.cap_nhat_luc = func.now()
        return True

    if session is not None:
        return await _xu_ly(session)

    factory = lay_sessionmaker_async()
    async with factory() as phien_moi, phien_moi.begin():
        return await _xu_ly(phien_moi)
