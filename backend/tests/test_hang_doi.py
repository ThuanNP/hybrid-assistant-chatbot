"""Bộ kiểm thử cho mô-đun điều phối hàng đợi local (test_hang_doi.py).

Kiểm tra giới hạn đồng thời, hàng đợi đầy, ước lượng thời gian,
và truyền độ dài hàng đợi vào bộ chạy local.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.loi import HANG_DOI_DAY, LoiHangDoiDay
from app.core.xac_thuc import NguoiDung
from app.hang_doi.dieu_phoi import DieuPhoi
from app.llm.bo_chay_local import KetQuaDongLocal, KetQuaGoiLocal
from app.llm.chinh_sach import CheDoDinhTuyen, NhanDuLieu
from app.llm.nha_cung_cap_dam_may import KetQuaGoiDamMay
from app.llm.router import ManhPhatRa, goi_mo_hinh, goi_mo_hinh_theo_dong


@pytest.mark.asyncio
async def test_vuot_do_dai_toi_da_chuoi_chi_local_nem_hang_doi_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1. Vượt độ dài tối đa, chuỗi chỉ local -> từ chối ngay với mã HANG_DOI_DAY."""
    dp = DieuPhoi(so_luong_dong_thoi=1, do_dai_hang_doi_toi_da=2)
    # Giả lập hàng đợi đã đầy 2/2 yêu cầu đang chờ
    dp._dang_cho = 2

    mock_local = AsyncMock()
    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u_hd1", phong_ban="TaiChinh", che_do_dinh_tuyen=CheDoDinhTuyen.CHI_LOCAL)

    with pytest.raises(LoiHangDoiDay) as exc_info:
        await goi_mo_hinh(
            [{"role": "user", "content": "tra cứu nội bộ"}],
            nguoi=nguoi,
            ma_yeu_cau="yc_hd_01",
            nhan_du_lieu=NhanDuLieu.NHAY_CAM,
            dieu_phoi=dp,
        )

    assert exc_info.value.ma_loi == "HANG_DOI_DAY"
    assert issubclass(HANG_DOI_DAY, LoiHangDoiDay)
    assert mock_local.call_count == 0
    assert mock_dam_may.call_count == 0
    assert dp.so_bi_tu_choi_1_gio >= 1


@pytest.mark.asyncio
async def test_vuot_do_dai_toi_da_chuoi_co_dam_may_tang_1_phuc_vu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2. Vượt độ dài tối đa, chuỗi có đám mây -> bỏ qua tầng 0, tầng 1 phục vụ."""
    dp = DieuPhoi(so_luong_dong_thoi=1, do_dai_hang_doi_toi_da=2)
    dp._dang_cho = 2

    mock_local = AsyncMock()
    mock_dam_may = AsyncMock(
        return_value=KetQuaGoiDamMay(
            noi_dung="Chào từ Gemini tầng 1",
            model="gemini/gemini-3.5-flash-lite",
            token_vao=20,
            token_ra=40,
            do_tre_ms=300.0,
            ma_yeu_cau="yc_hd_02",
            tang=1,
            so_lan_thu=1,
        )
    )
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u_hd2", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_hd_02",
        dieu_phoi=dp,
    )

    assert kq.tang == 1
    assert kq.nguon == "dam_may"
    assert 0 in kq.danh_sach_tang_da_hong
    assert mock_local.call_count == 0
    assert mock_dam_may.call_count == 1


@pytest.mark.asyncio
async def test_vi_tri_va_uoc_luong_thoi_gian_tinh_dung(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3. Vị trí và ước lượng thời gian tính đúng; phát mảnh hang_doi trong stream."""
    dp = DieuPhoi(so_luong_dong_thoi=1, do_dai_hang_doi_toi_da=10)
    # Nạp 20 mẫu thời gian xử lý: trung vị là 4.0 giây
    for t in [4.0] * 20:
        dp.ghi_nhan_thoi_gian(t)

    vt1 = await dp.vao_hang("yc_vt1")
    assert vt1.vi_tri == 1
    assert vt1.uoc_luong_giay == 4.0

    vt2 = await dp.vao_hang("yc_vt2")
    assert vt2.vi_tri == 2
    assert vt2.uoc_luong_giay == 8.0

    tt = dp.trang_thai()
    assert tt.dang_cho == 2
    assert tt.thoi_gian_cho_trung_vi == 4.0

    # Kiểm tra router phát ra ManhPhatRa loại "hang_doi" ngay khi vào hàng
    async def _mock_local_stream(*args, **kwargs):
        yield KetQuaDongLocal(
            noi_dung="Nội dung phản hồi",
            da_xong=False,
            model="qwen3.5:9b",
            bac="chinh",
            ma_yeu_cau="yc_hd_03",
        )
        yield KetQuaDongLocal(
            noi_dung="",
            da_xong=True,
            model="qwen3.5:9b",
            bac="chinh",
            ma_yeu_cau="yc_hd_03",
        )

    async def _goi_local_fake(*args, **kwargs):
        if kwargs.get("phat_theo_dong"):
            return _mock_local_stream()
        raise NotImplementedError

    monkeypatch.setattr("app.llm.router.goi_local", _goi_local_fake)

    nguoi = NguoiDung(id="u_hd3", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    dp_stream = DieuPhoi(so_luong_dong_thoi=1, do_dai_hang_doi_toi_da=5)
    dp_stream._dang_chay = 1  # Chiếm slot để kích hoạt luồng xếp hàng chờ

    cac_manh: list[ManhPhatRa] = []
    # Giải phóng slot sau 0.05 giây để luồng chờ được chạy
    async def _giai_phong_som() -> None:
        await dp_stream._semaphore.acquire()
        dp_stream._semaphore.release()
        dp_stream._dang_chay = 0

    import asyncio
    asyncio.create_task(_giai_phong_som())

    async for manh in goi_mo_hinh_theo_dong(
        [{"role": "user", "content": "chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_hd_03",
        dieu_phoi=dp_stream,
        luon_vao_hang=True,
    ):
        cac_manh.append(manh)

    assert any(m.loai == "hang_doi" for m in cac_manh)
    manh_hd = next(m for m in cac_manh if m.loai == "hang_doi")
    assert manh_hd.vi_tri is not None
    assert manh_hd.uoc_luong_giay is not None


@pytest.mark.asyncio
async def test_do_dai_hang_doi_duoc_truyen_vao_goi_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4. Độ dài hàng đợi hiện tại được truyền chính xác vào goi_local."""
    dp = DieuPhoi(so_luong_dong_thoi=2, do_dai_hang_doi_toi_da=10)
    dp._dang_cho = 5  # Giả định hàng đợi có 5 người đang chờ

    mock_local = AsyncMock(
        return_value=KetQuaGoiLocal(
            noi_dung="Kết quả local",
            model="qwen3.5:2b",
            bac="nho",
            thoi_gian_nap_ms=10.0,
            do_tre_ms=150.0,
            toc_do_tok_s=40.0,
            token_vao=15,
            token_ra=25,
            ma_yeu_cau="yc_hd_04",
            do_dai_hang_doi=5,
        )
    )
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)

    nguoi = NguoiDung(id="u_hd4", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    await goi_mo_hinh(
        [{"role": "user", "content": "kiểm tra hàng đợi"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_hd_04",
        dieu_phoi=dp,
    )

    assert mock_local.call_count == 1
    call_kwargs = mock_local.call_args.kwargs
    assert call_kwargs.get("do_dai_hang_doi") == 5
