"""Bộ kiểm thử cho mô-đun quản lý chi phí và ngân sách (test_chi_phi.py).

Kiểm tra tính chi phí theo bảng giá YAML, kiểm soát vượt ngân sách,
và tính toán tỷ lệ rơi tầng trên dữ liệu giả lập.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.loi import VUOT_NGAN_SACH, LoiVuotNganSach
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import KetQuaGoiLocal
from app.llm.chi_phi import (
    KhoLuotGoiBoNho,
    LuotGoi,
    bao_cao_chi_phi,
    tinh_ty_le_roi_tang,
    uoc_tinh_chi_phi,
)
from app.llm.chinh_sach import CheDoDinhTuyen
from app.llm.router import goi_mo_hinh


@pytest.mark.asyncio
async def test_vuot_ngan_sach_0_loi_goi_dam_may_local_van_phuc_vu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1. Vượt ngân sách -> 0 lời gọi đám mây, local vẫn phục vụ bình thường."""
    kho = KhoLuotGoiBoNho()
    # Nạp 1 bản ghi lịch sử gọi đám mây trong ngày với chi phí 15.0 USD (vượt mức 10.0 USD)
    kho.ghi(
        LuotGoi(
            nguoi_id="u_cu",
            nguon="dam_may",
            tang=1,
            model="gemini/gemini-3.5-flash-lite",
            token_vao=1000,
            token_ra=5000,
            chi_phi_usd=15.0,
            do_tre_ms=500.0,
            thoi_gian_nap_ms=0.0,
            toc_do_tok_s=20.0,
            thanh_cong=True,
            ma_yeu_cau="yc_cu_01",
        )
    )

    mock_dam_may = AsyncMock()
    mock_local = AsyncMock(
        return_value=KetQuaGoiLocal(
            noi_dung="Chào từ local khi vượt ngân sách",
            model="qwen3.5:9b",
            bac="chinh",
            thoi_gian_nap_ms=12.0,
            do_tre_ms=200.0,
            toc_do_tok_s=35.0,
            token_vao=10,
            token_ra=20,
            ma_yeu_cau="yc_ns_01",
        )
    )
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)

    # Chế độ dam_may_truoc: chuỗi ưu tiên đám mây trước, sau đó rơi xuống local
    nguoi = NguoiDung(id="u_ns1", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.DAM_MAY_TRUOC)
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "tính tiền điện"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_ns_01",
        kho_luot_goi=kho,
    )

    # Đám mây bị bỏ qua hoàn toàn do vượt ngân sách, 0 lời gọi phát sinh
    assert mock_dam_may.call_count == 0
    # Tầng local tiếp theo phục vụ thành công
    assert mock_local.call_count == 1
    assert kq.nguon == "local"
    assert kq.tang == 0

    # Trường hợp chuỗi chỉ có đám mây hoặc không còn local -> ném LoiVuotNganSach
    mock_local_loi = AsyncMock(side_effect=RuntimeError("Local lỗi"))
    monkeypatch.setattr("app.llm.router.goi_local", mock_local_loi)

    nguoi_local_truoc = NguoiDung(
        id="u_ns2",
        phong_ban="CNTT",
        che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC,
    )
    with pytest.raises(LoiVuotNganSach) as exc_info:
        await goi_mo_hinh(
            [{"role": "user", "content": "xin chào"}],
            nguoi=nguoi_local_truoc,
            ma_yeu_cau="yc_ns_02",
            kho_luot_goi=kho,
        )

    assert exc_info.value.ma_loi == "VUOT_NGAN_SACH"
    assert issubclass(VUOT_NGAN_SACH, LoiVuotNganSach)


def test_chi_phi_tang_0_bang_0_tang_4_tinh_dung_theo_yaml() -> None:
    """2. Chi phí tầng 0 bằng 0; tầng 4 tính đúng theo đơn giá trong models.yaml."""
    # Tầng 0 (local): luôn luôn bằng 0.0 USD
    chi_phi_t0 = uoc_tinh_chi_phi(tang=0, token_vao=50000, token_ra=20000)
    assert chi_phi_t0 == 0.0

    # Tầng 4 (OpenAI trong config/models.yaml: giá vào 2.00 USD/triệu, giá ra 12.00 USD/triệu)
    # Ví dụ: 1000 token vào, 500 token ra
    # Chi phí = (1000 * 2.00 + 500 * 12.00) / 1,000,000 = (2000 + 6000) / 1,000,000 = 0.008 USD
    chi_phi_t4 = uoc_tinh_chi_phi(tang=4, token_vao=1000, token_ra=500)
    assert chi_phi_t4 == 0.008

    # Tầng 1 (Gemini trong models.yaml: giá vào 0.30 USD/triệu, giá ra 2.50 USD/triệu)
    # Ví dụ: 1,000,000 token vào, 1,000,000 token ra = 0.30 + 2.50 = 2.80 USD
    chi_phi_t1 = uoc_tinh_chi_phi(tang=1, token_vao=1_000_000, token_ra=1_000_000)
    assert chi_phi_t1 == 2.80


def test_ty_le_roi_tang_tinh_dung_tren_du_lieu_gia() -> None:
    """3. Tỷ lệ rơi tầng tính đúng trên dữ liệu giả lập và báo cáo chi phí tổng hợp."""
    kho = KhoLuotGoiBoNho()
    now = datetime.now(timezone.utc)

    # Nạp 10 lượt gọi giả lập trong vòng 1 giờ qua:
    # 7 lượt chạy thành công ở tầng đầu (roi_tang=False)
    # 3 lượt bị rơi tầng (roi_tang=True)
    for i in range(7):
        kho.ghi(
            LuotGoi(
                thoi_diem=now,
                nguoi_id=f"u_ok_{i}",
                nguon="local",
                tang=0,
                model="qwen3.5:9b",
                token_vao=100,
                token_ra=200,
                chi_phi_usd=0.0,
                do_tre_ms=100.0,
                thoi_gian_nap_ms=0.0,
                toc_do_tok_s=30.0,
                thanh_cong=True,
                ma_yeu_cau=f"yc_ok_{i}",
                roi_tang=False,
            )
        )

    for i in range(3):
        kho.ghi(
            LuotGoi(
                thoi_diem=now,
                nguoi_id=f"u_roi_{i}",
                nguon="dam_may",
                tang=1,
                model="gemini/gemini-3.5-flash-lite",
                token_vao=200,
                token_ra=300,
                chi_phi_usd=0.001,
                do_tre_ms=300.0,
                thoi_gian_nap_ms=0.0,
                toc_do_tok_s=25.0,
                thanh_cong=True,
                ma_yeu_cau=f"yc_roi_{i}",
                roi_tang=True,
                ly_do_that_bai_tang_dau="Local timeout quá hạn 120s",
            )
        )

    ty_le, ly_do = tinh_ty_le_roi_tang(kho=kho, gio_gan_nhat=1)
    # 3 / 10 = 0.30 (tương đương 30%)
    assert ty_le == 0.30 or ty_le == 30.0
    assert ly_do == "Local timeout quá hạn 120s"

    bc = bao_cao_chi_phi(kho=kho)
    assert bc["ty_le_roi_tang"] == 0.30 or bc["ty_le_roi_tang"] == 30.0
    assert bc["ty_le_local"] == 0.70 or bc["ty_le_local"] == 70.0
    assert bc["chi_phi_hom_nay_usd"] == 0.003
    assert 0 in bc["phan_ra_theo_tang"]
    assert 1 in bc["phan_ra_theo_tang"]
    assert bc["phan_ra_theo_tang"][0]["so_luot"] == 7
    assert bc["phan_ra_theo_tang"][1]["so_luot"] == 3
