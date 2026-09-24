"""Mô-đun truy hồi lai (Hybrid Search) kết hợp vector nhúng và tìm kiếm toàn văn.

KIẾN TRÚC BẢO MẬT VÀ TUÂN THỦ OWASP LLM08 (Vector and Embedding Weaknesses):
Lọc sau khi truy hồi (post-retrieval filtering) là SAI LẦM BẢO MẬT NGHIÊM TRỌNG:
1. Khi truy vấn không kèm điều kiện quyền, nội dung ngoài thẩm quyền của người dùng đã
   bị kéo vào bộ nhớ tiến trình xử lý, làm tăng nguy cơ rò rỉ vào ngữ cảnh LLM.
2. Số lượng kết quả bị lọc sau truy vấn vô tình tiết lộ sự tồn tại của tài liệu mật
   (Metadata / Existence Leakage).
Do đó, điều kiện kiểm tra thẩm quyền phòng ban (pham_vi_doc) và trạng thái hiệu lực
(tinh_trang, ngay_het_hieu_luc) BẮT BUỘC phải nằm trong mệnh đề WHERE của SQL ở TẤT CẢ
các nhánh CTE (nhánh vector và nhánh từ khóa). Tuyệt đối không dùng vòng lặp Python
để lọc quyền sau khi nhận kết quả từ CSDL.
"""

import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import TaiLieuModel, lay_sessionmaker_async
from app.core.xac_thuc import NguoiDung
from app.llm.router import _doc_cau_hinh_rag
from app.rag.nhung import nhung_cau_hoi
from app.rag.schemas import DanhSachUngVien, UngVien

logger = logging.getLogger(__name__)

__all__ = ["truy_hoi_lai"]


def _chuan_hoa_ma_tim_kiem(van_ban: str) -> str:
    """Loại bỏ ký tự phân cách đặc biệt để so khớp mã định danh văn bản."""
    return re.sub(r"[^a-zA-Z0-9]", "", van_ban).lower()


async def _tim_van_ban_thay_the(cau_hoi: str, session: AsyncSession) -> str | None:
    """Tìm mã văn bản thay thế nếu câu hỏi nhắc tới một văn bản đã hết hiệu lực.

    Căn cứ: Yêu cầu 3 - Khi câu hỏi nhắc tới văn bản hết hiệu lực, không trả nội dung cũ
    mà cung cấp văn bản thay thế để mô hình thông báo sự thay thế.
    """
    truy_van = select(TaiLieuModel.ma_tai_lieu, TaiLieuModel.van_ban_thay_the).where(
        TaiLieuModel.tinh_trang == "het_hieu_luc",
        TaiLieuModel.van_ban_thay_the.isnot(None),
    )
    ket_qua = await session.execute(truy_van)
    danh_sach = ket_qua.all()
    if not danh_sach:
        return None

    ch_chuan = _chuan_hoa_ma_tim_kiem(cau_hoi)
    for ma_tl, vb_thay_the in danh_sach:
        if not ma_tl or not vb_thay_the:
            continue
        ma_chuan = _chuan_hoa_ma_tim_kiem(ma_tl)
        if ma_chuan in ch_chuan:
            return str(vb_thay_the)
        ma_so_hieu = re.sub(r"^[a-zA-Z]+-", "", ma_tl)
        ma_so_hieu_chuan = _chuan_hoa_ma_tim_kiem(ma_so_hieu)
        if ma_so_hieu_chuan and ma_so_hieu_chuan in ch_chuan:
            return str(vb_thay_the)
    return None


def _tao_cau_lenh_sql_lai() -> str:
    """Tạo câu truy vấn SQL CTE duy nhất kết hợp vector và FTS qua Reciprocal Rank Fusion."""
    return """
    WITH nhan_vector AS (
        SELECT
            d.id AS doan_id,
            tl.ma_tai_lieu,
            d.tieu_de_muc,
            d.duong_dan_muc,
            d.noi_dung,
            d.so_token,
            ROW_NUMBER() OVER (
                ORDER BY d.vector <=> CAST(:vector_cau_hoi AS vector)
            ) AS hang_vector
        FROM doan d
        JOIN tai_lieu tl ON d.tai_lieu_id = tl.id
        WHERE tl.tinh_trang = 'con_hieu_luc'
          AND (tl.ngay_het_hieu_luc IS NULL OR tl.ngay_het_hieu_luc > :ngay_tra_cuu)
          AND tl.pham_vi_doc && :pham_vi_doc_nguoi_dung
          AND tl.model_nhung = :model_nhung
        ORDER BY d.vector <=> CAST(:vector_cau_hoi AS vector)
        LIMIT :k_truy_hoi
    ),
    nhan_tu_khoa AS (
        SELECT
            d.id AS doan_id,
            tl.ma_tai_lieu,
            d.tieu_de_muc,
            d.duong_dan_muc,
            d.noi_dung,
            d.so_token,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank(d.tsv, plainto_tsquery('simple', unaccent(:cau_hoi))) DESC
            ) AS hang_tu_khoa
        FROM doan d
        JOIN tai_lieu tl ON d.tai_lieu_id = tl.id
        WHERE tl.tinh_trang = 'con_hieu_luc'
          AND (tl.ngay_het_hieu_luc IS NULL OR tl.ngay_het_hieu_luc > :ngay_tra_cuu)
          AND tl.pham_vi_doc && :pham_vi_doc_nguoi_dung
          AND tl.model_nhung = :model_nhung
          AND d.tsv @@ plainto_tsquery('simple', unaccent(:cau_hoi))
        ORDER BY ts_rank(d.tsv, plainto_tsquery('simple', unaccent(:cau_hoi))) DESC
        LIMIT :k_truy_hoi
    ),
    hop_nhat AS (
        SELECT
            COALESCE(v.doan_id, k.doan_id) AS doan_id,
            COALESCE(v.ma_tai_lieu, k.ma_tai_lieu) AS ma_tai_lieu,
            COALESCE(v.tieu_de_muc, k.tieu_de_muc) AS tieu_de_muc,
            COALESCE(v.duong_dan_muc, k.duong_dan_muc) AS duong_dan_muc,
            COALESCE(v.noi_dung, k.noi_dung) AS noi_dung,
            COALESCE(v.so_token, k.so_token) AS so_token,
            v.hang_vector,
            k.hang_tu_khoa,
            (
                COALESCE(1.0 / (:k_rrf + v.hang_vector), 0.0) +
                COALESCE(1.0 / (:k_rrf + k.hang_tu_khoa), 0.0)
            ) AS diem_rrf
        FROM nhan_vector v
        FULL OUTER JOIN nhan_tu_khoa k ON v.doan_id = k.doan_id
    )
    SELECT
        doan_id,
        ma_tai_lieu,
        tieu_de_muc,
        duong_dan_muc,
        noi_dung,
        so_token,
        diem_rrf,
        hang_vector,
        hang_tu_khoa
    FROM hop_nhat
    ORDER BY diem_rrf DESC;
    """


def _tao_cau_lenh_sql_tu_khoa() -> str:
    """Tạo câu truy vấn SQL chỉ chạy nhánh từ khóa khi mô hình nhúng bị lỗi."""
    return """
    WITH nhan_tu_khoa AS (
        SELECT
            d.id AS doan_id,
            tl.ma_tai_lieu,
            d.tieu_de_muc,
            d.duong_dan_muc,
            d.noi_dung,
            d.so_token,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank(d.tsv, plainto_tsquery('simple', unaccent(:cau_hoi))) DESC
            ) AS hang_tu_khoa
        FROM doan d
        JOIN tai_lieu tl ON d.tai_lieu_id = tl.id
        WHERE tl.tinh_trang = 'con_hieu_luc'
          AND (tl.ngay_het_hieu_luc IS NULL OR tl.ngay_het_hieu_luc > :ngay_tra_cuu)
          AND tl.pham_vi_doc && :pham_vi_doc_nguoi_dung
          AND tl.model_nhung = :model_nhung
          AND d.tsv @@ plainto_tsquery('simple', unaccent(:cau_hoi))
        ORDER BY ts_rank(d.tsv, plainto_tsquery('simple', unaccent(:cau_hoi))) DESC
        LIMIT :k_truy_hoi
    )
    SELECT
        doan_id,
        ma_tai_lieu,
        tieu_de_muc,
        duong_dan_muc,
        noi_dung,
        so_token,
        (1.0 / (:k_rrf + hang_tu_khoa)) AS diem_rrf,
        NULL::integer AS hang_vector,
        hang_tu_khoa
    FROM nhan_tu_khoa
    ORDER BY diem_rrf DESC;
    """


async def _thuc_thi_truy_van(
    session: AsyncSession,
    cau_lenh: str,
    tham_so: dict[str, Any],
    van_ban_thay_the: str | None,
) -> DanhSachUngVien:
    """Thực thi câu SQL truy hồi và ánh xạ bản ghi CSDL sang danh sách UngVien."""
    ket_qua = await session.execute(text(cau_lenh), tham_so)
    cac_hang = ket_qua.all()

    danh_sach: list[UngVien] = []
    for h in cac_hang:
        danh_sach.append(
            UngVien(
                doan_id=int(h.doan_id),
                ma_tai_lieu=str(h.ma_tai_lieu),
                tieu_de_muc=str(h.tieu_de_muc),
                duong_dan_muc=str(h.duong_dan_muc) if h.duong_dan_muc else None,
                noi_dung=str(h.noi_dung),
                so_token=int(h.so_token or 0),
                diem_rrf=float(h.diem_rrf),
                hang_vector=int(h.hang_vector) if h.hang_vector is not None else None,
                hang_tu_khoa=int(h.hang_tu_khoa) if h.hang_tu_khoa is not None else None,
                van_ban_thay_the=van_ban_thay_the,
            )
        )

    return DanhSachUngVien(danh_sach, van_ban_thay_the=van_ban_thay_the)


async def truy_hoi_lai(
    cau_hoi: str,
    nguoi: NguoiDung,
    ngay_tra_cuu: date | None = None,
    *,
    session: AsyncSession | None = None,
    vector_cau_hoi: list[float] | None = None,
    che_do_truy_hoi: str = "lai",
    k_truy_hoi: int | None = None,
    k_rrf: int | None = None,
    model_nhung: str | None = None,
) -> DanhSachUngVien:
    """Truy hồi tài liệu lai (vector + từ khóa) trong một câu SQL CTE duy nhất.

    Tham số:
    - cau_hoi: Câu hỏi hoặc từ khóa tra cứu của người dùng.
    - nguoi: Đối tượng NguoiDung mang pham_vi_doc để kiểm soát quyền.
    - ngay_tra_cuu: Ngày kiểm tra hiệu lực (mặc định hôm nay).
    - session: AsyncSession tùy chọn; nếu không truyền sẽ tự mở phiên.
    - vector_cau_hoi: Vector nhúng câu hỏi (tự động tạo nếu chưa có).
    - che_do_truy_hoi: 'lai' hoặc 'chi_tu_khoa' (suy giảm mức 2).
    """
    rag_cfg = _doc_cau_hinh_rag()
    gioi_han_k = int(k_truy_hoi or rag_cfg.get("k_truy_hoi", 20))
    he_so_rrf = int(k_rrf or rag_cfg.get("k_rrf", 60))
    ten_model = str(model_nhung or rag_cfg.get("model_nhung", "bge-m3"))
    ngay_chuan = ngay_tra_cuu or datetime.now(timezone.utc).date()


    vec_hien_tai = vector_cau_hoi
    che_do_hien_tai = che_do_truy_hoi

    # Tạo vector nhúng cho câu hỏi nếu chưa có và đang ở chế độ lai
    if vec_hien_tai is None and che_do_hien_tai != "chi_tu_khoa":
        kq_nhung = await nhung_cau_hoi(cau_hoi)
        vec_hien_tai = kq_nhung.vector
        if kq_nhung.che_do_truy_hoi == "chi_tu_khoa" or vec_hien_tai is None:
            che_do_hien_tai = "chi_tu_khoa"

    # Định dạng chuỗi vector cho pgvector
    chuoi_vector = f"[{','.join(str(float(x)) for x in vec_hien_tai)}]" if vec_hien_tai else "[]"

    tham_so = {
        "cau_hoi": cau_hoi,
        "vector_cau_hoi": chuoi_vector,
        "ngay_tra_cuu": ngay_chuan,
        "pham_vi_doc_nguoi_dung": list(nguoi.pham_vi_doc),
        "model_nhung": ten_model,
        "k_truy_hoi": gioi_han_k,
        "k_rrf": he_so_rrf,
    }

    cau_lenh = (
        _tao_cau_lenh_sql_tu_khoa()
        if che_do_hien_tai == "chi_tu_khoa" or vec_hien_tai is None
        else _tao_cau_lenh_sql_lai()
    )

    async def _xu_ly(s: AsyncSession) -> DanhSachUngVien:
        vb_thay_the = await _tim_van_ban_thay_the(cau_hoi, s)
        return await _thuc_thi_truy_van(s, cau_lenh, tham_so, vb_thay_the)

    if session is not None:
        return await _xu_ly(session)

    factory = lay_sessionmaker_async()
    async with factory() as phien:
        return await _xu_ly(phien)
