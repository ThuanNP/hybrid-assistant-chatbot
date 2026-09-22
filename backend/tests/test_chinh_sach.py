"""Bộ kiểm thử cho chính sách bảo vệ dữ liệu nhạy cảm và định tuyến mô hình.

Căn cứ: Quy tắc tuyệt đối 2 trong AGENTS.md.
"""

from app.config import cau_hinh
from app.llm.chinh_sach import (
    CheDoDinhTuyen,
    NhanDuLieu,
    ThongTinNguoiDung,
    nhan_cua_hoi_thoai,
    phat_hien_nhay_cam,
    xac_dinh_chuoi,
)


def test_tin_nhan_chua_ma_khach_hang_chi_co_tang_0() -> None:
    """Tin nhắn chứa mã khách hàng KH00012345 thì chuỗi chỉ có duy nhất tầng 0."""
    tin_nhan = "Khách hàng có mã KH00012345 cần tra cứu chỉ số sử dụng."
    assert phat_hien_nhay_cam(tin_nhan) is True

    nhan = nhan_cua_hoi_thoai(lich_su=[], tin_nhan_moi=tin_nhan)
    assert nhan == NhanDuLieu.NHAY_CAM

    kq = xac_dinh_chuoi(
        nguoi=None,
        nhan_du_lieu=nhan,
        che_do=CheDoDinhTuyen.LOCAL_TRUOC,
    )
    assert [t.so for t in kq.chuoi] == [0]
    assert kq.chuoi[0].nguon == "local"
    assert kq.ly_do_chuoi == "du_lieu_nhay_cam"


def test_dam_may_truoc_nhung_nhay_cam_van_chi_tang_0() -> None:
    """Dù chế độ là dam_may_truoc nhưng dữ liệu nhạy cảm thì vẫn chỉ được dùng tầng 0."""
    kq = xac_dinh_chuoi(
        nguoi=None,
        nhan_du_lieu=NhanDuLieu.NHAY_CAM,
        che_do=CheDoDinhTuyen.DAM_MAY_TRUOC,
    )
    assert [t.so for t in kq.chuoi] == [0]
    assert kq.chuoi[0].nguon == "local"
    assert kq.ly_do_chuoi == "du_lieu_nhay_cam"


def test_phong_ban_cham_soc_khach_hang_chi_tang_0() -> None:
    """Người dùng thuộc phòng ban CHAM_SOC_KHACH_HANG chỉ được dùng tầng 0."""
    nguoi = ThongTinNguoiDung(
        ma_nguoi_dung="NV_CSKH_01",
        phong_ban="CHAM_SOC_KHACH_HANG",
    )
    # Câu hỏi nghiệp vụ thông thường, không chứa dữ liệu nhạy cảm
    cau_hoi = "Quy trình tiếp nhận báo mất điện như thế nào?"
    nhan = nhan_cua_hoi_thoai(lich_su=[], tin_nhan_moi=cau_hoi)
    assert nhan == NhanDuLieu.THUONG

    # Dù cấu hình yêu cầu đám mây trước, người thuộc CSKH vẫn bị giới hạn local
    kq = xac_dinh_chuoi(
        nguoi=nguoi,
        nhan_du_lieu=nhan,
        che_do=CheDoDinhTuyen.DAM_MAY_TRUOC,
    )
    assert [t.so for t in kq.chuoi] == [0]
    assert kq.chuoi[0].nguon == "local"
    assert "phong_ban_chi_local" in kq.ly_do_chuoi


def test_luot_thu_ba_hoi_thoai_co_so_dien_thoai_o_luot_dau_chi_tang_0() -> None:
    """Lượt thứ ba hỏi thông thường nhưng lượt đầu có SĐT thì chuỗi chỉ có tầng 0."""
    lich_su = [
        {"vai_tro": "user", "noi_dung": "Số điện thoại của tôi là 0900 000 001"},
        {"vai_tro": "assistant", "noi_dung": "Dạ, em đã ghi nhận số điện thoại của anh."},
    ]
    tin_nhan_moi = "Cách tính tiền điện bậc thang hiện hành như thế nào?"

    # Tin nhắn mới tự thân nó không nhạy cảm
    assert phat_hien_nhay_cam(tin_nhan_moi) is False

    # Nhưng xét theo toàn bộ hội thoại thì ngữ cảnh chứa thông tin nhạy cảm ở lượt 1
    nhan_ht = nhan_cua_hoi_thoai(lich_su=lich_su, tin_nhan_moi=tin_nhan_moi)
    assert nhan_ht == NhanDuLieu.NHAY_CAM

    kq = xac_dinh_chuoi(
        nguoi=None,
        nhan_du_lieu=nhan_ht,
        che_do=CheDoDinhTuyen.LOCAL_TRUOC,
    )
    assert [t.so for t in kq.chuoi] == [0]
    assert kq.ly_do_chuoi == "du_lieu_nhay_cam"


def test_thieu_anthropic_api_key_khong_co_tang_3_trong_chuoi() -> None:
    """Khi thiếu ANTHROPIC_API_KEY, tầng 3 (claude) bị loại khỏi chuỗi định tuyến."""
    ch_gia_lap = cau_hinh.model_copy(deep=True)
    for t in ch_gia_lap.chuoi_dam_may:
        # Giả lập tầng 3 thiếu khóa, các tầng 1, 2, 4 sẵn sàng
        t.kha_dung = t.tang != 3

    kq = xac_dinh_chuoi(
        nguoi=None,
        nhan_du_lieu=NhanDuLieu.THUONG,
        che_do=CheDoDinhTuyen.LOCAL_TRUOC,
        cau_hinh_he_thong=ch_gia_lap,
    )
    danh_sach_tang = [t.so for t in kq.chuoi]
    assert 3 not in danh_sach_tang
    assert danh_sach_tang == [0, 1, 2, 4]


def test_local_truoc_cau_hoi_thuong_dung_thu_tu_01234() -> None:
    """Chế độ local_truoc với câu hỏi thường sắp xếp đúng thứ tự 0, 1, 2, 3, 4."""
    ch_gia_lap = cau_hinh.model_copy(deep=True)
    for t in ch_gia_lap.chuoi_dam_may:
        t.kha_dung = True

    nguoi_cntt = ThongTinNguoiDung(ma_nguoi_dung="NV_CNTT_01", phong_ban="CNTT")
    kq = xac_dinh_chuoi(
        nguoi=nguoi_cntt,
        nhan_du_lieu=NhanDuLieu.THUONG,
        che_do=CheDoDinhTuyen.LOCAL_TRUOC,
        cau_hinh_he_thong=ch_gia_lap,
    )
    danh_sach_tang = [t.so for t in kq.chuoi]
    assert danh_sach_tang == [0, 1, 2, 3, 4]
    assert kq.ly_do_chuoi == "local_truoc"
