"""Kiểm thử ghi nhận rơi tầng, cờ hạ cấp và mục đích lượt gọi (migration 002)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.loi import LoiHetBacLocal
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import KetQuaGoiLocal
from app.llm.chi_phi import (
    KhoLuotGoiBoNho,
    KhoLuotGoiPostgres,
    LuotGoi,
    bao_cao_chi_phi,
)
from app.llm.chinh_sach import CheDoDinhTuyen
from app.llm.nha_cung_cap_dam_may import KetQuaGoiDamMay
from app.llm.router import goi_mo_hinh


def _kq_local(bac: str = "chinh") -> KetQuaGoiLocal:
    return KetQuaGoiLocal(
        noi_dung="Trả lời local",
        model="model-local:1b-q4_K_M",
        bac=bac,
        thoi_gian_nap_ms=10.0,
        do_tre_ms=100.0,
        toc_do_tok_s=30.0,
        token_vao=5,
        token_ra=10,
        ma_yeu_cau="yc",
    )


def _kq_dam_may() -> KetQuaGoiDamMay:
    return KetQuaGoiDamMay(
        noi_dung="Trả lời đám mây",
        model="nha-cung-cap/model",
        token_vao=5,
        token_ra=10,
        do_tre_ms=200.0,
        ma_yeu_cau="yc",
        tang=1,
        so_lan_thu=1,
    )


def _nguoi(che_do: CheDoDinhTuyen = CheDoDinhTuyen.LOCAL_TRUOC) -> NguoiDung:
    return NguoiDung(id="u_roi", phong_ban="CNTT", che_do_dinh_tuyen=che_do)


@pytest.mark.asyncio
async def test_roi_tang_duoc_ghi_kem_loai_loi_va_ha_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tầng 0 hỏng, tầng 1 phục vụ -> bản ghi roi_tang, loại lỗi tầng đầu, ha_cap=True."""
    monkeypatch.setattr(
        "app.llm.router.goi_local", AsyncMock(side_effect=LoiHetBacLocal("hết bậc"))
    )
    monkeypatch.setattr("app.llm.router.goi_dam_may", AsyncMock(return_value=_kq_dam_may()))
    kho = KhoLuotGoiBoNho()

    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=_nguoi(),
        ma_yeu_cau="yc_roi_1",
        kho_luot_goi=kho,
    )

    assert kq.tang == 1
    assert kq.ha_cap is True
    [ban_ghi] = kho.lay_tat_ca()
    assert ban_ghi.roi_tang is True
    assert ban_ghi.ly_do_that_bai_tang_dau == "LoiHetBacLocal"
    assert bao_cao_chi_phi(kho=kho)["ty_le_roi_tang"] == 1.0


@pytest.mark.asyncio
async def test_bac_nho_la_ha_cap_nhung_khong_roi_tang(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bậc nho trả lời -> ha_cap=True nhưng tầng phục vụ vẫn là tầng đầu."""
    monkeypatch.setattr("app.llm.router.goi_local", AsyncMock(return_value=_kq_local("nho")))
    monkeypatch.setattr("app.llm.router.goi_dam_may", AsyncMock())
    kho = KhoLuotGoiBoNho()

    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=_nguoi(),
        ma_yeu_cau="yc_roi_2",
        kho_luot_goi=kho,
    )

    assert kq.ha_cap is True
    assert kho.lay_tat_ca()[0].roi_tang is False


@pytest.mark.asyncio
async def test_dam_may_truoc_tang_1_khong_la_ha_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chế độ dam_may_truoc: tầng 1 là tầng đầu nên không bị coi là hạ cấp."""
    monkeypatch.setattr("app.llm.router.goi_local", AsyncMock())
    monkeypatch.setattr("app.llm.router.goi_dam_may", AsyncMock(return_value=_kq_dam_may()))

    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=_nguoi(CheDoDinhTuyen.DAM_MAY_TRUOC),
        ma_yeu_cau="yc_roi_3",
        kho_luot_goi=KhoLuotGoiBoNho(),
    )

    assert kq.tang == 1
    assert kq.ha_cap is False


@pytest.mark.asyncio
async def test_khoa_noi_bo_khong_chuyen_sang_nha_cung_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Các khoá nội bộ của router không được truyền xuống lời gọi đám mây."""
    mock_dam_may = AsyncMock(return_value=_kq_dam_may())
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=_nguoi(CheDoDinhTuyen.DAM_MAY_TRUOC),
        ma_yeu_cau="yc_roi_4",
        kho_luot_goi=KhoLuotGoiBoNho(),
        da_cat_ngu_canh=True,
        so_luot_bi_cat=2,
        muc_dich="chat",
    )

    tham_so = mock_dam_may.call_args.kwargs
    for khoa in ("da_cat_ngu_canh", "so_luot_bi_cat", "muc_dich", "kho_luot_goi"):
        assert khoa not in tham_so


@pytest.mark.asyncio
async def test_het_chuoi_local_ghi_luot_that_bai(monkeypatch: pytest.MonkeyPatch) -> None:
    """chi_local, local hỏng -> câu có kiểm soát và một bản ghi thanh_cong=False, roi_tang."""
    monkeypatch.setattr(
        "app.llm.router.goi_local", AsyncMock(side_effect=LoiHetBacLocal("hết bậc"))
    )
    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)
    kho = KhoLuotGoiBoNho()

    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=_nguoi(CheDoDinhTuyen.CHI_LOCAL),
        ma_yeu_cau="yc_roi_5",
        kho_luot_goi=kho,
    )

    assert kq.ten_model == "khong_co"
    assert mock_dam_may.call_count == 0
    [ban_ghi] = kho.lay_tat_ca()
    assert ban_ghi.thanh_cong is False
    assert ban_ghi.roi_tang is True
    assert bao_cao_chi_phi(kho=kho)["ty_le_roi_tang"] == 1.0


def test_luot_dat_tieu_de_khong_tinh_vao_ty_le() -> None:
    """Lượt muc_dich=tieu_de không làm lệch tỷ lệ local và phân rã theo tầng."""
    kho = KhoLuotGoiBoNho()
    chung = {
        "nguoi_id": "u",
        "nguon": "local",
        "tang": 0,
        "model": "m",
        "token_vao": 1,
        "token_ra": 1,
        "chi_phi_usd": 0.0,
        "do_tre_ms": 1.0,
        "thoi_gian_nap_ms": 0.0,
        "toc_do_tok_s": 1.0,
    }
    kho.ghi(LuotGoi(**chung, ma_yeu_cau="a", muc_dich="tieu_de"))
    kho.ghi(LuotGoi(**{**chung, "nguon": "dam_may", "tang": 1}, ma_yeu_cau="b"))

    bc = bao_cao_chi_phi(kho=kho)

    assert bc["ty_le_local"] == 0.0
    assert bc["phan_ra_theo_tang"] == {1: {"so_luot": 1, "token": 2, "chi_phi": 0.0}}


def test_kho_postgres_luu_du_cot_moi() -> None:
    """KhoLuotGoiPostgres ghi và đọc lại roi_tang, ly_do_that_bai_tang_dau, muc_dich."""
    kho = KhoLuotGoiPostgres()
    ma = f"yc_pg_{uuid.uuid4().hex[:8]}"
    kho.ghi(
        LuotGoi(
            nguoi_id="u_pg",
            nguon="dam_may",
            tang=2,
            model="m",
            token_vao=1,
            token_ra=1,
            chi_phi_usd=0.0,
            do_tre_ms=1.0,
            thoi_gian_nap_ms=0.0,
            toc_do_tok_s=1.0,
            ma_yeu_cau=ma,
            roi_tang=True,
            ly_do_that_bai_tang_dau="LoiTamThoi",
            muc_dich="tieu_de",
        )
    )

    bay_gio = datetime.now(timezone.utc)
    [ban_ghi] = [
        lg
        for lg in kho.lay_trong_khoang(bay_gio - timedelta(minutes=5), bay_gio)
        if lg.ma_yeu_cau == ma
    ]
    assert ban_ghi.roi_tang is True
    assert ban_ghi.ly_do_that_bai_tang_dau == "LoiTamThoi"
    assert ban_ghi.muc_dich == "tieu_de"
