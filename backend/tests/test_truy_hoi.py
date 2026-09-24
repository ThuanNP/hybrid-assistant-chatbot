"""Bộ kiểm thử cho tính năng truy hồi lai và tái xếp hạng kho tri thức RAG (PROMPT 28).

Tuân thủ nghiêm ngặt:
- Kiểm thử trên kho tài liệu mẫu đã nạp: LUAT-61-2024-QH15, QD-DICH-VU-DIEN-2024,
  LUAT-28-2004-QH11, HD-DMTMN-2025.
- Đoạn của văn bản hết hiệu lực (LUAT-28-2004-QH11) không bao giờ xuất hiện.
- Phân quyền theo phòng ban: KY_THUAT_AN_TOAN không đọc được QD-DICH-VU-DIEN-2024,
  KINH_DOANH thì đọc được.
- Tái xếp hạng: Câu hỏi có số hiệu "61/2024/QH15" xếp tài liệu đó lên đầu.
- Cổng phủ từ khóa 30%: Trả điểm 0 khi tỷ lệ từ trùng dưới 30%.
- Cụm hai âm tiết (bigram): "giá cổ phiếu hôm nay" không khớp "phiếu công tác".
- GET /api/v1/toi trả về pham_vi_doc.
- Chạy bằng: uv run --frozen pytest tests/test_truy_hoi.py -v
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.main import app
from app.rag.schemas import UngVien
from app.rag.tai_xep_hang import tai_xep_hang
from app.rag.truy_hoi import truy_hoi_lai


@pytest.fixture
def nguoi_kinh_doanh() -> NguoiDung:
    """Tạo người dùng thuộc phòng KINH_DOANH."""
    return NguoiDung(
        id=101,
        email="cb_kd@evnhcmc.vn",
        ho_ten="Cán bộ Kinh doanh",
        vai_tro="nguoi_dung",
        phong_ban="KINH_DOANH",
        pham_vi_doc=["KINH_DOANH"],
    )


@pytest.fixture
def nguoi_ky_thuat() -> NguoiDung:
    """Tạo người dùng thuộc phòng KY_THUAT_AN_TOAN."""
    return NguoiDung(
        id=102,
        email="cb_kt@evnhcmc.vn",
        ho_ten="Cán bộ Kỹ thuật",
        vai_tro="nguoi_dung",
        phong_ban="KY_THUAT_AN_TOAN",
        pham_vi_doc=["KY_THUAT_AN_TOAN"],
    )


@pytest.mark.asyncio
async def test_van_ban_het_hieu_luc_khong_bao_gio_xuat_hien(
    nguoi_kinh_doanh: NguoiDung,
) -> None:
    """1. Đoạn của LUAT-28-2004-QH11 (tinh_trang = 'het_hieu_luc') không bao giờ xuất hiện."""
    vector_gia = [0.01] * 1024
    kq = await truy_hoi_lai(
        cau_hoi="Quy định về giá bán điện và thị trường điện",
        nguoi=nguoi_kinh_doanh,
        ngay_tra_cuu=date(2026, 9, 24),
        vector_cau_hoi=vector_gia,
    )

    cac_ma = [uv.ma_tai_lieu for uv in kq]
    assert "LUAT-28-2004-QH11" not in cac_ma, (
        "Lỗi bảo mật: Văn bản đã hết hiệu lực LUAT-28-2004-QH11 xuất hiện trong kết quả!"
    )
    assert len(kq) > 0


@pytest.mark.asyncio
async def test_phan_quyen_phong_ban_ky_thuat_khong_xem_duoc_quyet_dinh_dich_vu_dien(
    nguoi_ky_thuat: NguoiDung,
    nguoi_kinh_doanh: NguoiDung,
) -> None:
    """2. Phân quyền phòng ban:

    - KY_THUAT_AN_TOAN không truy hồi được QD-DICH-VU-DIEN-2024.
    - KINH_DOANH thì truy hồi được bình thường.
    """
    vector_gia = [0.01] * 1024
    cau_hoi = "thủ tục đăng ký dịch vụ cấp điện mới"

    # Người dùng phòng Kỹ thuật An toàn
    kq_kt = await truy_hoi_lai(
        cau_hoi=cau_hoi,
        nguoi=nguoi_ky_thuat,
        ngay_tra_cuu=date(2026, 9, 24),
        vector_cau_hoi=vector_gia,
    )
    ma_kt = {uv.ma_tai_lieu for uv in kq_kt}
    assert "QD-DICH-VU-DIEN-2024" not in ma_kt, (
        "Lỗi rò rỉ quyền: KY_THUAT_AN_TOAN xem được QD-DICH-VU-DIEN-2024!"
    )

    # Người dùng phòng Kinh doanh
    kq_kd = await truy_hoi_lai(
        cau_hoi=cau_hoi,
        nguoi=nguoi_kinh_doanh,
        ngay_tra_cuu=date(2026, 9, 24),
        vector_cau_hoi=vector_gia,
    )
    ma_kd = {uv.ma_tai_lieu for uv in kq_kd}
    assert "QD-DICH-VU-DIEN-2024" in ma_kd, (
        "Phòng KINH_DOANH phải xem được tài liệu QD-DICH-VU-DIEN-2024."
    )


@pytest.mark.asyncio
async def test_cau_hoi_nhac_van_ban_het_hieu_luc_tra_kem_van_ban_thay_the(
    nguoi_kinh_doanh: NguoiDung,
) -> None:
    """3. Câu hỏi nhắc tới văn bản hết hiệu lực: kèm van_ban_thay_the LUAT-61-2024-QH15."""
    vector_gia = [0.01] * 1024
    cau_hoi = "Luật Điện lực số 28/2004/QH11 quy định gì về giá điện?"

    kq = await truy_hoi_lai(
        cau_hoi=cau_hoi,
        nguoi=nguoi_kinh_doanh,
        ngay_tra_cuu=date(2026, 9, 24),
        vector_cau_hoi=vector_gia,
    )

    assert "LUAT-28-2004-QH11" not in [uv.ma_tai_lieu for uv in kq]
    assert kq.van_ban_thay_the == "LUAT-61-2024-QH15"


@pytest.mark.asyncio
async def test_truy_hoi_chi_tu_khoa_khi_khong_co_vector(
    nguoi_kinh_doanh: NguoiDung,
) -> None:
    """4. Khi che_do_truy_hoi = 'chi_tu_khoa', chỉ chạy nhánh từ khóa, hang_vector là None."""
    kq = await truy_hoi_lai(
        cau_hoi="điện mặt trời mái nhà",
        nguoi=nguoi_kinh_doanh,
        ngay_tra_cuu=date(2026, 9, 24),
        che_do_truy_hoi="chi_tu_khoa",
    )

    assert len(kq) > 0
    for uv in kq:
        assert uv.hang_vector is None
        assert uv.hang_tu_khoa is not None
        assert uv.diem_rrf > 0.0


def test_tai_xep_hang_so_hieu_61_2024_qh15_len_dau() -> None:
    """5. Tái xếp hạng: câu hỏi có số hiệu 61/2024/QH15 xếp văn bản đó lên đầu."""
    cau_hoi = "Theo Luật Điện lực số 61/2024/QH15 thì quy định về điện gió như thế nào?"

    ung_vien_1 = UngVien(
        doan_id=1,
        ma_tai_lieu="QD-DICH-VU-DIEN-2024",
        tieu_de_muc="Quy trình cung cấp điện",
        noi_dung="Cung cấp các dịch vụ phát triển nguồn điện và thỏa thuận đấu nối kỹ thuật.",
        so_token=100,
        diem_rrf=0.03,
    )
    ung_vien_2 = UngVien(
        doan_id=2,
        ma_tai_lieu="LUAT-61-2024-QH15",
        tieu_de_muc="Điều 20. Quy định chung phát triển điện năng lượng tái tạo",
        noi_dung="Căn cứ Luật Điện lực số 61/2024/QH15 về phát triển điện gió và điện mặt trời.",
        so_token=150,
        diem_rrf=0.02,
    )

    kq = tai_xep_hang(cau_hoi, [ung_vien_1, ung_vien_2])
    assert len(kq) == 2
    # Văn bản chứa số hiệu 61/2024/QH15 phải được xếp lên đầu
    assert kq[0].ma_tai_lieu == "LUAT-61-2024-QH15"
    assert (kq[0].diem_tai_xep_hang or 0) > (kq[1].diem_tai_xep_hang or 0)


def test_cong_phu_tu_khoa_duoi_30_phan_tram_tra_diem_khong() -> None:
    """6. Cổng phủ từ khóa: đoạn chứa dưới 30% số từ của câu hỏi thì điểm bằng 0."""
    cau_hoi = "Quy trình cấp điện trung áp cho khách hàng công nghiệp và khu chế xuất"
    # Đoạn chỉ chứa 1 từ trùng "khách hàng" trong 13 từ của câu hỏi (~7.6% < 30%)
    ung_vien = UngVien(
        doan_id=10,
        ma_tai_lieu="HD-DMTMN-2025",
        tieu_de_muc="Hướng dẫn chung",
        noi_dung="Đoạn văn bản chỉ nói về pin năng lượng mặt trời và hỗ trợ khách hàng.",
        so_token=50,
        diem_rrf=0.015,
    )

    kq = tai_xep_hang(cau_hoi, [ung_vien])
    assert len(kq) == 1
    assert kq[0].diem_tai_xep_hang == 0.0


def test_phan_biet_cum_hai_am_tiet_gia_co_phieu_khong_khop_phieu_cong_tac() -> None:
    """7. Tiếng Việt đa âm tiết: 'giá cổ phiếu hôm nay' không khớp 'phiếu công tác'."""
    cau_hoi = "giá cổ phiếu hôm nay"
    # Đoạn văn về an toàn lao động có chứa từ "phiếu công tác"
    ung_vien = UngVien(
        doan_id=20,
        ma_tai_lieu="QD-AN-TOAN",
        tieu_de_muc="Biện pháp an toàn",
        noi_dung="Trước khi làm việc trên lưới điện phải làm thủ tục cấp phiếu công tác theo quy trình.",
        so_token=80,
        diem_rrf=0.01,
    )

    kq = tai_xep_hang(cau_hoi, [ung_vien])
    assert len(kq) == 1
    # Bị cổng phủ loại trừ hoặc điểm bằng 0 do không khớp bigram
    assert kq[0].diem_tai_xep_hang == 0.0


def test_he_so_phat_doan_dai_tu_0_85_den_1_00() -> None:
    """8. Hệ số nhân phạt đoạn dài giảm dần từ 1.00 về 0.85 khi độ dài tăng."""
    cau_hoi = "tiêu chuẩn hệ thống điện mặt trời"
    # Đoạn ngắn (150 token <= ngưỡng 200 token)
    uv_ngan = UngVien(
        doan_id=1,
        ma_tai_lieu="HD-DMTMN-2025",
        tieu_de_muc="Hệ thống điện mặt trời",
        noi_dung="Tiêu chuẩn kỹ thuật hệ thống điện mặt trời mái nhà.",
        so_token=150,
        diem_rrf=0.02,
    )
    # Đoạn dài (500 token)
    uv_dai = UngVien(
        doan_id=2,
        ma_tai_lieu="HD-DMTMN-2025",
        tieu_de_muc="Hệ thống điện mặt trời",
        noi_dung="Tiêu chuẩn kỹ thuật hệ thống điện mặt trời mái nhà." + " nội dung dài" * 80,
        so_token=500,
        diem_rrf=0.02,
    )

    kq = tai_xep_hang(cau_hoi, [uv_ngan, uv_dai])
    assert len(kq) == 2
    diem_ngan = next(x.diem_tai_xep_hang for x in kq if x.doan_id == 1) or 0.0
    diem_dai = next(x.diem_tai_xep_hang for x in kq if x.doan_id == 2) or 0.0

    assert diem_ngan > diem_dai
    # Điểm đoạn dài bằng đúng tỷ lệ phạt 0.85 so với điểm chưa phạt
    assert round(diem_dai / (diem_ngan if diem_ngan > 0 else 1.0), 2) == 0.85


def test_endpoint_get_toi_tra_ve_pham_vi_doc() -> None:
    """9. Endpoint GET /api/v1/toi trả về trường pham_vi_doc đầy đủ."""
    nguoi_test = NguoiDung(
        id=999,
        email="test_pham_vi@evnhcmc.vn",
        ho_ten="Người dùng Thử nghiệm",
        vai_tro="nguoi_dung",
        phong_ban="KY_THUAT_AN_TOAN",
        pham_vi_doc=["KY_THUAT_AN_TOAN"],
    )
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_test
    try:
        client = TestClient(app)
        phan_hoi = client.get("/api/v1/toi")
        assert phan_hoi.status_code == 200
        du_lieu = phan_hoi.json()
        assert "pham_vi_doc" in du_lieu
        assert du_lieu["pham_vi_doc"] == ["KY_THUAT_AN_TOAN"]
    finally:
        app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)

