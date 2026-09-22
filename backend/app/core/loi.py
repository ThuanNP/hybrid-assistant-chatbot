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


class LoiTamThoi(LoiHeThong):
    """Ngoại lệ khi gặp lỗi tạm thời (429, 500, 502, 503, 504, quá hạn, lỗi mạng).

    Lỗi này có thể tự phục hồi, được phép thử lại tối đa số lần cấu hình với
    chính sách giãn cách lũy thừa trước khi router quyết định chuyển tầng.
    """

    def __init__(
        self,
        thong_diep: str,
        *,
        ma_trang_thai: int | None = None,
        ma_yeu_cau: str = "",
        chi_tiet: Any = None,
        so_lan_thu: int = 1,
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.ma_trang_thai = ma_trang_thai
        self.chi_tiet = chi_tiet
        self.so_lan_thu = so_lan_thu


class LoiVinhVien(LoiHeThong):
    """Ngoại lệ khi gặp lỗi vĩnh viễn (401 sai khoá, 403 không có quyền, 404 sai model).

    Lỗi cấu hình hoặc quyền hạn không thể tự phục hồi, tuyệt đối không thử lại,
    router sẽ lập tức chuyển sang tầng tiếp theo trong chuỗi định tuyến.
    """

    def __init__(
        self,
        thong_diep: str,
        *,
        ma_trang_thai: int | None = None,
        ma_yeu_cau: str = "",
        chi_tiet: Any = None,
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.ma_trang_thai = ma_trang_thai
        self.chi_tiet = chi_tiet
