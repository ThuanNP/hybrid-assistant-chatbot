"""Kiểm thử lược đồ kho tri thức RAG và các ràng buộc toàn vẹn cơ sở dữ liệu."""

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import DoanModel, TaiLieuModel
from app.rag.schemas import NguonThamChieu, SieuDuLieuTaiLieu


def test_sieu_du_lieu_tai_lieu_thieu_tinh_trang_bi_tu_choi() -> None:
    """Kiểm tra Pydantic từ chối nếu thiếu trường bắt buộc tinh_trang, không gán mặc định."""
    du_lieu = {
        "ma_tai_lieu": "QD-123",
        "tieu_de": "Quy định giá điện 2026",
        # Thiếu tinh_trang
        "pham_vi_doc": ["KINH_DOANH"],
        "ngay_ban_hanh": date(2026, 1, 1),
        "model_nhung": "bge-m3",
    }
    with pytest.raises(ValidationError) as exc_info:
        SieuDuLieuTaiLieu(**du_lieu)
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("tinh_trang",) for err in errors)


def test_sieu_du_lieu_tai_lieu_thieu_truong_bat_buoc_khac_bi_tu_choi() -> None:
    """Kiểm tra các trường bắt buộc khác (ma_tai_lieu, tieu_de, pham_vi_doc, ngay_ban_hanh, model_nhung) không có giá trị mặc định."""
    du_lieu_thieu_model = {
        "ma_tai_lieu": "QD-124",
        "tieu_de": "Quy chế an toàn điện",
        "tinh_trang": "con_hieu_luc",
        "pham_vi_doc": ["KY_THUAT_AN_TOAN"],
        "ngay_ban_hanh": date(2026, 1, 1),
        # Thiếu model_nhung
    }
    with pytest.raises(ValidationError) as exc_info:
        SieuDuLieuTaiLieu(**du_lieu_thieu_model)
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("model_nhung",) for err in errors)


def test_sieu_du_lieu_tai_lieu_het_hieu_luc_thieu_van_ban_thay_the_bi_tu_choi() -> None:
    """Kiểm tra Pydantic từ chối tài liệu het_hieu_luc nếu không có văn bản thay thế."""
    du_lieu = {
        "ma_tai_lieu": "QD-999",
        "tieu_de": "Quy định cũ đã hết hiệu lực",
        "tinh_trang": "het_hieu_luc",
        "pham_vi_doc": ["CNTT"],
        "ngay_ban_hanh": date(2020, 1, 1),
        "model_nhung": "bge-m3",
        "van_ban_thay_the": None,
    }
    with pytest.raises(ValidationError) as exc_info:
        SieuDuLieuTaiLieu(**du_lieu)
    loi = str(exc_info.value)
    assert "văn bản thay thế" in loi


def test_sieu_du_lieu_tai_lieu_hop_le() -> None:
    """Kiểm tra tài liệu hợp lệ được tạo thành công."""
    du_lieu = {
        "ma_tai_lieu": "QD-2026-01",
        "tieu_de": "Biểu giá chi phí điện lực mới",
        "tinh_trang": "con_hieu_luc",
        "pham_vi_doc": ["KINH_DOANH", "CHAM_SOC_KHACH_HANG"],
        "ngay_ban_hanh": date(2026, 3, 1),
        "model_nhung": "bge-m3",
        "don_vi_quan_ly": "Ban Kinh Doanh",
    }
    tai_lieu = SieuDuLieuTaiLieu(**du_lieu)
    assert tai_lieu.ma_tai_lieu == "QD-2026-01"
    assert tai_lieu.tinh_trang == "con_hieu_luc"


def test_nguon_tham_chieu_hop_le() -> None:
    """Kiểm tra schema NguonThamChieu khớp cấu trúc quy định."""
    ref = NguonThamChieu(
        ma_tai_lieu="QD-01",
        tieu_de_muc="Điều 3. Biểu giá",
        doan_id=10,
        diem=0.88,
    )
    assert ref.ma_tai_lieu == "QD-01"
    assert ref.diem == 0.88


@pytest.mark.asyncio
async def test_csdl_het_hieu_luc_thieu_van_ban_thay_the_loi_rang_buoc(
    phien_csdl: AsyncSession,
) -> None:
    """Kiểm tra ràng buộc CHECK tại tầng CSDL: hết hiệu lực mà thiếu văn bản thay thế sẽ lỗi."""
    tl = TaiLieuModel(
        ma_tai_lieu="TEST-HET-HL-CSDL",
        tieu_de="Tài liệu kiểm thử hết hiệu lực",
        tinh_trang="het_hieu_luc",
        pham_vi_doc=["CNTT"],
        van_ban_thay_the=None,  # Vi phạm ràng buộc CHECK ck_tai_lieu_van_ban_thay_the
        ngay_ban_hanh=date(2025, 1, 1),
        model_nhung="bge-m3",
    )
    phien_csdl.add(tl)
    with pytest.raises(IntegrityError):
        await phien_csdl.commit()
    await phien_csdl.rollback()


@pytest.mark.asyncio
async def test_csdl_chi_muc_hnsw_va_gin_ton_tai(phien_csdl: AsyncSession) -> None:
    """Kiểm tra chỉ mục HNSW và GIN trên bảng doan đã được tạo trong PostgreSQL."""
    truy_van = text(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'doan';
        """
    )
    ket_qua = await phien_csdl.execute(truy_van)
    chi_muc = {row[0]: row[1] for row in ket_qua.fetchall()}

    assert "ix_doan_vector_hnsw" in chi_muc, "Chỉ mục HNSW trên cột vector không tồn tại"
    assert "hnsw" in chi_muc["ix_doan_vector_hnsw"].lower(), "Chỉ mục không phải kiểu HNSW"
    assert "vector_cosine_ops" in chi_muc["ix_doan_vector_hnsw"].lower(), "Chỉ mục không dùng vector_cosine_ops"

    assert "ix_doan_tsv_gin" in chi_muc, "Chỉ mục GIN trên cột tsv không tồn tại"
    assert "gin" in chi_muc["ix_doan_tsv_gin"].lower(), "Chỉ mục không phải kiểu GIN"


@pytest.mark.asyncio
async def test_csdl_xoa_tai_lieu_cascade_doan(phien_csdl: AsyncSession) -> None:
    """Kiểm tra xoá tài liệu sẽ cascade xoá sạch các đoạn con liên kết."""
    tl = TaiLieuModel(
        ma_tai_lieu="TEST-CASCADE-TL",
        tieu_de="Tài liệu thử cascade delete",
        tinh_trang="con_hieu_luc",
        pham_vi_doc=["CNTT"],
        ngay_ban_hanh=date(2026, 1, 1),
        model_nhung="bge-m3",
    )
    phien_csdl.add(tl)
    await phien_csdl.flush()

    doan = DoanModel(
        tai_lieu_id=tl.id,
        thu_tu=1,
        tieu_de_muc="Mục 1",
        noi_dung="Nội dung thử nghiệm",
    )
    phien_csdl.add(doan)
    await phien_csdl.commit()

    doan_id = doan.id

    # Xoá tài liệu
    await phien_csdl.delete(tl)
    await phien_csdl.commit()
    phien_csdl.expire_all()

    # Kiểm tra đoạn con đã bị xoá khỏi CSDL theo cascade
    cau_lenh_doan = select(DoanModel).where(DoanModel.id == doan_id)
    doan_tim = (await phien_csdl.scalars(cau_lenh_doan)).first()
    assert doan_tim is None


@pytest.mark.asyncio
async def test_tim_kiem_tieng_viet_khong_dau_khop_noi_dung_co_dau(
    phien_csdl: AsyncSession,
) -> None:
    """Kiểm tra cấu hình tìm kiếm 'tieng_viet' (simple + unaccent) khớp cả khi gõ từ khoá không dấu."""
    tl = TaiLieuModel(
        ma_tai_lieu="TEST-SEARCH-FTS",
        tieu_de="Hướng dẫn tiết kiệm điện năng mùa cao điểm hè",
        tinh_trang="con_hieu_luc",
        pham_vi_doc=["CHAM_SOC_KHACH_HANG"],
        ngay_ban_hanh=date(2026, 6, 1),
        model_nhung="bge-m3",
    )
    phien_csdl.add(tl)
    await phien_csdl.flush()

    doan = DoanModel(
        tai_lieu_id=tl.id,
        thu_tu=1,
        tieu_de_muc="Chương I: Biện pháp giảm phụ tải",
        noi_dung="Các hộ tiêu thụ điện công nghiệp cần bố trí ca sản xuất hợp lý tránh giờ cao điểm.",
    )
    phien_csdl.add(doan)
    await phien_csdl.commit()

    try:
        # Truy vấn tìm kiếm bằng từ khoá không dấu: "tieu thu dien cong nghiep"
        truy_van = text(
            """
            SELECT id, tieu_de_muc
            FROM doan
            WHERE id = :doan_id
              AND tsv @@ to_tsquery('tieng_viet', 'tieu & thu & dien & cong & nghiep');
            """
        )
        kq = await phien_csdl.execute(truy_van, {"doan_id": doan.id})
        dong = kq.fetchone()
        assert dong is not None, "Không tìm thấy đoạn văn bản khi tìm kiếm không dấu"
        assert dong[0] == doan.id
    finally:
        await phien_csdl.delete(tl)
        await phien_csdl.commit()
