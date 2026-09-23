"""Kiểm thử các phần API mà giao diện Angular phụ thuộc.

Gồm: lọc và sắp xếp Lịch sử ở máy chủ, quyền truy cập hội thoại khi phát theo dòng,
trường đầy đủ khi mở lại hội thoại, sự kiện xong có ma_yeu_cau và ha_cap, số câu hỏi
trong ngày, không lưu nội dung bị móc kiểm duyệt từ chối, và CORS expose_headers.
"""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.chat.su_kien_sse as sse_mod
from app.chat.su_kien_sse import ManhPhatRa
from app.config import cau_hinh
from app.core.bao_mat import KetQuaKiemDuyet
from app.core.csdl import (
    HoiThoaiModel,
    LuotModel,
    NguoiDungModel,
    lay_sessionmaker_async,
)
from app.core.thoi_gian import MUI_GIO_VN
from app.core.xac_thuc import NguoiDung
from app.llm.router import KetQuaGoi
from app.main import app


@pytest.fixture
def client_api() -> TestClient:
    return TestClient(app)


def _su_kien(van_ban: str) -> list[tuple[str, dict[str, Any]]]:
    """Tách chuỗi SSE thành danh sách (tên sự kiện, dữ liệu)."""
    ket_qua: list[tuple[str, dict[str, Any]]] = []
    for khoi in van_ban.split("\n\n"):
        ten, du_lieu = "", ""
        for dong in khoi.splitlines():
            if dong.startswith("event: "):
                ten = dong[len("event: "):]
            elif dong.startswith("data: "):
                du_lieu = dong[len("data: "):]
        if ten:
            ket_qua.append((ten, json.loads(du_lieu)))
    return ket_qua


async def _dem_luot(hoi_thoai_id: int) -> int:
    async with lay_sessionmaker_async()() as phien:
        cau_lenh = select(func.count(LuotModel.id)).where(LuotModel.hoi_thoai_id == hoi_thoai_id)
        return int((await phien.scalars(cau_lenh)).first() or 0)


def _gia_lap_luong(monkeypatch: pytest.MonkeyPatch, *, ha_cap: bool = False) -> None:
    async def _goi_theo_dong_gia(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(loai="bat_dau", nguon="local", tang=0, ten_model="m-local")
        yield ManhPhatRa(loai="manh", noi_dung="Xin ")
        yield ManhPhatRa(loai="manh", noi_dung="chào.")
        yield ManhPhatRa(
            loai="xong",
            ket_qua=KetQuaGoi(
                noi_dung="Xin chào.",
                nguon="local",
                tang=0,
                bac_local="nho" if ha_cap else "chinh",
                ten_model="m-local",
                ha_cap=ha_cap,
            ),
        )

    monkeypatch.setattr(sse_mod, "goi_mo_hinh_theo_dong", _goi_theo_dong_gia)
    # Không chạy tác vụ nền đặt tiêu đề trong kiểm thử
    monkeypatch.setattr(sse_mod, "tu_dat_tieu_de", _khong_lam_gi)


async def _khong_lam_gi(**_: Any) -> None:
    return None


async def _hoi_thoai_nguoi_khac(phien: AsyncSession) -> int:
    if await phien.get(NguoiDungModel, 9999) is None:
        phien.add(
            NguoiDungModel(
                id=9999,
                ten_dang_nhap="can_bo_9999",
                ho_ten="Cán bộ phòng ban khác",
                vai_tro="nguoi_dung",
                bac="chinh",
                phong_ban="KY_THUAT",
                dang_hoat_dong=True,
            )
        )
        await phien.flush()
    ht = HoiThoaiModel(nguoi_id=9999, tieu_de="Hội thoại của người khác", da_xoa=False)
    phien.add(ht)
    await phien.commit()
    return ht.id


# ---------------------------------------------------------------------------
# Lọc và sắp xếp Lịch sử ở máy chủ
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loc_tu_khoa_ngay_va_sap_xep(
    phien_csdl: AsyncSession, nguoi_dung_test: NguoiDung, client_api: TestClient
) -> None:
    ma = uuid.uuid4().hex[:8]
    hom_nay = datetime.now(MUI_GIO_VN).replace(hour=10, minute=0, second=0, microsecond=0)
    mau = [
        (f"Beta {ma}", hom_nay),
        (f"alpha {ma}", hom_nay - timedelta(days=1)),
        (f"Gamma {ma}", hom_nay - timedelta(days=10)),
    ]
    cac_id: list[int] = []
    for tieu_de, thoi_diem in mau:
        ht = HoiThoaiModel(
            nguoi_id=nguoi_dung_test.id,
            tieu_de=tieu_de,
            da_xoa=False,
            cap_nhat_luc=thoi_diem.astimezone(timezone.utc),
        )
        phien_csdl.add(ht)
        await phien_csdl.flush()
        cac_id.append(ht.id)
    await phien_csdl.commit()

    try:
        tat_ca = client_api.get(f"/api/v1/hoi-thoai?tu_khoa={ma.upper()}&kich_thuoc=100").json()
        assert tat_ca["tong_so"] == 3

        theo_ten = client_api.get(f"/api/v1/hoi-thoai?tu_khoa={ma}&sap_xep=ten_tang").json()
        assert [m["tieu_de"].split()[0] for m in theo_ten["danh_sach"]] == [
            "alpha",
            "Beta",
            "Gamma",
        ]

        cu_nhat = client_api.get(f"/api/v1/hoi-thoai?tu_khoa={ma}&sap_xep=cu_nhat").json()
        assert cu_nhat["danh_sach"][0]["tieu_de"] == f"Gamma {ma}"

        hai_ngay = (hom_nay - timedelta(days=1)).date().isoformat()
        loc_ngay = client_api.get(
            f"/api/v1/hoi-thoai?tu_khoa={ma}&tu_ngay={hai_ngay}&den_ngay={hai_ngay}"
        ).json()
        assert [m["tieu_de"] for m in loc_ngay["danh_sach"]] == [f"alpha {ma}"]
        assert loc_ngay["tong_so"] == 1

        phan_trang = client_api.get(f"/api/v1/hoi-thoai?tu_khoa={ma}&kich_thuoc=2&trang=2")
        assert [m["tieu_de"] for m in phan_trang.json()["danh_sach"]] == [f"Gamma {ma}"]
    finally:
        for ht_id in cac_id:
            client_api.delete(f"/api/v1/hoi-thoai/{ht_id}")


def test_tu_khoa_ky_tu_dai_dien_duoc_thoat(client_api: TestClient) -> None:
    """Ký tự % trong từ khoá được so khớp nguyên văn, không thành ký tự đại diện."""
    phan_hoi = client_api.get("/api/v1/hoi-thoai?tu_khoa=%25%25khong-co-tieu-de-nay%25")
    assert phan_hoi.status_code == 200
    assert phan_hoi.json()["tong_so"] == 0


def test_tu_ngay_sau_den_ngay_tra_422(client_api: TestClient) -> None:
    phan_hoi = client_api.get("/api/v1/hoi-thoai?tu_ngay=2026-09-10&den_ngay=2026-09-01")
    assert phan_hoi.status_code == 422
    assert phan_hoi.json()["loi"]["ma"] == "DAU_VAO_KHONG_HOP_LE"


def test_sap_xep_la_tra_422(client_api: TestClient) -> None:
    phan_hoi = client_api.get("/api/v1/hoi-thoai?sap_xep=ngau_nhien")
    assert phan_hoi.status_code == 422


# ---------------------------------------------------------------------------
# Quyền truy cập hội thoại khi phát theo dòng
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_hoi_thoai_nguoi_khac_bi_tu_choi(
    monkeypatch: pytest.MonkeyPatch,
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
    client_api: TestClient,
) -> None:
    _gia_lap_luong(monkeypatch)
    ht_id = await _hoi_thoai_nguoi_khac(phien_csdl)

    phan_hoi = client_api.post(
        "/api/v1/chat/stream", json={"hoi_thoai_id": ht_id, "noi_dung": "xin chào"}
    )

    [(ten, du_lieu)] = _su_kien(phan_hoi.text)
    assert ten == "loi"
    assert du_lieu["ma"] == "KHONG_TIM_THAY"
    assert await _dem_luot(ht_id) == 0


@pytest.mark.asyncio
async def test_stream_id_khong_ton_tai_khong_tao_hoi_thoai(
    monkeypatch: pytest.MonkeyPatch, nguoi_dung_test: NguoiDung, client_api: TestClient
) -> None:
    _gia_lap_luong(monkeypatch)
    id_la = 2_000_000_000

    phan_hoi = client_api.post(
        "/api/v1/chat/stream", json={"hoi_thoai_id": id_la, "noi_dung": "xin chào"}
    )

    assert _su_kien(phan_hoi.text)[0][1]["ma"] == "KHONG_TIM_THAY"
    async with lay_sessionmaker_async()() as phien:
        assert await phien.get(HoiThoaiModel, id_la) is None


def test_chat_id_khong_ton_tai_tra_404(client_api: TestClient) -> None:
    phan_hoi = client_api.post(
        "/api/v1/chat", json={"hoi_thoai_id": 2_000_000_001, "noi_dung": "xin chào"}
    )
    assert phan_hoi.status_code == 404
    assert phan_hoi.json()["loi"]["ma"] == "KHONG_TIM_THAY"


def test_stream_noi_dung_rong_tra_422(client_api: TestClient) -> None:
    phan_hoi = client_api.post("/api/v1/chat/stream", json={"noi_dung": ""})
    assert phan_hoi.status_code == 422


# ---------------------------------------------------------------------------
# Sự kiện xong và mở lại hội thoại
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_xong_co_ma_yeu_cau_va_ha_cap_mo_lai_du_truong(
    monkeypatch: pytest.MonkeyPatch, nguoi_dung_test: NguoiDung, client_api: TestClient
) -> None:
    _gia_lap_luong(monkeypatch, ha_cap=True)

    phan_hoi = client_api.post("/api/v1/chat/stream", json={"noi_dung": "xin chào"})

    su_kien = dict(_su_kien(phan_hoi.text))
    ma_yc = phan_hoi.headers["X-Ma-Yeu-Cau"]
    assert su_kien["xong"]["ma_yeu_cau"] == ma_yc
    assert su_kien["xong"]["ha_cap"] is True

    ht_id = su_kien["bat_dau"]["hoi_thoai_id"]
    try:
        chi_tiet = client_api.get(f"/api/v1/hoi-thoai/{ht_id}").json()
        nguoi, tro_ly = chi_tiet["cac_luot"]
        assert nguoi["nhan_ai"] is None
        assert nguoi["ha_cap"] is False
        assert tro_ly["ma_yeu_cau"] == ma_yc
        assert tro_ly["nhan_ai"].startswith("Nội dung do AI tạo - m-local - ")
        assert tro_ly["ha_cap"] is True
        for truong in ("toc_do_tok_s", "do_tre_ms", "da_cat_ngu_canh", "so_luot_bi_cat"):
            assert truong in tro_ly
    finally:
        client_api.delete(f"/api/v1/hoi-thoai/{ht_id}")


# ---------------------------------------------------------------------------
# Không lưu nội dung bị móc kiểm duyệt từ chối
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dau_ra_bi_chan_khong_luu(
    monkeypatch: pytest.MonkeyPatch,
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
    client_api: TestClient,
) -> None:
    _gia_lap_luong(monkeypatch)

    async def _chan(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        return KetQuaKiemDuyet(cho_qua=False, ly_do="Bị chặn trong kiểm thử")

    monkeypatch.setattr(sse_mod, "kiem_duyet_dau_ra", _chan)
    ht = HoiThoaiModel(nguoi_id=nguoi_dung_test.id, tieu_de="Kiểm duyệt đầu ra", da_xoa=False)
    phien_csdl.add(ht)
    await phien_csdl.commit()

    try:
        phan_hoi = client_api.post(
            "/api/v1/chat/stream", json={"hoi_thoai_id": ht.id, "noi_dung": "xin chào"}
        )
        assert _su_kien(phan_hoi.text)[-1][1]["ma"] == "NOI_DUNG_BI_CHAN"
        assert await _dem_luot(ht.id) == 0
    finally:
        client_api.delete(f"/api/v1/hoi-thoai/{ht.id}")


@pytest.mark.asyncio
async def test_dau_vao_bi_chan_khong_tao_hoi_thoai(
    monkeypatch: pytest.MonkeyPatch, nguoi_dung_test: NguoiDung, client_api: TestClient
) -> None:
    _gia_lap_luong(monkeypatch)

    async def _chan(noi_dung: str, nguoi: Any) -> KetQuaKiemDuyet:
        return KetQuaKiemDuyet(cho_qua=False)

    monkeypatch.setattr(sse_mod, "kiem_duyet_dau_vao", _chan)
    truoc = client_api.get("/api/v1/hoi-thoai").json()["tong_so"]

    phan_hoi = client_api.post("/api/v1/chat/stream", json={"noi_dung": "xin chào"})

    [(ten, du_lieu)] = _su_kien(phan_hoi.text)
    assert (ten, du_lieu["ma"]) == ("loi", "NOI_DUNG_BI_CHAN")
    assert client_api.get("/api/v1/hoi-thoai").json()["tong_so"] == truoc


# ---------------------------------------------------------------------------
# Số liệu KPI và CORS
# ---------------------------------------------------------------------------


def test_chi_phi_co_so_cau_hoi_va_nguong(client_api: TestClient) -> None:
    du_lieu = client_api.get("/api/v1/chi-phi").json()
    for truong in ("so_cau_hoi_hom_nay", "so_cau_hoi_noi_bo", "so_cau_hoi_dam_may"):
        assert isinstance(du_lieu[truong], int)
    assert 0.0 <= du_lieu["ty_le_local"] <= 1.0
    assert 0.0 <= du_lieu["ty_le_roi_tang"] <= 1.0
    assert du_lieu["nguong_canh_bao_ngan_sach"] == cau_hinh.cai_dat_chung.nguong_canh_bao_ngan_sach
    assert du_lieu["nguong_ty_le_roi_tang"] == cau_hinh.cai_dat_chung.nguong_ty_le_roi_tang


def test_cors_mo_header_ma_yeu_cau(client_api: TestClient) -> None:
    if not cau_hinh.cors_origins:
        pytest.skip("CORS_ORIGINS trống")
    phan_hoi = client_api.get("/health", headers={"Origin": cau_hinh.cors_origins[0]})
    assert "X-Ma-Yeu-Cau" in phan_hoi.headers.get("access-control-expose-headers", "")
