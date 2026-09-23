"""Bộ kiểm thử cho cơ chế kiểm soát 4 lớp hạn mức (backend/app/core/han_muc.py).

Kiểm tra:
1. Bốn lớp hoạt động độc lập.
2. Thứ tự kiểm tra đúng: IP bị chặn thì không truy cập CSDL người dùng.
3. Người dùng bậc pro được nhân hệ số HE_SO_BAC_PRO ở hạn mức giờ.
4. Hạn mức ngày: tổng token sinh ra và chi phí đám mây theo bậc từ luot_goi.
5. Tối đa một yêu cầu đang chạy đồng thời cho mỗi người tại một thời điểm (HTTP 429).
6. Luồng lỗi giữa chừng vẫn giải phóng khe an toàn.
7. Ghi nhật ký kiểm toán nhat_ky_kiem_toan mỗi lần vượt hạn mức.
8. GET /api/v1/toi bổ sung đầy đủ các trường hạn mức.
"""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.chat.su_kien_sse import ManhPhatRa
from app.config import cau_hinh
from app.core.csdl import (
    HanMucDemModel,
    LuotGoiModel,
    NguoiDungModel,
    NhatKyKiemToanModel,
    lay_sessionmaker_async,
)
from app.core.han_muc import (
    _CAC_YEU_CAU_DANG_CHAY,
    chiem_khe_yeu_cau,
    giai_phong_khe_yeu_cau,
    kiem_tra_dang_chay,
    lay_ip_yeu_cau,
)
from app.core.xac_thuc import NguoiDung, bam_mat_khau, lay_nguoi_dung_hien_tai
from app.llm.router import KetQuaGoi
from app.main import app


@pytest.fixture(autouse=True)
async def don_dep_khe_va_han_muc() -> AsyncIterator[None]:
    """Dọn sạch danh sách yêu cầu đang chạy và bảng han_muc_dem trước/sau mỗi bài test."""
    _CAC_YEU_CAU_DANG_CHAY.clear()
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        await phien.execute(HanMucDemModel.__table__.delete())
    yield
    _CAC_YEU_CAU_DANG_CHAY.clear()
    async with maker() as phien, phien.begin():
        await phien.execute(HanMucDemModel.__table__.delete())
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)


@pytest.fixture
def client() -> TestClient:
    """Khởi tạo TestClient cho ứng dụng FastAPI."""
    return TestClient(app)


@pytest.fixture
async def nguoi_dung_free() -> AsyncIterator[NguoiDung]:
    """Người dùng bậc free dùng cho kiểm thử, bảo đảm tồn tại trong CSDL."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        nd = await phien.get(NguoiDungModel, 901)
        if nd is None:
            phien.add(
                NguoiDungModel(
                    id=901,
                    email="user_free_901@vidu.com",
                    mat_khau_bam=bam_mat_khau("MatKhau123"),
                    ho_ten="Người dùng Free",
                    vai_tro="nguoi_dung",
                    bac="free",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
            )
    yield NguoiDung(
        id=901,
        email="user_free_901@vidu.com",
        ho_ten="Người dùng Free",
        vai_tro="nguoi_dung",
        bac="free",
        phong_ban="CNTT",
    )


@pytest.fixture
async def nguoi_dung_pro() -> AsyncIterator[NguoiDung]:
    """Người dùng bậc pro dùng cho kiểm thử, bảo đảm tồn tại trong CSDL."""
    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        nd = await phien.get(NguoiDungModel, 902)
        if nd is None:
            phien.add(
                NguoiDungModel(
                    id=902,
                    email="user_pro_902@vidu.com",
                    mat_khau_bam=bam_mat_khau("MatKhau123"),
                    ho_ten="Người dùng Pro",
                    vai_tro="nguoi_dung",
                    bac="pro",
                    phong_ban="CNTT",
                    dang_hoat_dong=True,
                )
            )
    yield NguoiDung(
        id=902,
        email="user_pro_902@vidu.com",
        ho_ten="Người dùng Pro",
        vai_tro="nguoi_dung",
        bac="pro",
        phong_ban="CNTT",
    )


@pytest.mark.asyncio
async def test_lop_a_theo_ip_chua_xac_thuc_va_dang_nhap(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lớp a: Địa chỉ IP gửi quá HAN_MUC_IP_PHUT bị chặn 429 tại /dang-nhap."""
    monkeypatch.setattr(cau_hinh, "han_muc_ip_phut", 3)
    ip_test = "192.0.2.1"
    headers = {"x-forwarded-for": ip_test}

    # 3 yêu cầu đầu tiên chạm hạn mức
    for _ in range(3):
        phan_hoi = client.post(
            "/api/v1/dang-nhap",
            json={"email": "sai@vidu.com", "mat_khau": "sai"},
            headers=headers,
        )
        assert phan_hoi.status_code == 401

    # Yêu cầu thứ 4 bị chặn bởi Lớp a
    phan_hoi_4 = client.post(
        "/api/v1/dang-nhap",
        json={"email": "sai@vidu.com", "mat_khau": "sai"},
        headers=headers,
    )
    assert phan_hoi_4.status_code == 429
    du_lieu = phan_hoi_4.json()
    assert du_lieu.get("loi", {}).get("ma") == "VUOT_HAN_MUC"
    assert "Retry-After" in phan_hoi_4.headers
    assert int(phan_hoi_4.headers["Retry-After"]) > 0


@pytest.mark.asyncio
async def test_thu_tu_kiem_tra_ip_bi_chan_khong_truy_cap_nguoi_dung(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thứ tự kiểm tra: IP bị chặn trước thì KHÔNG được truy vấn CSDL người dùng."""
    monkeypatch.setattr(cau_hinh, "han_muc_ip_phut", 1)
    ip_test = "192.0.2.2"
    headers = {"x-forwarded-for": ip_test}

    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free

    # Lượt 1 thành công
    with (
        patch("app.main.goi_mo_hinh", new_callable=AsyncMock) as mock_goi,
        patch("app.main.kiem_duyet_dau_vao", new_callable=AsyncMock) as mock_kd,
        patch("app.main.kiem_duyet_dau_ra", new_callable=AsyncMock) as mock_kdr,
    ):
        mock_kd.return_value.cho_qua = True
        mock_kd.return_value.noi_dung_thay_the = None
        mock_kdr.return_value.cho_qua = True
        mock_kdr.return_value.noi_dung_thay_the = None
        mock_goi.return_value = KetQuaGoi(
            noi_dung="Chào bạn",
            nguon="local",
            tang=0,
            ten_model="qwen3.5:9b-q4_K_M",
            token_vao=5,
            token_ra=5,
            chi_phi_usd=0.0,
            do_tre_ms=10.0,
            toc_do_tok_s=20.0,
        )
        res1 = client.post("/api/v1/chat", json={"noi_dung": "xin chào"}, headers=headers)
        assert res1.status_code == 200

    # Lượt 2 IP bị chặn ngay ở lớp a; mock hàm kiểm tra lớp b để chứng minh không bị gọi tới
    with patch("app.core.han_muc.kiem_tra_han_muc_nguoi_gio", new_callable=AsyncMock) as mock_b:
        res2 = client.post("/api/v1/chat", json={"noi_dung": "xin chào tiếp"}, headers=headers)
        assert res2.status_code == 429
        assert res2.json()["loi"]["ma"] == "VUOT_HAN_MUC"
        assert mock_b.call_count == 0


@pytest.mark.asyncio
async def test_lop_b_theo_nguoi_dung_gio_va_he_so_pro(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
    nguoi_dung_pro: NguoiDung,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lớp b: Hạn mức theo giờ của bậc pro được nhân hệ số HE_SO_BAC_PRO."""
    monkeypatch.setattr(cau_hinh, "han_muc_ip_phut", 100)
    monkeypatch.setattr(cau_hinh, "han_muc_moi_nguoi_gio", 2)
    monkeypatch.setattr(cau_hinh, "he_so_bac_pro", 2.0)  # Free: 2, Pro: 4

    maker = lay_sessionmaker_async()
    bay_gio = datetime.now(timezone.utc)

    # 1. Ghi sẵn 2 lượt cho free user và 2 lượt cho pro user trong bảng han_muc_dem
    async with maker() as phien, phien.begin():
        phien.add(HanMucDemModel(khoa=f"user:{nguoi_dung_free.id}", thoi_diem=bay_gio))
        phien.add(HanMucDemModel(khoa=f"user:{nguoi_dung_free.id}", thoi_diem=bay_gio))
        phien.add(HanMucDemModel(khoa=f"user:{nguoi_dung_pro.id}", thoi_diem=bay_gio))
        phien.add(HanMucDemModel(khoa=f"user:{nguoi_dung_pro.id}", thoi_diem=bay_gio))

    # Free user đã dùng 2/2 -> lượt 3 bị 429
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free
    res_free = client.post("/api/v1/chat", json={"noi_dung": "câu hỏi free"})
    assert res_free.status_code == 429
    assert "dùng hết 2 lượt hỏi trong giờ này" in res_free.json()["loi"]["thong_diep"]

    # Pro user đã dùng 2/4 -> lượt 3 vẫn được thông qua (hạn mức 4)
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_pro
    with (
        patch("app.main.goi_mo_hinh", new_callable=AsyncMock) as mock_goi,
        patch("app.main.kiem_duyet_dau_vao", new_callable=AsyncMock) as mock_kd,
        patch("app.main.kiem_duyet_dau_ra", new_callable=AsyncMock) as mock_kdr,
    ):
        mock_kd.return_value.cho_qua = True
        mock_kd.return_value.noi_dung_thay_the = None
        mock_kdr.return_value.cho_qua = True
        mock_kdr.return_value.noi_dung_thay_the = None
        mock_goi.return_value = KetQuaGoi(
            noi_dung="Trả lời pro",
            nguon="local",
            tang=0,
            ten_model="qwen3.5:9b-q4_K_M",
            token_vao=5,
            token_ra=5,
            chi_phi_usd=0.0,
            do_tre_ms=10.0,
            toc_do_tok_s=20.0,
        )
        res_pro = client.post("/api/v1/chat", json={"noi_dung": "câu hỏi pro"})
        assert res_pro.status_code == 200


@pytest.mark.asyncio
async def test_lop_c_theo_ngay_token_va_chi_phi(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lớp c: Vượt tổng token ngày hoặc chi phí đám mây theo bậc sẽ bị 429."""
    monkeypatch.setattr(cau_hinh, "han_muc_ip_phut", 100)
    monkeypatch.setattr(cau_hinh, "han_muc_moi_nguoi_gio", 100)
    monkeypatch.setattr(cau_hinh, "han_muc_token_ngay", 1000)
    monkeypatch.setattr(cau_hinh, "han_muc_chi_phi_ngay_free_usd", 0.05)

    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free
    maker = lay_sessionmaker_async()
    bay_gio = datetime.now(timezone.utc)

    # 1. Ghi nhận lượt gọi vượt token ngày
    async with maker() as phien, phien.begin():
        phien.add(
            LuotGoiModel(
                nguoi_id=str(nguoi_dung_free.id),
                nguon="local",
                tang=0,
                model="qwen3.5:9b-q4_K_M",
                token_vao=100,
                token_ra=1500,  # Vượt 1000
                chi_phi_usd=0.0,
                thoi_diem=bay_gio,
                thanh_cong=True,
                ma_yeu_cau="yc_token_over",
            )
        )

    res_token = client.post("/api/v1/chat", json={"noi_dung": "hỏi token"})
    assert res_token.status_code == 429
    assert "token sinh ra trong ngày hôm nay" in res_token.json()["loi"]["thong_diep"]

    # 2. Xóa lượt gọi cũ, thêm lượt gọi vượt chi phí
    async with maker() as phien, phien.begin():
        await phien.execute(
            select(LuotGoiModel).where(LuotGoiModel.nguoi_id == str(nguoi_dung_free.id))
        )
        cau_lenh_xoa = LuotGoiModel.__table__.delete().where(
            LuotGoiModel.nguoi_id == str(nguoi_dung_free.id)
        )
        await phien.execute(cau_lenh_xoa)

        phien.add(
            LuotGoiModel(
                nguoi_id=str(nguoi_dung_free.id),
                nguon="dam_may",
                tang=1,
                model="gemini-2.5-flash",
                token_vao=100,
                token_ra=200,
                chi_phi_usd=0.10,  # Vượt 0.05
                thoi_diem=bay_gio,
                thanh_cong=True,
                ma_yeu_cau="yc_cost_over",
            )
        )

    res_cost = client.post("/api/v1/chat", json={"noi_dung": "hỏi chi phí"})
    assert res_cost.status_code == 429
    assert "chi phí đám mây" in res_cost.json()["loi"]["thong_diep"]


@pytest.mark.asyncio
async def test_lop_d_toi_da_mot_yeu_cau_dong_thoi(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
) -> None:
    """Lớp d: Người dùng đang có một yêu cầu chạy thì yêu cầu thứ hai bị 429 ngay lập tức."""
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free

    # Giả lập yêu cầu 1 đang chiếm khe
    await chiem_khe_yeu_cau(nguoi_dung_free.id, "yc_dang_chay_1")
    assert kiem_tra_dang_chay(nguoi_dung_free.id) is True

    # Yêu cầu 2 gửi đến -> Bị từ chối 429
    res = client.post("/api/v1/chat", json={"noi_dung": "câu hỏi tab 2"})
    assert res.status_code == 429
    assert "đang có một yêu cầu khác đang được xử lý" in res.json()["loi"]["thong_diep"]
    assert res.headers.get("Retry-After") == "5"

    # Giải phóng khe yêu cầu 1
    await giai_phong_khe_yeu_cau(nguoi_dung_free.id)
    assert kiem_tra_dang_chay(nguoi_dung_free.id) is False

    # Yêu cầu tiếp theo được tiếp nhận
    with (
        patch("app.main.goi_mo_hinh", new_callable=AsyncMock) as mock_goi,
        patch("app.main.kiem_duyet_dau_vao", new_callable=AsyncMock) as mock_kd,
        patch("app.main.kiem_duyet_dau_ra", new_callable=AsyncMock) as mock_kdr,
    ):
        mock_kd.return_value.cho_qua = True
        mock_kd.return_value.noi_dung_thay_the = None
        mock_kdr.return_value.cho_qua = True
        mock_kdr.return_value.noi_dung_thay_the = None
        mock_goi.return_value = KetQuaGoi(
            noi_dung="Chào bạn",
            nguon="local",
            tang=0,
            ten_model="qwen3.5:9b-q4_K_M",
            token_vao=5,
            token_ra=5,
            chi_phi_usd=0.0,
            do_tre_ms=10.0,
            toc_do_tok_s=20.0,
        )
        res_ok = client.post("/api/v1/chat", json={"noi_dung": "câu hỏi sau khi giải phóng"})
        assert res_ok.status_code == 200


@pytest.mark.asyncio
async def test_luong_loi_giua_chung_van_giai_phong_khe(
    nguoi_dung_free: NguoiDung,
) -> None:
    """Luồng xử lý gặp ngoại lệ bất ngờ vẫn phải giải phóng khe trong finally."""
    client_safe = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free

    with (
        patch("app.main.goi_mo_hinh", side_effect=RuntimeError("Mô hình gặp sự cố")),
        patch("app.main.kiem_duyet_dau_vao", new_callable=AsyncMock) as mock_kd,
    ):
        mock_kd.return_value.cho_qua = True
        mock_kd.return_value.noi_dung_thay_the = None
        res = client_safe.post("/api/v1/chat", json={"noi_dung": "câu hỏi lỗi"})
        assert res.status_code == 500

    # Khe phải được giải phóng
    assert kiem_tra_dang_chay(nguoi_dung_free.id) is False


@pytest.mark.asyncio
async def test_luong_stream_giai_phong_khe_khi_xong(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
) -> None:
    """Luồng SSE stream chiếm khe và giải phóng khi kết thúc luồng."""
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free

    khe_da_chiem_khi_stream = False

    async def _mock_stream(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        nonlocal khe_da_chiem_khi_stream
        khe_da_chiem_khi_stream = kiem_tra_dang_chay(nguoi_dung_free.id)
        yield ManhPhatRa(loai="bat_dau", nguon="local", tang=0, ten_model="qwen3.5:9b-q4_K_M")
        yield ManhPhatRa(loai="manh", noi_dung="Xin chào")
        yield ManhPhatRa(loai="xong", ten_model="qwen3.5:9b-q4_K_M")

    with (
        patch("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", side_effect=_mock_stream),
        patch("app.chat.su_kien_sse.kiem_duyet_dau_vao", new_callable=AsyncMock) as mock_kd,
        patch("app.chat.su_kien_sse.kiem_duyet_dau_ra", new_callable=AsyncMock) as mock_kdr,
    ):
        mock_kd.return_value.cho_qua = True
        mock_kd.return_value.noi_dung_thay_the = None
        mock_kdr.return_value.cho_qua = True
        mock_kdr.return_value.noi_dung_thay_the = None

        with client.stream("POST", "/api/v1/chat/stream", json={"noi_dung": "alo"}) as res:
            assert res.status_code == 200
            for _ in res.iter_lines():
                pass

    # Trong khi stream chạy thì khe đã được chiếm
    assert khe_da_chiem_khi_stream is True
    # Sau khi đọc xong stream, khe đã được giải phóng
    assert kiem_tra_dang_chay(nguoi_dung_free.id) is False


@pytest.mark.asyncio
async def test_ghi_nhat_ky_kiem_toan_khi_vuot_han_muc(
    client: TestClient,
    nguoi_dung_free: NguoiDung,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mỗi lần vượt hạn mức đều ghi một bản ghi vào nhat_ky_kiem_toan."""
    monkeypatch.setattr(cau_hinh, "han_muc_ip_phut", 100)
    monkeypatch.setattr(cau_hinh, "han_muc_moi_nguoi_gio", 1)

    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_free
    maker = lay_sessionmaker_async()
    bay_gio = datetime.now(timezone.utc)

    async with maker() as phien, phien.begin():
        phien.add(HanMucDemModel(khoa=f"user:{nguoi_dung_free.id}", thoi_diem=bay_gio))

    # Gửi yêu cầu thứ 2 để kích hoạt vượt hạn mức giờ
    res = client.post("/api/v1/chat", json={"noi_dung": "test audit"})
    assert res.status_code == 429
    ma_yc = res.headers.get("X-Ma-Yeu-Cau", "")

    # Kiểm tra bản ghi kiểm toán trong CSDL
    async with maker() as phien:
        cau_lenh = (
            select(NhatKyKiemToanModel)
            .where(
                NhatKyKiemToanModel.nguoi_id == nguoi_dung_free.id,
                NhatKyKiemToanModel.hanh_dong == "vuot_han_muc",
            )
            .order_by(NhatKyKiemToanModel.id.desc())
        )
        kiem_toan = (await phien.scalars(cau_lenh)).first()
        assert kiem_toan is not None
        assert kiem_toan.chi_tiet is not None
        assert kiem_toan.chi_tiet.get("loai") == "nguoi_dung_gio"
        assert kiem_toan.ma_yeu_cau == ma_yc


@pytest.mark.asyncio
async def test_get_toi_bo_sung_du_lieu_han_muc(
    client: TestClient,
    nguoi_dung_pro: NguoiDung,
) -> None:
    """GET /api/v1/toi trả về đầy đủ các trường hạn mức mới."""
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: nguoi_dung_pro
    maker = lay_sessionmaker_async()

    # Đảm bảo tài khoản tồn tại trong bảng nguoi_dung
    async with maker() as phien, phien.begin():
        nd = await phien.get(NguoiDungModel, nguoi_dung_pro.id)
        if nd is None:
            phien.add(
                NguoiDungModel(
                    id=nguoi_dung_pro.id,
                    email=nguoi_dung_pro.email,
                    mat_khau_bam=bam_mat_khau("MatKhau123"),
                    ho_ten=nguoi_dung_pro.ho_ten,
                    vai_tro=nguoi_dung_pro.vai_tro,
                    bac=nguoi_dung_pro.bac,
                    phong_ban=nguoi_dung_pro.phong_ban,
                    dang_hoat_dong=True,
                )
            )

    res = client.get("/api/v1/toi")
    assert res.status_code == 200
    du_lieu = res.json()

    assert du_lieu["bac"] == "pro"
    assert "da_dung_trong_gio" in du_lieu
    assert "token_da_sinh_hom_nay" in du_lieu
    assert "chi_phi_hom_nay_usd" in du_lieu
    assert "han_muc_con_lai" in du_lieu
    assert "dang_chay" in du_lieu
    assert du_lieu["dang_chay"] is False


def _yeu_cau_gia(ip_ket_noi: str, headers: dict[str, str]) -> Request:
    """Dựng Request tối giản với địa chỉ kết nối trực tiếp và tiêu đề cho trước."""
    return Request(
        {
            "type": "http",
            "client": (ip_ket_noi, 50000),
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        }
    )


def test_ip_bo_qua_tieu_de_proxy_tu_client_truc_tiep() -> None:
    """Client kết nối thẳng từ ngoài không tự đổi được IP hạn mức bằng tiêu đề proxy."""
    yc = _yeu_cau_gia("8.8.4.4", {"x-forwarded-for": "1.2.3.4", "x-real-ip": "5.6.7.8"})
    assert lay_ip_yeu_cau(yc) == "8.8.4.4"


def test_ip_qua_proxy_noi_bo_dung_x_real_ip_va_phan_tu_cuoi() -> None:
    """Qua nginx nội bộ: ưu tiên X-Real-IP, sau đó phần tử cuối của X-Forwarded-For."""
    assert lay_ip_yeu_cau(_yeu_cau_gia("172.18.0.3", {"x-real-ip": "192.168.1.20"})) == (
        "192.168.1.20"
    )
    yc = _yeu_cau_gia("172.18.0.3", {"x-forwarded-for": "1.2.3.4, 192.168.1.21"})
    assert lay_ip_yeu_cau(yc) == "192.168.1.21"
