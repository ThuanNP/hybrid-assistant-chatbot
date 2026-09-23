"""Định nghĩa các ngoại lệ tùy biến, chuẩn hóa mã lỗi và bộ bắt lỗi toàn cục."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.nhat_ky import lay_ma_yeu_cau

logger = logging.getLogger(__name__)


class LoiHeThong(Exception):
    """Lớp cơ sở cho toàn bộ ngoại lệ nghiệp vụ của hệ thống trợ lý AI."""

    def __init__(self, thong_diep: str, *, ma_yeu_cau: str = "") -> None:
        super().__init__(thong_diep)
        self.thong_diep = thong_diep
        self.ma_yeu_cau = ma_yeu_cau


class LoiUngDung(LoiHeThong):
    """Ngoại lệ ứng dụng chuẩn hóa có mã lỗi, thông điệp người dùng và mã trạng thái HTTP."""

    def __init__(
        self,
        ma: str,
        thong_diep: str,
        http: int = 500,
        *,
        ma_yeu_cau: str = "",
        chi_tiet: Any = None,
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.ma = ma
        self.http = http
        self.chi_tiet = chi_tiet


class LoiDauVao(LoiHeThong):
    """Ngoại lệ khi yêu cầu gửi tới bộ chạy không hợp lệ (mã lỗi HTTP 4xx)."""

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
    """Ngoại lệ khi cả hai bậc mô hình local (chính và nhỏ) đều thất bại."""

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
    """Ngoại lệ khi gặp lỗi tạm thời (429, 500, 502, 503, 504, quá hạn, lỗi mạng)."""

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
    """Ngoại lệ khi gặp lỗi vĩnh viễn (401 sai khoá, 403 không có quyền, 404 sai model)."""

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


class LoiHetChuoiDuPhong(LoiHeThong):
    """Ngoại lệ khi toàn bộ các tầng trong chuỗi định tuyến dự phòng đều thất bại."""

    def __init__(
        self,
        thong_diep: str,
        *,
        danh_sach_ly_do: dict[int, str] | None = None,
        ma_yeu_cau: str = "",
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.danh_sach_ly_do = danh_sach_ly_do or {}
        self.ly_do = self.danh_sach_ly_do


class LoiNguCanhQuaDai(LoiHeThong):
    """Ngoại lệ khi riêng lời nhắc hệ thống cộng tin nhắn mới vượt ngân sách ngữ cảnh."""

    ma_loi: str = "NGU_CANH_QUA_DAI"

    def __init__(
        self,
        thong_diep: str = "Ngữ cảnh hội thoại vượt quá ngân sách cho phép của mô hình",
        *,
        ma_yeu_cau: str = "",
        so_token: int = 0,
        ngan_sach: int = 0,
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)
        self.so_token = so_token
        self.ngan_sach = ngan_sach


NGU_CANH_QUA_DAI = LoiNguCanhQuaDai


class LoiHangDoiDay(LoiHeThong):
    """Ngoại lệ khi hàng đợi cục bộ vượt quá giới hạn tối đa cho phép."""

    ma_loi: str = "HANG_DOI_DAY"

    def __init__(
        self,
        thong_diep: str = "Hàng đợi xử lý cục bộ đã đầy",
        *,
        ma_yeu_cau: str = "",
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)


HANG_DOI_DAY = LoiHangDoiDay


class LoiVuotNganSach(LoiHeThong):
    """Ngoại lệ khi chi phí gọi mô hình đám mây vượt quá ngân sách cho phép."""

    ma_loi: str = "VUOT_NGAN_SACH"

    def __init__(
        self,
        thong_diep: str = "Vượt ngân sách gọi mô hình đám mây trong ngày",
        *,
        ma_yeu_cau: str = "",
    ) -> None:
        super().__init__(thong_diep, ma_yeu_cau=ma_yeu_cau)


VUOT_NGAN_SACH = LoiVuotNganSach

# Mã lỗi chỉ xuất hiện trong sự kiện SSE "loi" khi luồng bị ngắt sau khi đã phát mảnh;
# HTTP vẫn là 200 vì luồng đã mở, nên không có mục ánh xạ HTTP, chỉ có thông điệp.
LOI_DONG = "LOI_DONG"


# Thông điệp ngắn gọn hiển thị cho người dùng theo từng mã lỗi chuẩn hóa
THONG_DIEP_LOI: dict[str, str] = {
    "HANG_DOI_DAY": "Hệ thống đang bận, vui lòng thử lại sau.",
    "QUA_HAN": "Hết thời gian chờ, vui lòng thử lại.",
    "NGU_CANH_QUA_DAI": "Tin nhắn quá dài, vui lòng rút gọn.",
    "BO_CHAY_KHONG_PHAN_HOI": "Mô hình nội bộ không phản hồi, vui lòng thử lại sau.",
    "DICH_VU_TAM_NGUNG": "Dịch vụ tạm gián đoạn, vui lòng thử lại sau.",
    "HET_CHUOI_DU_PHONG": "Không mô hình nào phản hồi, vui lòng thử lại sau.",
    "VUOT_NGAN_SACH": "Đã hết hạn mức sử dụng AI trong ngày.",
    "VUOT_HAN_MUC": "Gửi quá nhiều yêu cầu, vui lòng thử lại sau.",
    "KHONG_CO_QUYEN": "Bạn không có quyền thực hiện thao tác này.",
    "CHUA_XAC_THUC": "Chưa đăng nhập hoặc phiên đã hết hạn.",
    "DAU_VAO_KHONG_HOP_LE": "Dữ liệu không hợp lệ.",
    "NOI_DUNG_BI_CHAN": "Nội dung vi phạm chính sách kiểm duyệt.",
    "KHONG_TIM_THAY": "Không tìm thấy dữ liệu yêu cầu.",
    "LOI_DONG": "Phản hồi bị gián đoạn, vui lòng gửi lại.",
    "LOI_HE_THONG": "Lỗi hệ thống, vui lòng thử lại sau.",
}


def _muc(ma: str, http: int, thong_diep: str | None = None) -> tuple[str, int, str]:
    """Tạo một mục bảng ánh xạ, mặc định lấy thông điệp chuẩn của mã lỗi."""
    return ma, http, thong_diep or THONG_DIEP_LOI[ma]


# Bảng ánh xạ mã lỗi hoặc tên lớp ngoại lệ sang mã chuẩn hóa, trạng thái HTTP, thông điệp
BANG_ANH_XA_LOI: dict[str, tuple[str, int, str]] = {
    "HANG_DOI_DAY": _muc("HANG_DOI_DAY", 503),
    "LoiHangDoiDay": _muc("HANG_DOI_DAY", 503),
    "QUA_HAN": _muc("QUA_HAN", 504),
    "TimeoutError": _muc("QUA_HAN", 504),
    "NGU_CANH_QUA_DAI": _muc("NGU_CANH_QUA_DAI", 422),
    "LoiNguCanhQuaDai": _muc("NGU_CANH_QUA_DAI", 422),
    "BO_CHAY_KHONG_PHAN_HOI": _muc("BO_CHAY_KHONG_PHAN_HOI", 503),
    "LoiHetBacLocal": _muc("BO_CHAY_KHONG_PHAN_HOI", 503),
    "DICH_VU_TAM_NGUNG": _muc("DICH_VU_TAM_NGUNG", 503),
    "HET_CHUOI_DU_PHONG": _muc("HET_CHUOI_DU_PHONG", 503),
    "LoiHetChuoiDuPhong": _muc("HET_CHUOI_DU_PHONG", 503),
    "VUOT_NGAN_SACH": _muc("VUOT_NGAN_SACH", 503),
    "LoiVuotNganSach": _muc("VUOT_NGAN_SACH", 503),
    "VUOT_HAN_MUC": _muc("VUOT_HAN_MUC", 429),
    "KHONG_CO_QUYEN": _muc("KHONG_CO_QUYEN", 403),
    "CHUA_XAC_THUC": _muc("CHUA_XAC_THUC", 401),
    "DAU_VAO_KHONG_HOP_LE": _muc("DAU_VAO_KHONG_HOP_LE", 422),
    "LoiDauVao": _muc(
        "DAU_VAO_KHONG_HOP_LE", 422, "Mô hình từ chối yêu cầu, vui lòng sửa nội dung."
    ),
    "NOI_DUNG_BI_CHAN": _muc("NOI_DUNG_BI_CHAN", 422),
    "KHONG_TIM_THAY": _muc("KHONG_TIM_THAY", 404),
    "LOI_HE_THONG": _muc("LOI_HE_THONG", 500),
}

# Ánh xạ mã trạng thái HTTP tiêu chuẩn sang mã lỗi nội bộ
BANG_HTTP_SANG_MA_LOI: dict[int, str] = {
    400: "DAU_VAO_KHONG_HOP_LE",
    401: "CHUA_XAC_THUC",
    403: "KHONG_CO_QUYEN",
    404: "KHONG_TIM_THAY",
    422: "DAU_VAO_KHONG_HOP_LE",
    429: "VUOT_HAN_MUC",
    503: "DICH_VU_TAM_NGUNG",
    504: "QUA_HAN",
}


def tao_noi_dung_loi(
    ma: str, thong_diep: str, ma_yeu_cau: str
) -> dict[str, dict[str, str]]:
    """Tạo cấu trúc phản hồi lỗi chuẩn tuân thủ hợp đồng giao diện API."""
    return {
        "loi": {
            "ma": ma,
            "thong_diep": thong_diep,
            "ma_yeu_cau": ma_yeu_cau,
        }
    }


def chuyen_doi_loi_sang_loi_ung_dung(
    err: Exception, ma_yeu_cau: str = ""
) -> LoiUngDung:
    """Chuyển đổi ngoại lệ bất kỳ sang đối tượng LoiUngDung chuẩn hóa."""
    ma_yc = ma_yeu_cau or lay_ma_yeu_cau()
    if isinstance(err, LoiUngDung):
        if not err.ma_yeu_cau:
            err.ma_yeu_cau = ma_yc
        return err

    ten_lop = type(err).__name__
    ma_loi_lop = getattr(err, "ma_loi", None)

    # 1-2. Tìm theo ma_loi rồi theo tên lớp. Thông điệp nội bộ của ngoại lệ (lỗi thô
    # từ bộ chạy, tên nhà cung cấp, chi phí...) chỉ ghi nhật ký; người dùng nhận câu chuẩn.
    khoa_bang = ma_loi_lop if ma_loi_lop in BANG_ANH_XA_LOI else ten_lop
    if khoa_bang in BANG_ANH_XA_LOI:
        ma, http, td = BANG_ANH_XA_LOI[khoa_bang]
        return LoiUngDung(ma=ma, thong_diep=td, http=http, ma_yeu_cau=ma_yc)

    # 3. Lỗi HTTP (FastAPI hoặc Starlette): luôn dùng thông điệp chuẩn, không trả detail
    if isinstance(err, StarletteHTTPException):
        ma_mac_dinh = (
            "DAU_VAO_KHONG_HOP_LE" if err.status_code < 500 else "LOI_HE_THONG"
        )
        ma = BANG_HTTP_SANG_MA_LOI.get(err.status_code, ma_mac_dinh)
        return LoiUngDung(
            ma=ma, thong_diep=THONG_DIEP_LOI[ma], http=err.status_code, ma_yeu_cau=ma_yc
        )

    # 4. Mặc định trả về lỗi hệ thống 500
    return LoiUngDung(
        ma="LOI_HE_THONG",
        thong_diep=THONG_DIEP_LOI["LOI_HE_THONG"],
        http=500,
        ma_yeu_cau=ma_yc,
    )


def dang_ky_bo_bat_loi(app: FastAPI) -> None:
    """Đăng ký các bộ xử lý lỗi toàn cục cho ứng dụng FastAPI.

    Bảo đảm mọi phản hồi lỗi đều có mã yêu cầu, thông điệp tiếng Việt dễ hiểu
    và không bao giờ làm rò rỉ vết ngăn xếp (Traceback) ra ngoài.
    """

    @app.exception_handler(LoiUngDung)
    async def _xu_ly_loi_ung_dung(request: Request, exc: LoiUngDung) -> JSONResponse:
        ma_yc = exc.ma_yeu_cau or lay_ma_yeu_cau()
        logger.warning("[%s] Lỗi ứng dụng (%s): %s", ma_yc, exc.ma, exc.thong_diep)
        return JSONResponse(
            status_code=exc.http,
            content=tao_noi_dung_loi(exc.ma, exc.thong_diep, ma_yc),
            headers={"X-Ma-Yeu-Cau": ma_yc},
        )

    @app.exception_handler(LoiHeThong)
    async def _xu_ly_loi_he_thong(request: Request, exc: LoiHeThong) -> JSONResponse:
        ma_yc = exc.ma_yeu_cau or lay_ma_yeu_cau()
        loi_ud = chuyen_doi_loi_sang_loi_ung_dung(exc, ma_yc)
        logger.warning(
            "[%s] Ngoại lệ nghiệp vụ (%s): %s", ma_yc, loi_ud.ma, exc.thong_diep
        )
        return JSONResponse(
            status_code=loi_ud.http,
            content=tao_noi_dung_loi(loi_ud.ma, loi_ud.thong_diep, ma_yc),
            headers={"X-Ma-Yeu-Cau": ma_yc},
        )

    @app.exception_handler(RequestValidationError)
    async def _xu_ly_loi_pydantic(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        ma_yc = lay_ma_yeu_cau()
        # Chỉ ghi vị trí và loại lỗi; trường "input" có thể chứa nội dung tin nhắn
        cac_truong = sorted(
            {
                ".".join(str(p) for p in e["loc"] if p != "body") or "body"
                for e in exc.errors()
            }
        )
        logger.info(
            "[%s] Dữ liệu đầu vào không hợp lệ: %s",
            ma_yc,
            [(e["loc"], e["type"]) for e in exc.errors()],
        )
        return JSONResponse(
            status_code=422,
            content=tao_noi_dung_loi(
                "DAU_VAO_KHONG_HOP_LE",
                f"Dữ liệu không hợp lệ ở trường: {', '.join(cac_truong)}.",
                ma_yc,
            ),
            headers={"X-Ma-Yeu-Cau": ma_yc},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _xu_ly_loi_http(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        ma_yc = lay_ma_yeu_cau()
        loi_ud = chuyen_doi_loi_sang_loi_ung_dung(exc, ma_yc)
        return JSONResponse(
            status_code=exc.status_code,
            content=tao_noi_dung_loi(loi_ud.ma, loi_ud.thong_diep, ma_yc),
            headers={"X-Ma-Yeu-Cau": ma_yc},
        )

    @app.exception_handler(Exception)
    async def _xu_ly_loi_bat_ky(request: Request, exc: Exception) -> JSONResponse:
        ma_yc = lay_ma_yeu_cau()
        # Vết ngăn xếp CHỈ ghi vào nhật ký, TUYỆT ĐỐI không trả ra ngoài
        logger.error(
            "[%s] Lỗi hệ thống không lường trước: %s",
            ma_yc,
            exc,
            exc_info=True,  # noqa: LOG014
        )
        return JSONResponse(
            status_code=500,
            content=tao_noi_dung_loi(
                "LOI_HE_THONG",
                THONG_DIEP_LOI["LOI_HE_THONG"],
                ma_yc,
            ),
            headers={"X-Ma-Yeu-Cau": ma_yc},
        )
