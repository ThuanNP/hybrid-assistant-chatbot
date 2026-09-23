"""Bộ kiểm thử xác thực, phân quyền và bảo mật danh tính người dùng (Giai đoạn 5).

Kiểm tra:
1. Đăng nhập sai mật khẩu -> 401 CHUA_XAC_THUC.
2. Email chưa có tài khoản -> 401 CHUA_XAC_THUC (tránh rò rỉ tài khoản tồn tại).
3. Email viết hoa vẫn đăng nhập được (chuẩn hóa email).
4. Mật khẩu lưu trong CSDL dạng băm bcrypt ($2b$).
5. Vai trò chi_doc được xem lịch sử nhưng gửi tin mới trả 403 KHONG_CO_QUYEN.
6. XAC_THUC_GIA=true trong môi trường prod từ chối khởi động (sys.exit).
7. Làm mới token thành công và thu hồi khi đăng xuất.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import cau_hinh
from app.core.csdl import (
    NguoiDungModel,
    lay_sessionmaker_async,
)
from app.core.xac_thuc import (
    NguoiDung,
    bam_mat_khau,
    kiem_tra_an_toan_xac_thuc,
    lay_nguoi_dung_hien_tai,
    tao_access_token,
    xac_minh_mat_khau,
)
from app.main import app


@pytest.fixture(autouse=True)
def xoa_override_xac_thuc() -> Any:
    """Hủy bỏ override mặc định để kiểm thử luồng xác thực và JWT thật."""
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)
    yield
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)


@pytest.fixture
def client_xac_thuc() -> TestClient:
    """TestClient không override xác thực để kiểm thử luồng đăng nhập và JWT thật."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_sai_mat_khau_tra_ve_401(client_xac_thuc: TestClient) -> None:
    """Đăng nhập sai mật khẩu phải trả về 401 CHUA_XAC_THUC."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == "test_sai_mk@vidu.com")
        nd = (await phien.scalars(cau_lenh)).first()
        if nd is None:
            phien.add(
                NguoiDungModel(
                    email="test_sai_mk@vidu.com",
                    mat_khau_bam=bam_mat_khau("MatKhauDung123"),
                    ho_ten="Người dùng kiểm thử",
                    vai_tro="nguoi_dung",
                    bac="free",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
            )

    phan_hoi = client_xac_thuc.post(
        "/api/v1/dang-nhap",
        json={"email": "test_sai_mk@vidu.com", "mat_khau": "MatKhauSai456"},
    )
    assert phan_hoi.status_code == 401
    du_lieu = phan_hoi.json()
    assert du_lieu.get("loi", {}).get("ma") == "CHUA_XAC_THUC"
    assert "X-Ma-Yeu-Cau" in phan_hoi.headers


@pytest.mark.asyncio
async def test_email_chua_ton_tai_tra_ve_401(client_xac_thuc: TestClient) -> None:
    """Tài khoản không tồn tại phải trả cùng mã lỗi 401 để không lộ thông tin."""
    phan_hoi = client_xac_thuc.post(
        "/api/v1/dang-nhap",
        json={"email": "chua_co_tai_khoan_nay@vidu.com", "mat_khau": "BatKy123"},
    )
    assert phan_hoi.status_code == 401
    du_lieu = phan_hoi.json()
    assert du_lieu.get("loi", {}).get("ma") == "CHUA_XAC_THUC"


@pytest.mark.asyncio
async def test_email_viet_hoa_van_dang_nhap_thanh_cong(client_xac_thuc: TestClient) -> None:
    """Email viết hoa hoặc có khoảng trắng hai đầu vẫn được chuẩn hóa và đăng nhập thành công."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == "hoa_thuong@vidu.com")
        nd = (await phien.scalars(cau_lenh)).first()
        if nd is None:
            phien.add(
                NguoiDungModel(
                    email="hoa_thuong@vidu.com",
                    mat_khau_bam=bam_mat_khau("MatKhauChuan123"),
                    ho_ten="Người dùng Hoa Thường",
                    vai_tro="nguoi_dung",
                    bac="free",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
            )

    phan_hoi = client_xac_thuc.post(
        "/api/v1/dang-nhap",
        json={"email": "  HOA_THUONG@VIDU.COM  ", "mat_khau": "MatKhauChuan123"},
    )
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert "access_token" in du_lieu
    assert du_lieu["nguoi_dung"]["email"] == "hoa_thuong@vidu.com"
    # Kiểm tra cookie refresh_token
    assert "refresh_token" in phan_hoi.cookies


@pytest.mark.asyncio
async def test_mat_khau_luu_dang_bam_bcrypt() -> None:
    """Mật khẩu lưu trong cơ sở dữ liệu phải là chuỗi băm bcrypt ($2b$)."""
    mat_khau_tho = "KiemTraBcrypt123@"
    chuoi_bam = bam_mat_khau(mat_khau_tho)

    assert chuoi_bam.startswith("$2b$")
    assert chuoi_bam != mat_khau_tho
    assert xac_minh_mat_khau(mat_khau_tho, chuoi_bam) is True
    assert xac_minh_mat_khau("MatKhauSai", chuoi_bam) is False


@pytest.mark.asyncio
async def test_chi_doc_gui_tin_bi_chan_403(client_xac_thuc: TestClient) -> None:
    """Người dùng có vai trò chi_doc bị cấm gửi tin nhắn mới (403 KHONG_CO_QUYEN)."""
    maker = lay_sessionmaker_async()
    nguoi_id = 0
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == "chi_doc@vidu.com")
        nd = (await phien.scalars(cau_lenh)).first()
        if nd is None:
            nd = NguoiDungModel(
                email="chi_doc@vidu.com",
                mat_khau_bam=bam_mat_khau("MatKhauChiDoc123"),
                ho_ten="Cán bộ chỉ đọc",
                vai_tro="chi_doc",
                bac="free",
                phong_ban="CNTT",
                dang_hoat_dong=True,
            )
            phien.add(nd)
            await phien.flush()
        nguoi_id = nd.id

    nguoi_chi_doc = NguoiDung(
        id=nguoi_id,
        email="chi_doc@vidu.com",
        ho_ten="Cán bộ chỉ đọc",
        vai_tro="chi_doc",
        bac="free",
        phong_ban="CNTT",
    )
    token = tao_access_token(nguoi_chi_doc)

    # 1. Gọi POST /api/v1/chat (không phát dòng)
    phan_hoi = client_xac_thuc.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"noi_dung": "Câu hỏi từ tài khoản chỉ đọc"},
    )
    assert phan_hoi.status_code == 403
    du_lieu = phan_hoi.json()
    assert du_lieu.get("loi", {}).get("ma") == "KHONG_CO_QUYEN"

    # 2. Gọi POST /api/v1/chat/stream (phát dòng)
    phan_hoi_stream = client_xac_thuc.post(
        "/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"noi_dung": "Câu hỏi stream từ tài khoản chỉ đọc"},
    )
    assert phan_hoi_stream.status_code == 403
    du_lieu_stream = phan_hoi_stream.json()
    assert du_lieu_stream.get("loi", {}).get("ma") == "KHONG_CO_QUYEN"


def test_xac_thuc_gia_trong_prod_tu_choi_khoi_dong(monkeypatch: pytest.MonkeyPatch) -> None:
    """XAC_THUC_GIA=true ở MOI_TRUONG=prod bắt buộc gọi sys.exit từ chối khởi động."""
    monkeypatch.setattr(cau_hinh, "moi_truong", "prod")
    monkeypatch.setattr(cau_hinh, "xac_thuc_gia", True)

    with pytest.raises(SystemExit) as thoat:
        kiem_tra_an_toan_xac_thuc()

    assert "XAC_THUC_GIA=true không được phép ở MOI_TRUONG=prod" in str(thoat.value)


@pytest.mark.asyncio
async def test_lam_moi_token_va_dang_xuat(client_xac_thuc: TestClient) -> None:
    """Kiểm tra quy trình đăng nhập -> lấy thông tin /toi -> làm mới token -> đăng xuất."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == "nguoi_dung_vong_doi@vidu.com")
        nd = (await phien.scalars(cau_lenh)).first()
        if nd is None:
            phien.add(
                NguoiDungModel(
                    email="nguoi_dung_vong_doi@vidu.com",
                    mat_khau_bam=bam_mat_khau("MatKhau123456"),
                    ho_ten="Người dùng vòng đời",
                    vai_tro="nguoi_dung",
                    bac="free",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
            )

    # 1. Đăng nhập
    dn = client_xac_thuc.post(
        "/api/v1/dang-nhap",
        json={"email": "nguoi_dung_vong_doi@vidu.com", "mat_khau": "MatKhau123456"},
    )
    assert dn.status_code == 200
    token_goc = dn.json()["access_token"]
    assert "refresh_token" in dn.cookies

    # 2. Truy cập /api/v1/toi bằng Bearer token
    toi = client_xac_thuc.get(
        "/api/v1/toi",
        headers={"Authorization": f"Bearer {token_goc}"},
    )
    assert toi.status_code == 200
    assert toi.json()["email"] == "nguoi_dung_vong_doi@vidu.com"

    # 3. Làm mới token qua cookie
    lm = client_xac_thuc.post("/api/v1/lam-moi-token")
    assert lm.status_code == 200
    token_moi = lm.json()["access_token"]
    assert token_moi != ""

    # 4. Đăng xuất
    dx = client_xac_thuc.post("/api/v1/dang-xuat")
    assert dx.status_code == 200
    assert dx.json()["thanh_cong"] is True

    # 5. Làm mới lại sau khi đã đăng xuất phải thất bại vì phiên đã bị thu hồi
    lm_sau_dx = client_xac_thuc.post("/api/v1/lam-moi-token")
    assert lm_sau_dx.status_code == 401
