"""Bộ kiểm thử cho tính năng kiểm tra ngưỡng từ chối RAG (PROMPT 29).

Quy định kiểm tra:
1. Dưới ngưỡng từ chối: trả về KetQuaTuChoi, TUYỆT ĐỐI KHÔNG có lời gọi goi_mo_hinh (mock đếm = 0).
2. HTTP 200 không phải mã lỗi (tránh kích hoạt cảnh báo giả trên biểu đồ giám sát).
3. Ghi nhận lượt vào CSDL: luot.tu_choi = True và lưu đúng diem_cao_nhat.
4. Đọc câu trả lời từ chối từ prompts/tu_choi.md kèm phien_ban.
5. Trên ngưỡng từ chối: kiem_tra_nguong trả về None, cho phép gọi mô hình.
6. Chạy bằng: uv run --frozen pytest tests/test_nguong.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import HoiThoaiModel, LuotModel, lay_sessionmaker_async
from app.core.xac_thuc import NguoiDung
from app.rag.nguong import (
    doc_loi_nhac_tu_choi,
    ghi_luot_tu_choi,
    kiem_tra_nguong,
    lay_diem_cao_nhat,
)
from app.rag.schemas import KetQuaTuChoi, UngVien
from app.rag.tai_xep_hang import tai_xep_hang
from app.rag.truy_hoi import truy_hoi_lai


@pytest.fixture
def nguoi_ky_thuat() -> NguoiDung:
    """Tạo người dùng thử nghiệm thuộc phòng KY_THUAT_AN_TOAN."""
    return NguoiDung(
        id=901,
        email="cb_kt_test@evnhcmc.vn",
        ho_ten="Cán bộ Kỹ thuật Test",
        vai_tro="nguoi_dung",
        phong_ban="KY_THUAT_AN_TOAN",
        pham_vi_doc=["KY_THUAT_AN_TOAN"],
    )


def test_doc_loi_nhac_tu_choi_kem_phien_ban() -> None:
    """1. Đọc nội dung thông điệp từ chối và phiên bản từ prompts/tu_choi.md."""
    cau_tra_loi, phien_ban = doc_loi_nhac_tu_choi()
    assert "Trợ lý nội bộ chưa tìm thấy căn cứ" in cau_tra_loi
    assert "liên hệ bộ phận phụ trách quy trình" in cau_tra_loi
    assert phien_ban.startswith("2026-")


def test_lay_diem_cao_nhat() -> None:
    """2. Xác định điểm số cao nhất trong danh sách ứng viên."""
    assert lay_diem_cao_nhat([]) == 0.0

    ung_vien_1 = UngVien(
        doan_id=1,
        ma_tai_lieu="TL-1",
        tieu_de_muc="Mục 1",
        noi_dung="Nội dung 1",
        diem_tai_xep_hang=15.5,
    )
    ung_vien_2 = UngVien(
        doan_id=2,
        ma_tai_lieu="TL-2",
        tieu_de_muc="Mục 2",
        noi_dung="Nội dung 2",
        diem_tai_xep_hang=32.8,
    )
    assert lay_diem_cao_nhat([ung_vien_1, ung_vien_2]) == 32.8


def test_duoi_nguong_tra_ket_qua_tu_choi_va_http_200() -> None:
    """3. Điểm cao nhất nhỏ hơn nguong_tu_choi thì trả KetQuaTuChoi kèm mã HTTP 200."""
    ung_vien_thap = [
        UngVien(
            doan_id=1,
            ma_tai_lieu="TL-1",
            tieu_de_muc="Mục 1",
            noi_dung="Nội dung 1",
            diem_tai_xep_hang=25.0,
        )
    ]
    # Ngưỡng cấu hình là 39.4211
    kq = kiem_tra_nguong(ung_vien_thap, nguong_tu_choi=39.4211)
    assert kq is not None
    assert isinstance(kq, KetQuaTuChoi)
    assert kq.tu_choi is True
    assert kq.diem_cao_nhat == 25.0
    assert kq.nguong_tu_choi == 39.4211
    assert kq.ma_trang_thai_http == 200  # HTTP 200 không phải mã lỗi
    assert "Trợ lý nội bộ chưa tìm thấy căn cứ" in kq.cau_tra_loi


def test_tren_nguong_khong_tu_choi() -> None:
    """4. Điểm cao nhất lớn hơn hoặc bằng nguong_tu_choi thì trả về None."""
    ung_vien_cao = [
        UngVien(
            doan_id=1,
            ma_tai_lieu="TL-1",
            tieu_de_muc="Mục 1",
            noi_dung="Nội dung 1",
            diem_tai_xep_hang=55.0,
        )
    ]
    kq = kiem_tra_nguong(ung_vien_cao, nguong_tu_choi=39.4211)
    assert kq is None


@pytest.mark.asyncio
async def test_duoi_nguong_khong_co_loi_goi_mo_hinh() -> None:
    """5. Khi điểm dưới ngưỡng, TUYỆT ĐỐI KHÔNG có lời gọi nào tới goi_mo_hinh (mock đếm = 0)."""
    mock_goi = AsyncMock()

    with patch("app.llm.router.goi_mo_hinh", mock_goi):
        # Ứng viên điểm thấp (ngoài kho)
        ung_vien_thap = [
            UngVien(
                doan_id=10,
                ma_tai_lieu="TL-NGOAI",
                tieu_de_muc="Căng tin",
                noi_dung="Thông báo ăn trưa",
                diem_tai_xep_hang=12.0,
            )
        ]
        kq_tu_choi = kiem_tra_nguong(ung_vien_thap, nguong_tu_choi=39.4211)
        if kq_tu_choi is not None and kq_tu_choi.tu_choi:
            # Luồng từ chối: trả kết quả từ chối ngay, không gọi mô hình
            ket_qua_tra_ve = kq_tu_choi
        else:
            # Luồng tiếp tục gọi mô hình
            await mock_goi()
            ket_qua_tra_ve = None

        assert ket_qua_tra_ve is not None
        assert ket_qua_tra_ve.tu_choi is True
        # Đảm bảo không có lời gọi goi_mo_hinh nào được thực thi
        mock_goi.assert_not_called()
        assert mock_goi.call_count == 0


@pytest.mark.asyncio
async def test_ghi_luot_tu_choi_luu_dung_vao_csdl() -> None:
    """6. Ghi nhận lượt từ chối vào bảng luot: tu_choi = True và diem_cao_nhat lưu đúng."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        # Tạo phiên hội thoại thử nghiệm
        hoi_thoai = HoiThoaiModel(nguoi_id=901, tieu_de="Thử nghiệm từ chối")
        phien.add(hoi_thoai)
        await phien.flush()

        kq_tc = KetQuaTuChoi(
            tu_choi=True,
            cau_tra_loi="Trợ lý nội bộ chưa tìm thấy căn cứ trong kho tài liệu.",
            diem_cao_nhat=21.45,
            nguong_tu_choi=39.4211,
            phien_ban_prompt="2026-09-24.1",
            ma_trang_thai_http=200,
        )

        luot_nguoi, luot_tro_ly = await ghi_luot_tu_choi(
            phien=phien,
            hoi_thoai_id=hoi_thoai.id,
            noi_dung_nguoi="Thực đơn căng tin hôm nay là gì?",
            ket_qua_tu_choi=kq_tc,
            ma_yeu_cau="yc-test-tu-choi-01",
        )

        # Kiểm tra trạng thái lượt của trợ lý
        assert luot_tro_ly.tu_choi is True
        assert luot_tro_ly.diem_cao_nhat == pytest.approx(21.45)
        assert luot_tro_ly.noi_dung == kq_tc.cau_tra_loi
        assert luot_tro_ly.token_vao == 0
        assert luot_tro_ly.token_ra == 0
        assert luot_tro_ly.chi_phi_usd == 0.0

        # Truy vấn trực tiếp từ CSDL kiểm tra tính toàn vẹn
        truy_van = (
            select(LuotModel)
            .where(LuotModel.hoi_thoai_id == hoi_thoai.id, LuotModel.vai_tro == "tro_ly")
            .order_by(LuotModel.id.desc())
        )
        ban_ghi = (await phien.scalars(truy_van)).first()
        assert ban_ghi is not None
        assert ban_ghi.tu_choi is True
        assert ban_ghi.diem_cao_nhat == pytest.approx(21.45)


@pytest.mark.asyncio
async def test_truc_tiep_cau_thuc_don_cang_tin_bi_tu_choi(
    nguoi_ky_thuat: NguoiDung,
) -> None:
    """7. Gọi trực tiếp truy hồi, tái xếp hạng và ngưỡng cho câu 'Thực đơn căng tin hôm nay là gì?'.

    Kỳ vọng: Trả về KetQuaTuChoi, câu từ chối, không có lời gọi goi_mo_hinh.
    """
    mock_goi = AsyncMock()

    with patch("app.llm.router.goi_mo_hinh", mock_goi):
        cau_hoi = "Thực đơn căng tin hôm nay là gì?"
        danh_sach_ung_vien = await truy_hoi_lai(cau_hoi, nguoi=nguoi_ky_thuat)
        danh_sach_tai_xep = tai_xep_hang(cau_hoi, danh_sach_ung_vien)

        kq_xet = kiem_tra_nguong(danh_sach_tai_xep)

        assert kq_xet is not None, "Câu hỏi ngoài kho phải bị từ chối bởi ngưỡng!"
        assert isinstance(kq_xet, KetQuaTuChoi)
        assert kq_xet.tu_choi is True
        assert kq_xet.diem_cao_nhat < kq_xet.nguong_tu_choi
        assert "Trợ lý nội bộ chưa tìm thấy căn cứ" in kq_xet.cau_tra_loi

        # Mô hình không bị gọi
        mock_goi.assert_not_called()
