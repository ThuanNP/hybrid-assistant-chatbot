"""Định nghĩa các ngoại lệ tùy biến và xử lý lỗi hệ thống."""

from typing import Any


class LoiHeThong(Exception):
    """Lớp cơ sở cho toàn bộ ngoại lệ nghiệp vụ của hệ thống trợ lý AI."""

    def __init__(self, thong_diep: str, *, ma_yeu_cau: str = "") -> None:
        super().__init__(thong_diep)
        self.thong_diep = thong_diep
        self.ma_yeu_cau = ma_yeu_cau


class LoiDauVao(LoiHeThong):
    """Ngoại lệ khi yêu cầu gửi tới bộ chạy không hợp lệ (mã lỗi HTTP 4xx).

    Lỗi này do dữ liệu đầu vào hoặc tham số sai, cần sửa mã nguồn hoặc dữ liệu gửi đi,
    tuyệt đối không được phép tự động hạ cấp sang bậc mô hình tiếp theo.
    """

    def __init__(
        self,
        thong_diep: str,
        *,
        ma_trang_thai: int = 400,
        ma_yeu_cau: str = "",
        chi_tiet: Any = None,
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.ma_trang_thai = ma_trang_thai
        self.chi_tiet = chi_tiet


class LoiHetBacLocal(LoiHeThong):
    """Ngoại lệ khi cả hai bậc mô hình local (chính và nhỏ) đều thất bại.

    Router sẽ bắt ngoại lệ này để quyết định chuyển sang tầng đám mây
    hoặc trả về câu thông báo lỗi có kiểm soát cho người dùng.
    """

    def __init__(
        self,
        thong_diep: str,
        *,
        ly_do_bac_1: str | None = None,
        ly_do_bac_2: str | None = None,
        ma_yeu_cau: str = "",
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.ly_do_bac_1 = ly_do_bac_1
        self.ly_do_bac_2 = ly_do_bac_2
