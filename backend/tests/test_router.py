"""Bộ kiểm thử đơn vị cho mô-đun định tuyến mô hình (router.py).

Toàn bộ các ca kiểm thử sử dụng giả lập (mock), bảo đảm không gọi mạng thật.
Tuân thủ đầy đủ 8 kịch bản kiểm thử bắt buộc trong yêu cầu nghiệp vụ.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.loi import (
    LoiDauVao,
    LoiHetBacLocal,
    LoiHetChuoiDuPhong,
    LoiTamThoi,
    LoiVinhVien,
)
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import KetQuaDongLocal, KetQuaGoiLocal
from app.llm.chinh_sach import CheDoDinhTuyen, NhanDuLieu
from app.llm.nha_cung_cap_dam_may import KetQuaDongDamMay, KetQuaGoiDamMay
from app.llm.router import ManhPhatRa, goi_mo_hinh, goi_mo_hinh_theo_dong


@pytest.mark.asyncio
async def test_tang_0_thanh_cong_khong_goi_tang_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """1. Tầng 0 thành công thì không gọi tầng 1."""
    mock_local = AsyncMock(
        return_value=KetQuaGoiLocal(
            noi_dung="Chào bạn từ local",
            model="qwen3.5:9b-q4_K_M",
            bac="chinh",
            thoi_gian_nap_ms=12.5,
            do_tre_ms=180.0,
            toc_do_tok_s=32.0,
            token_vao=12,
            token_ra=24,
            ma_yeu_cau="yc_01",
        )
    )
    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u1", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_01",
    )

    assert kq.nguon == "local"
    assert kq.tang == 0
    assert kq.bac_local == "chinh"
    assert kq.ten_model == "qwen3.5:9b-q4_K_M"
    assert kq.noi_dung == "Chào bạn từ local"
    assert mock_local.call_count == 1
    assert mock_dam_may.call_count == 0


@pytest.mark.asyncio
async def test_tang_0_hong_local_truoc_roi_tang_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """2. Tầng 0 hỏng, local_truoc -> tang = 1, danh_sach_tang_da_hong có tầng 0."""
    mock_local = AsyncMock(side_effect=LoiHetBacLocal("Cả hai bậc local đều không phản hồi"))
    mock_dam_may = AsyncMock(
        return_value=KetQuaGoiDamMay(
            noi_dung="Chào từ Gemini đám mây",
            model="gemini/gemini-3.5-flash-lite",
            token_vao=15,
            token_ra=30,
            do_tre_ms=320.0,
            ma_yeu_cau="yc_02",
            tang=1,
            so_lan_thu=1,
        )
    )
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u2", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_02",
    )

    assert kq.nguon == "dam_may"
    assert kq.tang == 1
    assert kq.ten_model == "gemini/gemini-3.5-flash-lite"
    assert kq.danh_sach_tang_da_hong == [0]
    assert mock_local.call_count == 1
    assert mock_dam_may.call_count == 1


@pytest.mark.asyncio
async def test_nhay_cam_tang_0_hong_tra_cau_kiem_soat(monkeypatch: pytest.MonkeyPatch) -> None:
    """3. NHAY_CAM, tầng 0 hỏng -> trả câu có kiểm soát; bộ giả lập đám mây ghi nhận 0 lần gọi."""
    mock_local = AsyncMock(side_effect=LoiHetBacLocal("Local sập hoàn toàn"))
    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u3", phong_ban="CNTT")
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "Tra cứu mã khách hàng PE01000123456"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_03",
        nhan_du_lieu=NhanDuLieu.NHAY_CAM,
    )

    assert kq.nguon == "local"
    assert kq.tang == 0
    assert kq.ten_model == "khong_co"
    assert "bận" in kq.noi_dung or "thử lại sau" in kq.noi_dung
    assert mock_dam_may.call_count == 0


@pytest.mark.asyncio
async def test_tang_1_tra_401_roi_tang_2_ngay(monkeypatch: pytest.MonkeyPatch) -> None:
    """4. Tầng 1 trả 401 (LoiVinhVien) -> rơi tầng 2 ngay."""
    mock_local = AsyncMock(side_effect=LoiHetBacLocal("Local lỗi"))

    async def _mock_dam_may(tang, *args, **kwargs):
        if tang.tang == 1:
            raise LoiVinhVien("Khoá API Gemini không hợp lệ", ma_trang_thai=401)
        if tang.tang == 2:
            return KetQuaGoiDamMay(
                noi_dung="Chào từ OpenRouter",
                model="openrouter/auto",
                token_vao=20,
                token_ra=40,
                do_tre_ms=410.0,
                ma_yeu_cau="yc_04",
                tang=2,
                so_lan_thu=1,
            )
        raise RuntimeError(f"Tầng ngoài dự kiến: {tang.tang}")

    mock_dam_may = AsyncMock(side_effect=_mock_dam_may)
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u4", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    kq = await goi_mo_hinh(
        [{"role": "user", "content": "xin chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_04",
    )

    assert kq.tang == 2
    assert kq.ten_model == "openrouter/auto"
    assert kq.danh_sach_tang_da_hong == [0, 1]
    assert mock_dam_may.call_count == 2


@pytest.mark.asyncio
async def test_loi_dau_vao_tang_1_nem_len_khong_goi_tang_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5. LoiDauVao ở tầng 1 -> ném lên, tầng 2 không được gọi."""
    mock_local = AsyncMock(side_effect=LoiHetBacLocal("Local lỗi"))
    mock_dam_may = AsyncMock(side_effect=LoiDauVao("Dữ liệu đầu vào sai cú pháp", ma_trang_thai=400))
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u5", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    with pytest.raises(LoiDauVao) as exc_info:
        await goi_mo_hinh(
            [{"role": "user", "content": "lỗi đầu vào"}],
            nguoi=nguoi,
            ma_yeu_cau="yc_05",
        )

    assert exc_info.value.ma_trang_thai == 400
    assert mock_dam_may.call_count == 1


@pytest.mark.asyncio
async def test_stream_loi_truoc_manh_dau_roi_tang(monkeypatch: pytest.MonkeyPatch) -> None:
    """6. Stream: lỗi trước mảnh đầu -> rơi tầng, người dùng nhận đủ câu từ tầng sau."""
    async def _mock_local_loi_dau(*args, **kwargs):
        raise LoiHetBacLocal("Local sập trước khi phát")
        yield  # Biến hàm thành generator

    async def _mock_dam_may_stream(tang, *args, **kwargs):
        yield KetQuaDongDamMay(
            noi_dung="Xin ",
            da_xong=False,
            model="gemini/gemini-3.5-flash-lite",
            tang=1,
            ma_yeu_cau="yc_06",
        )
        yield KetQuaDongDamMay(
            noi_dung="chào các bạn!",
            da_xong=False,
            model="gemini/gemini-3.5-flash-lite",
            tang=1,
            ma_yeu_cau="yc_06",
        )
        yield KetQuaDongDamMay(
            noi_dung="",
            da_xong=True,
            model="gemini/gemini-3.5-flash-lite",
            tang=1,
            ma_yeu_cau="yc_06",
            token_vao=8,
            token_ra=4,
            do_tre_ms=250.0,
        )

    async def _goi_local_fake(*args, **kwargs):
        if kwargs.get("phat_theo_dong"):
            return _mock_local_loi_dau()
        raise NotImplementedError

    async def _goi_dam_may_fake(tang, *args, **kwargs):
        if kwargs.get("phat_theo_dong"):
            return _mock_dam_may_stream(tang, *args, **kwargs)
        raise NotImplementedError

    monkeypatch.setattr("app.llm.router.goi_local", _goi_local_fake)
    monkeypatch.setattr("app.llm.router.goi_dam_may", _goi_dam_may_fake)

    nguoi = NguoiDung(id="u6", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    cac_manh: list[ManhPhatRa] = []
    async for manh in goi_mo_hinh_theo_dong(
        [{"role": "user", "content": "chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_06",
    ):
        cac_manh.append(manh)

    assert len(cac_manh) == 3
    assert cac_manh[0].loai == "manh" and cac_manh[0].noi_dung == "Xin "
    assert cac_manh[1].loai == "manh" and cac_manh[1].noi_dung == "chào các bạn!"
    assert cac_manh[2].loai == "xong"
    assert cac_manh[2].ket_qua is not None
    assert cac_manh[2].ket_qua.tang == 1
    assert cac_manh[2].ket_qua.noi_dung == "Xin chào các bạn!"
    assert cac_manh[2].ket_qua.danh_sach_tang_da_hong == [0]


@pytest.mark.asyncio
async def test_stream_loi_sau_hai_manh_tra_manh_loi_khong_goi_tang_sau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """7. Stream: lỗi sau 2 mảnh -> mảnh cuối là 'loi', có phần đã nhận, tầng sau không được gọi."""
    async def _mock_local_stream_loi_giua(*args, **kwargs):
        yield KetQuaDongLocal(
            noi_dung="Đoạn 1 ",
            da_xong=False,
            model="qwen3.5:9b",
            bac="chinh",
            ma_yeu_cau="yc_07",
        )
        yield KetQuaDongLocal(
            noi_dung="Đoạn 2 ",
            da_xong=False,
            model="qwen3.5:9b",
            bac="chinh",
            ma_yeu_cau="yc_07",
        )
        raise ConnectionResetError("Mất kết nối mạng đột ngột giữa chừng")

    async def _goi_local_fake(*args, **kwargs):
        if kwargs.get("phat_theo_dong"):
            return _mock_local_stream_loi_giua()
        raise NotImplementedError

    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_local", _goi_local_fake)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u7", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    cac_manh: list[ManhPhatRa] = []
    async for manh in goi_mo_hinh_theo_dong(
        [{"role": "user", "content": "chào"}],
        nguoi=nguoi,
        ma_yeu_cau="yc_07",
    ):
        cac_manh.append(manh)

    assert len(cac_manh) == 3
    assert cac_manh[0].loai == "manh" and cac_manh[0].noi_dung == "Đoạn 1 "
    assert cac_manh[1].loai == "manh" and cac_manh[1].noi_dung == "Đoạn 2 "
    assert cac_manh[2].loai == "loi"
    assert cac_manh[2].noi_dung == "Đoạn 1 Đoạn 2 "
    assert cac_manh[2].ket_qua is None
    assert mock_dam_may.call_count == 0


@pytest.mark.asyncio
async def test_het_chuoi_dam_may_nem_loi_het_chuoi_du_phong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8. Hết chuỗi đám mây -> LoiHetChuoiDuPhong có đủ lý do từng tầng."""
    mock_local = AsyncMock(side_effect=LoiHetBacLocal("Tầng 0: Local không khả dụng"))
    mock_dam_may = AsyncMock(side_effect=LoiTamThoi("Đám mây gặp lỗi 503 Service Unavailable"))
    monkeypatch.setattr("app.llm.router.goi_local", mock_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    nguoi = NguoiDung(id="u8", phong_ban="CNTT", che_do_dinh_tuyen=CheDoDinhTuyen.LOCAL_TRUOC)
    with pytest.raises(LoiHetChuoiDuPhong) as exc_info:
        await goi_mo_hinh(
            [{"role": "user", "content": "thử nghiệm"}],
            nguoi=nguoi,
            ma_yeu_cau="yc_08",
        )

    ly_do = exc_info.value.danh_sach_ly_do
    assert 0 in ly_do
    assert 1 in ly_do
