"""Kiểm thử mô-đun câu hỏi thường gặp và hai endpoint tài liệu hướng dẫn."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.chat.thuong_gap import (
    chon_muc_lien_quan,
    dinh_dang_khoi_thuong_gap,
    lay_du_lieu_thuong_gap,
)
from app.core.xac_thuc import NguoiDung, tao_access_token
from app.llm.dem_token import dem_token
from app.main import app


def test_chon_dung_muc_theo_tu_khoa() -> None:
    """Kiểm tra chọn đúng mục liên quan dựa trên các từ khóa câu hỏi."""
    cau_hoi = "Làm sao để đăng nhập tài khoản vào hệ thống?"
    cac_muc = chon_muc_lien_quan(cau_hoi)

    assert len(cac_muc) > 0
    ma_cac_muc = [m.ma for m in cac_muc]
    assert "TG-01" in ma_cac_muc


def test_cau_hoi_khong_lien_quan_khong_nap_muc_nao() -> None:
    """Kiểm tra câu hỏi hoàn toàn không liên quan thì không nạp bất kỳ mục nào."""
    cau_hoi = "Bầu trời ban ngày có màu xanh hay màu tím?"
    cac_muc = chon_muc_lien_quan(cau_hoi)

    assert len(cac_muc) == 0


def test_khoi_nap_khong_vuot_toi_da_token() -> None:
    """Kiểm tra khối định dạng câu hỏi thường gặp không vượt quá ngân sách token."""
    du_lieu = lay_du_lieu_thuong_gap()
    toi_da_token = du_lieu.gioi_han.toi_da_token
    # Chọn nhiều mục
    tat_ca_muc = du_lieu.muc[:10]
    khoi_dinh_dang = dinh_dang_khoi_thuong_gap(tat_ca_muc, toi_da_token=toi_da_token)

    so_token = dem_token(khoi_dinh_dang)
    assert so_token <= toi_da_token
    assert "## Câu hỏi thường gặp về cách sử dụng trợ lý" in khoi_dinh_dang


def test_hoi_xem_lai_cuoc_tro_chuyen_nap_nhom_lich_su() -> None:
    """Kiểm tra câu hỏi 'làm sao xem lại cuộc trò chuyện cũ' nạp mục thuộc nhóm lich_su."""
    cau_hoi = "làm sao xem lại cuộc trò chuyện cũ"
    cac_muc = chon_muc_lien_quan(cau_hoi)

    assert len(cac_muc) > 0
    cac_nhom = {m.nhom for m in cac_muc}
    assert "lich_su" in cac_nhom
    ma_cac_muc = [m.ma for m in cac_muc]
    assert "TG-13" in ma_cac_muc


@pytest.mark.asyncio
async def test_endpoint_huong_dan_va_thuong_gap_xac_thuc() -> None:
    """Kiểm tra /api/v1/huong-dan và /api/v1/cau-hoi-thuong-gap trả 401 khi thiếu token và 200 với chi_doc."""
    from sqlalchemy import select

    from app.config import cau_hinh
    from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
    from app.core.xac_thuc import lay_nguoi_dung_hien_tai

    # Tạm gỡ override để kiểm tra JWT thật
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)
    cu_xac_thuc_gia = cau_hinh.xac_thuc_gia
    cau_hinh.xac_thuc_gia = False

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Không có token -> 401
            res_hd_no_auth = await client.get("/api/v1/huong-dan")
            assert res_hd_no_auth.status_code == 401

            res_tg_no_auth = await client.get("/api/v1/cau-hoi-thuong-gap")
            assert res_tg_no_auth.status_code == 401

            # 2. Tìm hoặc tạo tài khoản chi_doc trong DB
            maker = lay_sessionmaker_async()
            async with maker() as phien, phien.begin():
                cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == "chi_doc_test@vidu.com")
                nd_db = (await phien.scalars(cau_lenh)).first()
                if nd_db is None:
                    nd_db = NguoiDungModel(
                        email="chi_doc_test@vidu.com",
                        mat_khau_bam=None,
                        ho_ten="Cán bộ chỉ đọc test",
                        vai_tro="chi_doc",
                        bac="free",
                        phong_ban="KinhDoanh",
                        dang_hoat_dong=True,
                    )
                    phien.add(nd_db)
                    await phien.flush()
                user_id = nd_db.id

            nguoi_chi_doc = NguoiDung(
                id=user_id,
                email="chi_doc_test@vidu.com",
                ho_ten="Cán bộ chỉ đọc test",
                vai_tro="chi_doc",
                bac="free",
                phong_ban="KinhDoanh",
            )
            token = tao_access_token(nguoi_chi_doc)
            headers = {"Authorization": f"Bearer {token}"}

            res_hd = await client.get("/api/v1/huong-dan", headers=headers)
            assert res_hd.status_code == 200
            du_lieu_hd = res_hd.json()
            assert "phien_ban" in du_lieu_hd
            assert "noi_dung" in du_lieu_hd
            assert len(du_lieu_hd["noi_dung"]) > 0

            res_tg = await client.get("/api/v1/cau-hoi-thuong-gap", headers=headers)
            assert res_tg.status_code == 200
            du_lieu_tg = res_tg.json()
            assert "phien_ban" in du_lieu_tg
            assert "muc" in du_lieu_tg
            assert len(du_lieu_tg["muc"]) == 20
            muc_dau = du_lieu_tg["muc"][0]
            assert "ma" in muc_dau
            assert "nhom" in muc_dau
            assert "cau_hoi" in muc_dau
            assert "tra_loi" in muc_dau
    finally:
        cau_hinh.xac_thuc_gia = cu_xac_thuc_gia
