"""Bộ kiểm thử cho quản lý hội thoại và lưu trữ cơ sở dữ liệu PostgreSQL.

Kiểm tra 4 kịch bản kỹ thuật cốt lõi theo yêu cầu:
1. Ghép ngữ cảnh đúng thứ tự thời gian.
2. Số liệu đo được lưu đầy đủ trong bảng luot.
3. Đặt tiêu đề dùng đúng bậc nho (hoặc bậc chinh khi so_model_nap_cung_luc = 1) và không gọi đám mây.
4. Xóa hội thoại thì toàn bộ các lượt bị xóa theo (ON DELETE CASCADE).
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.hoi_thoai import (
    doc_phien_ban_loi_nhac,
    lay_danh_sach_luot,
    lay_hoi_thoai,
    luu_cap_luot_hoi_thoai,
    tao_hoi_thoai,
    tu_dat_tieu_de,
    xoa_hoi_thoai,
)
from app.chat.ngu_canh import dung_ngu_canh
from app.config import cau_hinh
from app.core.csdl import LuotModel
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import KetQuaGoiLocal
from app.llm.chinh_sach import Tang
from app.llm.router import KetQuaGoi


@pytest.mark.asyncio
async def test_ghep_ngu_canh_dung_thu_tu_thoi_gian(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
) -> None:
    """1. Đọc các lượt của hội thoại theo thứ tự thời gian và ghép ngữ cảnh đúng."""
    # Tạo hội thoại mới
    ht = await tao_hoi_thoai(phien_csdl, nguoi_id=nguoi_dung_test.id, tieu_de="Hội thoại ngữ cảnh")
    await phien_csdl.commit()

    moc_goc = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Thêm 4 lượt với mốc thời gian tăng dần
    noi_dung_cac_luot = [
        ("nguoi_dung", "Hỏi tiền điện tháng 8"),
        ("tro_ly", "Tiền điện tháng 8 của Anh/Chị là 1.200.000 đ."),
        ("nguoi_dung", "Hỏi tiền điện tháng 9"),
        ("tro_ly", "Tiền điện tháng 9 của Anh/Chị là 1.450.000 đ."),
    ]

    for i, (vai_tro, noi_dung) in enumerate(noi_dung_cac_luot):
        phien_csdl.add(
            LuotModel(
                hoi_thoai_id=ht.id,
                vai_tro=vai_tro,
                noi_dung=noi_dung,
                token_vao=10,
                token_ra=20,
                tao_luc=moc_goc + timedelta(minutes=i),
            )
        )
    await phien_csdl.commit()

    # Đọc lại từ CSDL qua lay_danh_sach_luot
    cac_luot_db = await lay_danh_sach_luot(phien_csdl, ht.id)
    assert len(cac_luot_db) == 4
    assert [l.noi_dung for l in cac_luot_db] == [item[1] for item in noi_dung_cac_luot]

    # Chuyển đổi sang format tin nhắn cho dung_ngu_canh
    lich_su_tin_nhan = []
    for l in cac_luot_db:
        role = "user" if l.vai_tro == "nguoi_dung" else "assistant"
        lich_su_tin_nhan.append({"role": role, "content": l.noi_dung})

    # Dựng ngữ cảnh với tin nhắn mới
    chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=4096, nguon="local")]
    kq_ngu_canh = dung_ngu_canh(lich_su_tin_nhan, "Tháng nào dùng nhiều hơn?", chuoi)

    # Tin nhắn đầu là lời nhắc hệ thống, sau đó đến các cặp lịch sử theo đúng thứ tự thời gian
    tin_nhan_danh_sach = kq_ngu_canh.danh_sach
    assert tin_nhan_danh_sach[0]["role"] == "system"
    assert tin_nhan_danh_sach[1]["content"] == "Hỏi tiền điện tháng 8"
    assert tin_nhan_danh_sach[2]["content"] == "Tiền điện tháng 8 của Anh/Chị là 1.200.000 đ."
    assert tin_nhan_danh_sach[3]["content"] == "Hỏi tiền điện tháng 9"
    assert tin_nhan_danh_sach[4]["content"] == "Tiền điện tháng 9 của Anh/Chị là 1.450.000 đ."
    assert tin_nhan_danh_sach[5]["content"] == "Tháng nào dùng nhiều hơn?"


@pytest.mark.asyncio
async def test_so_lieu_do_luu_day_du(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
) -> None:
    """2. Lưu cả lượt người dùng và lượt trả lời trong MỘT giao dịch với đầy đủ số liệu đo."""
    ht = await tao_hoi_thoai(phien_csdl, nguoi_id=nguoi_dung_test.id, tieu_de="Đo lường")
    await phien_csdl.commit()

    kq_mau = KetQuaGoi(
        noi_dung="Chào Anh/Chị, tôi có thể hỗ trợ tra cứu hóa đơn điện.",
        nguon="local",
        tang=0,
        bac_local="chinh",
        ten_model="qwen3.5:9b-q4_K_M",
        token_vao=45,
        token_ra=92,
        chi_phi_usd=0.0,
        do_tre_ms=312.5,
        thoi_gian_nap_ms=18.4,
        toc_do_tok_s=28.7,
        da_cat_ngu_canh=False,
        so_luot_bi_cat=0,
    )

    pb_prompt = doc_phien_ban_loi_nhac()
    _luot_nguoi, _luot_tro_ly = await luu_cap_luot_hoi_thoai(
        phien_csdl,
        hoi_thoai_id=ht.id,
        noi_dung_nguoi="Chào trợ lý",
        noi_dung_tro_ly=kq_mau.noi_dung,
        kq_goi=kq_mau,
        ma_yeu_cau="yc_do_luong_123",
        nhan_du_lieu="THUONG",
        phien_ban_prompt=pb_prompt,
    )
    await phien_csdl.commit()

    # Truy vấn lại từ bảng luot
    cau_lenh = (
        select(LuotModel)
        .where(LuotModel.hoi_thoai_id == ht.id)
        .order_by(LuotModel.tao_luc.asc(), LuotModel.id.asc())
    )
    ket_qua = (await phien_csdl.scalars(cau_lenh)).all()
    assert len(ket_qua) == 2

    # Kiểm tra lượt người dùng
    l_user = ket_qua[0]
    assert l_user.vai_tro == "nguoi_dung"
    assert l_user.noi_dung == "Chào trợ lý"
    assert l_user.ma_yeu_cau == "yc_do_luong_123"
    assert l_user.nhan_du_lieu == "THUONG"
    assert l_user.phien_ban_loi_nhac == pb_prompt

    # Kiểm tra lượt trợ lý với đầy đủ thông số đo đạc kỹ thuật
    l_bot = ket_qua[1]
    assert l_bot.vai_tro == "tro_ly"
    assert l_bot.noi_dung == kq_mau.noi_dung
    assert l_bot.nguon == "local"
    assert l_bot.tang == 0
    assert l_bot.bac_local == "chinh"
    assert l_bot.model_da_dung == "qwen3.5:9b-q4_K_M"
    assert l_bot.token_vao == 45
    assert l_bot.token_ra == 92
    assert l_bot.chi_phi_usd == 0.0
    assert l_bot.do_tre_ms == 312.5
    assert l_bot.thoi_gian_nap_ms == 18.4
    assert l_bot.toc_do_tok_s == 28.7
    assert l_bot.da_cat_ngu_canh is False
    assert l_bot.so_luot_bi_cat == 0
    assert l_bot.phien_ban_loi_nhac == pb_prompt
    assert l_bot.ma_yeu_cau == "yc_do_luong_123"


@pytest.mark.asyncio
async def test_tu_dat_tieu_de_uu_tien_bac_nho_khong_goi_dam_may(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3. Tự đặt tiêu đề BUỘC dùng tầng 0 bậc nho (hoặc bậc chinh khi so_model_nap_cung_luc=1), không gọi đám mây."""
    ht = await tao_hoi_thoai(phien_csdl, nguoi_id=nguoi_dung_test.id, tieu_de="Cuộc trò chuyện mới")
    await phien_csdl.commit()

    bac_duoc_chon: list[str] = []

    async def _mock_goi_local(*args: Any, **kwargs: Any) -> KetQuaGoiLocal:
        uu_tien_nho = kwargs.get("uu_tien_bac_nho", False)
        assert uu_tien_nho is True, "Phải truyền uu_tien_bac_nho=True cho goi_local"

        # Kiểm tra bậc được chọn theo cấu hình so_model_nap_cung_luc
        if cau_hinh.so_model_nap_cung_luc == 1:
            bac = "chinh"
            model = cau_hinh.bac_local[0].model
        else:
            bac = "nho"
            model = cau_hinh.bac_local[1].model

        bac_duoc_chon.append(bac)
        return KetQuaGoiLocal(
            noi_dung="Tra cứu hóa đơn điện",
            model=model,
            bac=bac,
            thoi_gian_nap_ms=0.0,
            do_tre_ms=120.0,
            toc_do_tok_s=25.0,
            token_vao=30,
            token_ra=6,
            ma_yeu_cau="tieu_de_test",
        )

    mock_dam_may = AsyncMock()
    monkeypatch.setattr("app.llm.router.goi_local", _mock_goi_local)
    monkeypatch.setattr("app.llm.router.goi_dam_may", mock_dam_may)

    # Chạy tác vụ tự đặt tiêu đề
    await tu_dat_tieu_de(
        hoi_thoai_id=ht.id,
        noi_dung_nguoi="Xem tiền điện tháng này",
        noi_dung_tro_ly="Tiền điện là 1.200.000 đ",
        nguoi=nguoi_dung_test,
    )

    # Tuyệt đối không có lời gọi đám mây nào phát sinh
    assert mock_dam_may.call_count == 0
    # Đã gọi local đúng bậc
    assert len(bac_duoc_chon) == 1
    if cau_hinh.so_model_nap_cung_luc == 1:
        assert bac_duoc_chon[0] == "chinh"
    else:
        assert bac_duoc_chon[0] == "nho"

    # Kiểm tra tiêu đề đã được cập nhật trong CSDL
    await phien_csdl.refresh(ht)
    assert ht.tieu_de == "Tra cứu hóa đơn điện"


@pytest.mark.asyncio
async def test_xoa_hoi_thoai_cascade_luot(
    phien_csdl: AsyncSession,
    nguoi_dung_test: NguoiDung,
) -> None:
    """4. Xóa hội thoại thì các lượt liên kết bị xóa theo qua ON DELETE CASCADE."""
    ht = await tao_hoi_thoai(phien_csdl, nguoi_id=nguoi_dung_test.id, tieu_de="Hội thoại sắp xoá")
    await phien_csdl.commit()

    # Thêm 2 lượt vào hội thoại
    phien_csdl.add(LuotModel(hoi_thoai_id=ht.id, vai_tro="nguoi_dung", noi_dung="Xin chào"))
    phien_csdl.add(LuotModel(hoi_thoai_id=ht.id, vai_tro="tro_ly", noi_dung="Chào bạn"))
    await phien_csdl.commit()

    # Xác nhận 2 lượt tồn tại
    danh_sach_truoc = await lay_danh_sach_luot(phien_csdl, ht.id)
    assert len(danh_sach_truoc) == 2

    # Xóa hội thoại
    da_xoa = await xoa_hoi_thoai(phien_csdl, ht.id)
    assert da_xoa is True
    await phien_csdl.commit()

    # Kiểm tra hội thoại đã bị xóa
    ht_check = await lay_hoi_thoai(phien_csdl, ht.id)
    assert ht_check is None

    # Kiểm tra toàn bộ các lượt thuộc hội thoại cũng đã bị xóa khỏi CSDL
    cau_lenh_luot = select(LuotModel).where(LuotModel.hoi_thoai_id == ht.id)
    luot_con_lai = (await phien_csdl.scalars(cau_lenh_luot)).all()
    assert len(luot_con_lai) == 0
