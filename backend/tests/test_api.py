"""Bộ kiểm thử tích hợp và kiểm thử đơn vị cho toàn bộ API backend/app/main.py.

Bảo đảm:
1. /health trả nhanh kể cả khi cơ sở dữ liệu hỏng.
2. /ready trả 503 khi CSDL hoặc mô hình gặp sự cố, không lộ chi tiết thành phần.
3. /ready không gọi sinh văn bản (đếm lời gọi giả lập = 0).
4. GET /api/v1/hoi-thoai/{id} của người khác trả 404 KHONG_TIM_THAY.
5. Mọi lỗi có ma_yeu_cau và tuyệt đối không chứa chữ "Traceback".
6. Hai móc kiểm duyệt (kiem_duyet_dau_vao, kiem_duyet_dau_ra) được gọi đúng một lần mỗi yêu cầu.
7. Xóa mềm hội thoại thành công và loại bỏ khỏi danh sách hoạt động.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.chat.su_kien_sse as sse_mod
import app.llm.router as router_mod
import app.main as main_mod
from app.chat.su_kien_sse import ManhPhatRa
from app.config import cau_hinh
from app.core.bao_mat import KetQuaKiemDuyet
from app.core.csdl import HoiThoaiModel, NguoiDungModel, lay_sessionmaker_async
from app.core.loi import (
    BANG_ANH_XA_LOI,
    LoiDauVao,
    LoiVuotNganSach,
    chuyen_doi_loi_sang_loi_ung_dung,
)
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import BoChayOllama
from app.llm.router import KetQuaGoi
from app.main import _kiem_tra_cors_prod, app


@pytest.fixture
def client_api() -> TestClient:
    """Fixture cung cấp TestClient chuẩn cho ứng dụng FastAPI."""
    return TestClient(app)


def test_health_nhanh_khi_csdl_hong(
    monkeypatch: pytest.MonkeyPatch, client_api: TestClient
) -> None:
    """/health chỉ kiểm tra tiến trình sống, trả 200 ngay cả khi CSDL hỏng hoàn toàn."""

    def _csdl_hong() -> None:
        raise ConnectionRefusedError("Không thể kết nối PostgreSQL")

    monkeypatch.setattr(main_mod, "lay_sessionmaker_async", _csdl_hong)
    phan_hoi = client_api.get("/health")
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert du_lieu["trang_thai"] in ("song", "healthy")
    assert "phien_ban" in du_lieu


def test_ready_tra_200_khi_du_thanh_phan(
    monkeypatch: pytest.MonkeyPatch, client_api: TestClient
) -> None:
    """/ready trả 200 và nêu tình trạng db, bo_chay, dam_may khi mọi thành phần hoạt động."""

    async def _liet_ke_model_gia(self: BoChayOllama) -> list[str]:
        return ["qwen2.5:14b-instruct-q4_K_M"]

    monkeypatch.setattr(BoChayOllama, "liet_ke_model", _liet_ke_model_gia)
    phan_hoi = client_api.get("/ready")
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert du_lieu["trang_thai"] in ("san_sang", "ready")
    assert du_lieu["thanh_phan"]["db"] in ("ok", "up")
    assert du_lieu["thanh_phan"]["bo_chay"] in ("ok", "up")
    assert du_lieu["thanh_phan"]["dam_may"] in ("ok", "hong", "up", "down")


def test_ready_tra_503_khi_csdl_hong(
    monkeypatch: pytest.MonkeyPatch, client_api: TestClient
) -> None:
    """/ready trả 503 khi mất kết nối CSDL và nêu rõ thành phần db hỏng."""

    def _maker_hong() -> Any:
        class _PhienHong:
            async def __aenter__(self) -> None:
                raise ConnectionRefusedError("CSDL sập")

            async def __aexit__(self, *args: object) -> None:
                pass

        return _PhienHong

    monkeypatch.setattr(main_mod, "lay_sessionmaker_async", _maker_hong)
    phan_hoi = client_api.get("/ready")
    assert phan_hoi.status_code == 503
    du_lieu = phan_hoi.json()
    assert du_lieu["trang_thai"] in ("chua_san_sang", "not_ready")
    assert du_lieu["thanh_phan"]["db"] in ("hong", "down")


def test_ready_tra_503_khi_ca_bo_chay_va_dam_may_hong(
    monkeypatch: pytest.MonkeyPatch, client_api: TestClient
) -> None:
    """/ready trả 503 khi CSDL ok nhưng cả bộ chạy local và toàn bộ đám mây đều hỏng."""

    async def _liet_ke_that_bai(self: BoChayOllama) -> list[str]:
        raise TimeoutError("Bộ chạy quá thời gian 2 giây")

    monkeypatch.setattr(BoChayOllama, "liet_ke_model", _liet_ke_that_bai)

    # Giả lập toàn bộ tầng đám mây đều không khả dụng
    danh_sach_tam = []
    for t in cau_hinh.chuoi_dam_may:
        ban_sao = t.model_copy()
        ban_sao.kha_dung = False
        danh_sach_tam.append(ban_sao)
    monkeypatch.setattr(cau_hinh, "chuoi_dam_may", danh_sach_tam)

    phan_hoi = client_api.get("/ready")
    assert phan_hoi.status_code == 503
    du_lieu = phan_hoi.json()
    assert du_lieu["trang_thai"] in ("chua_san_sang", "not_ready")
    assert du_lieu["thanh_phan"]["bo_chay"] in ("hong", "down")
    assert du_lieu["thanh_phan"]["dam_may"] in ("hong", "down")


def test_ready_khong_goi_sinh_van_ban(
    monkeypatch: pytest.MonkeyPatch, client_api: TestClient
) -> None:
    """/ready chỉ gọi liet_ke_model(), tuyệt đối KHÔNG gọi bất kỳ hàm sinh văn bản nào."""
    dem_goi = {"sinh_van_ban": 0, "liet_ke": 0}

    async def _liet_ke_model_dem(self: BoChayOllama) -> list[str]:
        dem_goi["liet_ke"] += 1
        return ["qwen2.5:14b-instruct-q4_K_M"]

    async def _goi_mo_hinh_cam(*args: Any, **kwargs: Any) -> Any:
        dem_goi["sinh_van_ban"] += 1
        raise AssertionError("CẤM gọi goi_mo_hinh trong /ready")

    monkeypatch.setattr(BoChayOllama, "liet_ke_model", _liet_ke_model_dem)
    monkeypatch.setattr(router_mod, "goi_mo_hinh", _goi_mo_hinh_cam)
    monkeypatch.setattr(router_mod, "goi_mo_hinh_theo_dong", _goi_mo_hinh_cam)
    monkeypatch.setattr(main_mod, "goi_mo_hinh", _goi_mo_hinh_cam)

    phan_hoi = client_api.get("/ready")
    assert phan_hoi.status_code in (200, 503)
    assert dem_goi["liet_ke"] >= 1
    assert dem_goi["sinh_van_ban"] == 0, (
        "Không được phép gọi sinh văn bản khi kiểm tra /ready"
    )


@pytest.mark.asyncio
async def test_get_hoi_thoai_nguoi_khac_tra_404(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
    client_api: TestClient,
) -> None:
    """GET /api/v1/hoi-thoai/{id} của người dùng khác bắt buộc trả 404 KHONG_TIM_THAY."""
    # Đảm bảo người dùng khác (id=9999) tồn tại trong CSDL trước khi gán khoá ngoại
    nd_9999 = await phien_csdl.get(NguoiDungModel, 9999)
    if nd_9999 is None:
        nd_9999 = NguoiDungModel(
            id=9999,
            ten_dang_nhap="can_bo_9999",
            ho_ten="Cán bộ phòng ban khác",
            vai_tro="nguoi_dung",
            bac="chinh",
            phong_ban="KinhDoanh",
            dang_hoat_dong=True,
        )
        phien_csdl.add(nd_9999)
        await phien_csdl.flush()

    # Tạo hoặc cập nhật cuộc hội thoại thuộc người dùng khác (id=9999 khác nguoi_dung_test.id=1)
    ht_nguoi_khac = await phien_csdl.get(HoiThoaiModel, 8888)
    if ht_nguoi_khac is None:
        ht_nguoi_khac = HoiThoaiModel(
            id=8888,
            nguoi_id=9999,
            tieu_de="Cuộc trò chuyện bí mật người khác",
            da_xoa=False,
        )
        phien_csdl.add(ht_nguoi_khac)
    else:
        ht_nguoi_khac.nguoi_id = 9999
        ht_nguoi_khac.da_xoa = False
    await phien_csdl.commit()

    phan_hoi = client_api.get("/api/v1/hoi-thoai/8888")
    assert phan_hoi.status_code == 404
    du_lieu = phan_hoi.json()
    assert "loi" in du_lieu
    assert du_lieu["loi"]["ma"] == "KHONG_TIM_THAY"
    assert "ma_yeu_cau" in du_lieu["loi"]
    assert len(du_lieu["loi"]["ma_yeu_cau"]) > 0
    assert "Traceback" not in phan_hoi.text


def test_moi_loi_co_ma_yeu_cau_va_khong_co_traceback(client_api: TestClient) -> None:
    """Mọi lỗi trả về có ma_yeu_cau, đúng định dạng JSON và tuyệt đối không chứa chữ Traceback."""
    # 1. Truy vấn hội thoại không tồn tại
    res_404 = client_api.get("/api/v1/hoi-thoai/999999")
    assert res_404.status_code == 404
    d_404 = res_404.json()
    assert "loi" in d_404
    assert d_404["loi"]["ma"] == "KHONG_TIM_THAY"
    assert "ma_yeu_cau" in d_404["loi"]
    assert res_404.headers.get("X-Ma-Yeu-Cau") == d_404["loi"]["ma_yeu_cau"]
    assert "Traceback" not in res_404.text

    # 2. Gửi dữ liệu không hợp lệ vào POST /api/v1/chat
    res_422 = client_api.post("/api/v1/chat", json={})
    assert res_422.status_code == 422
    d_422 = res_422.json()
    assert "loi" in d_422
    assert d_422["loi"]["ma"] == "DAU_VAO_KHONG_HOP_LE"
    assert "noi_dung" in d_422["loi"]["thong_diep"]
    assert "ma_yeu_cau" in d_422["loi"]
    assert res_422.headers.get("X-Ma-Yeu-Cau") == d_422["loi"]["ma_yeu_cau"]
    assert "Traceback" not in res_422.text


@pytest.mark.asyncio
async def test_hai_moc_kiem_duyet_duoc_goi_dung_mot_lan_chat(
    monkeypatch: pytest.MonkeyPatch,
    client_api: TestClient,
    nguoi_dung_test: NguoiDung,
) -> None:
    """Hai móc kiểm duyệt được gọi đúng một lần mỗi yêu cầu trong luồng /api/v1/chat."""
    dem_kiem_duyet = {"vao": 0, "ra": 0}

    async def _kd_vao_dem(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        dem_kiem_duyet["vao"] += 1
        return KetQuaKiemDuyet(cho_qua=True)

    async def _kd_ra_dem(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        dem_kiem_duyet["ra"] += 1
        return KetQuaKiemDuyet(cho_qua=True)

    monkeypatch.setattr(main_mod, "kiem_duyet_dau_vao", _kd_vao_dem)
    monkeypatch.setattr(main_mod, "kiem_duyet_dau_ra", _kd_ra_dem)

    async def _goi_mo_hinh_gia(*args: Any, **kwargs: Any) -> KetQuaGoi:
        return KetQuaGoi(
            noi_dung="Chào đồng chí cán bộ ngành điện.",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen2.5:14b-instruct-q4_K_M",
            token_vao=15,
            token_ra=10,
            chi_phi_usd=0.0,
            do_tre_ms=120.0,
            toc_do_tok_s=25.0,
            thoi_gian_nap_ms=10.0,
        )

    monkeypatch.setattr(main_mod, "goi_mo_hinh", _goi_mo_hinh_gia)

    phan_hoi = client_api.post(
        "/api/v1/chat",
        json={"noi_dung": "Quy trình kiểm tra trạm biến áp?"},
    )
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert "nhan_ai" in du_lieu
    assert du_lieu["model"] == "qwen2.5:14b-instruct-q4_K_M"
    assert dem_kiem_duyet["vao"] == 1, "Móc kiểm duyệt đầu vào phải được gọi đúng 1 lần"
    assert dem_kiem_duyet["ra"] == 1, "Móc kiểm duyệt đầu ra phải được gọi đúng 1 lần"


@pytest.mark.asyncio
async def test_hai_moc_kiem_duyet_duoc_goi_dung_mot_lan_stream(
    monkeypatch: pytest.MonkeyPatch,
    client_api: TestClient,
    nguoi_dung_test: NguoiDung,
) -> None:
    """Hai móc kiểm duyệt được gọi đúng một lần mỗi yêu cầu trong luồng /api/v1/chat/stream."""
    dem_kiem_duyet = {"vao": 0, "ra": 0}

    async def _kd_vao_dem(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        dem_kiem_duyet["vao"] += 1
        return KetQuaKiemDuyet(cho_qua=True)

    async def _kd_ra_dem(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        dem_kiem_duyet["ra"] += 1
        return KetQuaKiemDuyet(cho_qua=True)

    monkeypatch.setattr(sse_mod, "kiem_duyet_dau_vao", _kd_vao_dem)
    monkeypatch.setattr(sse_mod, "kiem_duyet_dau_ra", _kd_ra_dem)

    async def _goi_theo_dong_gia(
        *args: Any, **kwargs: Any
    ) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(loai="bat_dau", nguon="local", tang=0, ten_model="qwen2.5:14b")
        yield ManhPhatRa(loai="manh", noi_dung="Xin chào ")
        yield ManhPhatRa(loai="manh", noi_dung="đồng chí.")
        yield ManhPhatRa(
            loai="xong",
            ket_qua=KetQuaGoi(
                noi_dung="Xin chào đồng chí.",
                nguon="local",
                tang=0,
                ten_model="qwen2.5:14b",
                token_vao=5,
                token_ra=5,
            ),
        )

    monkeypatch.setattr(sse_mod, "goi_mo_hinh_theo_dong", _goi_theo_dong_gia)

    phan_hoi = client_api.post(
        "/api/v1/chat/stream",
        json={"noi_dung": "Xin chào hệ thống trợ lý"},
    )
    assert phan_hoi.status_code == 200
    noi_dung_stream = phan_hoi.text
    assert "event: bat_dau" in noi_dung_stream
    assert "event: xong" in noi_dung_stream
    assert dem_kiem_duyet["vao"] == 1, (
        "Móc kiểm duyệt đầu vào trong SSE phải gọi đúng 1 lần"
    )
    assert dem_kiem_duyet["ra"] == 1, (
        "Móc kiểm duyệt đầu ra trong SSE phải gọi đúng 1 lần"
    )


@pytest.mark.asyncio
async def test_xoa_mem_cuoc_hoi_thoai(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
    client_api: TestClient,
) -> None:
    """DELETE /api/v1/hoi-thoai/{id} thực hiện xoá mềm, GET lại sau đó trả 404."""
    # 1. Tạo cuộc hội thoại thuộc người dùng test
    ht = HoiThoaiModel(
        nguoi_id=nguoi_dung_test.id,
        tieu_de="Hội thoại cần xoá mềm",
        da_xoa=False,
    )
    phien_csdl.add(ht)
    await phien_csdl.commit()
    ht_id = ht.id

    # 2. Gọi API xoá mềm
    res_xoa = client_api.delete(f"/api/v1/hoi-thoai/{ht_id}")
    assert res_xoa.status_code == 200
    assert res_xoa.json()["thanh_cong"] is True

    # 3. Kiểm tra trong CSDL cờ da_xoa đã chuyển thành True
    phien_moi = lay_sessionmaker_async()()
    async with phien_moi:
        ban_ghi = await phien_moi.get(HoiThoaiModel, ht_id)
        assert ban_ghi is not None
        assert ban_ghi.da_xoa is True

    # 4. GET lại phải nhận 404 KHONG_TIM_THAY
    res_get = client_api.get(f"/api/v1/hoi-thoai/{ht_id}")
    assert res_get.status_code == 404
    assert res_get.json()["loi"]["ma"] == "KHONG_TIM_THAY"


def test_danh_sach_hoi_thoai_phan_trang(client_api: TestClient) -> None:
    """GET /api/v1/hoi-thoai trả danh sách phân trang với cấu trúc chuẩn."""
    phan_hoi = client_api.get("/api/v1/hoi-thoai?trang=1&kich_thuoc=5")
    assert phan_hoi.status_code == 200
    du_lieu = phan_hoi.json()
    assert "danh_sach" in du_lieu
    assert "tong_so" in du_lieu
    assert du_lieu["trang"] == 1
    assert du_lieu["kich_thuoc"] == 5


def test_cac_endpoint_thong_tin(client_api: TestClient) -> None:
    """Kiểm tra các endpoint thông tin: chi-phi, models, hang-doi, ngu-canh."""
    # 1. /api/v1/models (tuyệt đối không trả khoá)
    res_models = client_api.get("/api/v1/models")
    assert res_models.status_code == 200
    d_models = res_models.json()
    assert "che_do_dinh_tuyen" in d_models
    assert "ho_so_gpu" in d_models
    assert "bac_local" in d_models
    assert "chuoi_dam_may" in d_models
    van_ban_models = res_models.text.lower()
    assert "api_key" not in van_ban_models
    assert "secret" not in van_ban_models

    # 2. /api/v1/hang-doi/tinh-trang
    res_hang_doi = client_api.get("/api/v1/hang-doi/tinh-trang")
    assert res_hang_doi.status_code == 200
    d_hd = res_hang_doi.json()
    assert "dang_chay" in d_hd
    assert "dang_cho" in d_hd

    # 3. /api/v1/ngu-canh/tinh-trang
    res_ngu_canh = client_api.get("/api/v1/ngu-canh/tinh-trang")
    assert res_ngu_canh.status_code == 200
    d_nc = res_ngu_canh.json()
    assert "bac_local" in d_nc
    assert "ngan_sach_token" in d_nc
    assert "so_luot_trung_binh_giu_duoc" in d_nc

    # 4. /api/v1/chi-phi
    res_chi_phi = client_api.get("/api/v1/chi-phi")
    assert res_chi_phi.status_code == 200
    d_cp = res_chi_phi.json()
    assert "chi_phi_hom_nay_usd" in d_cp
    assert "ngan_sach_ngay_usd" in d_cp


def test_thong_diep_noi_bo_khong_lo_ra_nguoi_dung() -> None:
    """Thông điệp nội bộ của ngoại lệ (lỗi thô bộ chạy, chi phí) được thay bằng câu chuẩn."""
    loi_bo_chay = LoiDauVao("Lỗi client từ bộ chạy (400): model 'x' not found")
    loi_ngan_sach = LoiVuotNganSach(
        "Chi phí trong ngày (5.1234 USD) đã vượt ngân sách (5.00 USD)"
    )

    for loi in (loi_bo_chay, loi_ngan_sach):
        loi_ud = chuyen_doi_loi_sang_loi_ung_dung(loi, "ma_thu")
        ma, _, thong_diep_chuan = BANG_ANH_XA_LOI[type(loi).__name__]
        assert loi_ud.ma == ma
        assert loi_ud.thong_diep == thong_diep_chuan


def test_http_exception_ma_tran_duoc_dien_giai() -> None:
    """HTTPException có detail là mã lỗi trần được thay bằng câu dễ hiểu."""
    loi_ud = chuyen_doi_loi_sang_loi_ung_dung(
        HTTPException(status_code=401, detail="CHUA_XAC_THUC"), "ma_thu"
    )
    assert loi_ud.ma == "CHUA_XAC_THUC"
    assert loi_ud.thong_diep != "CHUA_XAC_THUC"


def test_http_exception_khong_tra_detail_noi_bo() -> None:
    """detail tuỳ ý của HTTPException không được trả ra ngoài."""
    loi_ud = chuyen_doi_loi_sang_loi_ung_dung(
        HTTPException(status_code=403, detail="psycopg: role chatbot_app denied"),
        "ma_thu",
    )
    assert loi_ud.ma == "KHONG_CO_QUYEN"
    assert "psycopg" not in loi_ud.thong_diep


def test_duong_dan_khong_ton_tai_tra_dinh_dang_chuan(client_api: TestClient) -> None:
    """404 do sai đường dẫn (Starlette) cũng trả đúng định dạng lỗi chuẩn."""
    phan_hoi = client_api.get("/khong-ton-tai")
    assert phan_hoi.status_code == 404
    assert phan_hoi.json()["loi"]["ma"] == "KHONG_TIM_THAY"
    assert "detail" not in phan_hoi.json()


def test_http_503_chung_khong_gan_cho_bo_chay() -> None:
    """HTTPException 503 chung mang mã DICH_VU_TAM_NGUNG, không quy lỗi cho bộ chạy."""
    loi_ud = chuyen_doi_loi_sang_loi_ung_dung(HTTPException(status_code=503), "ma_thu")
    assert loi_ud.ma == "DICH_VU_TAM_NGUNG"
    assert loi_ud.http == 503


def test_cors_prod_chan_dau_sao(monkeypatch: pytest.MonkeyPatch) -> None:
    """Khi MOI_TRUONG=prod, nếu CORS_ORIGINS có dấu sao '*' thì cấm khởi động."""
    monkeypatch.setattr(cau_hinh, "moi_truong", "prod")
    monkeypatch.setattr(cau_hinh, "cors_origins", ["https://app.evn.com.vn", "*"])
    with pytest.raises(ValueError, match="Môi trường prod cấm sử dụng ký tự '\\*'"):
        _kiem_tra_cors_prod()
