"""Điều phối yêu cầu đồng thời và kiểm soát giới hạn hàng đợi cho mô hình local.

Quản lý số lượng yêu cầu gọi mô hình local chạy đồng thời thông qua semaphore
và xếp hàng các yêu cầu vượt quá khả năng xử lý tức thời.
"""

import asyncio
import logging
import statistics
import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field

from app.config import cau_hinh
from app.core.loi import LoiHangDoiDay

logger = logging.getLogger(__name__)

__all__ = ["DieuPhoi", "TrangThaiHangDoi", "ViTri", "dieu_phoi_mac_dinh"]


class ViTri(BaseModel):
    """Thông tin vị trí xếp hàng và thời gian ước lượng hoàn thành."""

    vi_tri: int = Field(ge=1, description="Thứ tự xếp hàng của yêu cầu (bắt đầu từ 1)")
    uoc_luong_giay: float = Field(ge=0.0, description="Thời gian chờ ước lượng tính bằng giây")


class TrangThaiHangDoi(BaseModel):
    """Ảnh chụp trạng thái vận hành hiện tại của hàng đợi điều phối local."""

    dang_chay: int = Field(ge=0, description="Số lượng yêu cầu đang được mô hình xử lý")
    dang_cho: int = Field(ge=0, description="Số lượng yêu cầu đang xếp hàng chờ lượt")
    thoi_gian_cho_trung_vi: float = Field(
        ge=0.0,
        description="Thời gian xử lý trung vị của tối đa 20 yêu cầu gần nhất",
    )
    so_bi_tu_choi_1_gio: int = Field(
        ge=0,
        description="Số lượng yêu cầu bị từ chối do hàng đợi đầy trong 1 giờ qua",
    )
    do_dai_toi_da: int = Field(
        ge=0,
        description="Sức chứa tối đa của hàng đợi; vượt mức này yêu cầu mới bị từ chối",
    )

    def __getitem__(self, item: str) -> Any:
        """Hỗ trợ truy cập dữ liệu theo cú pháp khóa từ điển."""
        return getattr(self, item)


class DieuPhoi:
    """Bộ điều phối giới hạn đồng thời và hàng đợi xử lý cho mô hình local tầng 0."""

    def __init__(
        self,
        so_luong_dong_thoi: int | None = None,
        do_dai_hang_doi_toi_da: int | None = None,
        thoi_gian_mac_dinh_giay: float = 5.0,
    ) -> None:
        # Giá trị này phải KHỚP với OLLAMA_NUM_PARALLEL; đặt cao hơn không làm nhanh hơn,
        # chỉ đẩy hàng đợi vào bên trong bộ chạy, nơi không quan sát được.
        self.so_luong_dong_thoi = (
            so_luong_dong_thoi
            if so_luong_dong_thoi is not None
            else cau_hinh.so_luong_dong_thoi
        )
        self.do_dai_hang_doi_toi_da = (
            do_dai_hang_doi_toi_da
            if do_dai_hang_doi_toi_da is not None
            else cau_hinh.do_dai_hang_doi_toi_da
        )
        self.thoi_gian_mac_dinh_giay = thoi_gian_mac_dinh_giay

        self._semaphore = asyncio.Semaphore(max(1, self.so_luong_dong_thoi))
        self._dang_chay: int = 0
        self._dang_cho: int = 0
        self._thoi_gian_xu_ly: deque[float] = deque(maxlen=20)
        self._tu_choi_timestamps: list[float] = []

    @property
    def dang_chay(self) -> int:
        """Số lượng yêu cầu local đang trong tiến trình chạy thực tế."""
        return self._dang_chay

    @property
    def dang_cho(self) -> int:
        """Số lượng yêu cầu đang chờ trong hàng đợi."""
        return self._dang_cho

    @property
    def thoi_gian_cho_trung_vi(self) -> float:
        """Thời gian xử lý trung vị của tối đa 20 yêu cầu local gần nhất."""
        if not self._thoi_gian_xu_ly:
            return self.thoi_gian_mac_dinh_giay
        return round(float(statistics.median(self._thoi_gian_xu_ly)), 2)

    @property
    def so_bi_tu_choi_1_gio(self) -> int:
        """Số lượt yêu cầu bị từ chối do quá tải hàng đợi trong vòng 1 giờ qua."""
        moc_mot_gio = time.time() - 3600.0
        self._tu_choi_timestamps = [ts for ts in self._tu_choi_timestamps if ts >= moc_mot_gio]
        return len(self._tu_choi_timestamps)

    def kiem_tra_hang_doi_day(self) -> bool:
        """Kiểm tra số lượng yêu cầu đang chờ đã vượt ngưỡng tối đa hay chưa."""
        return self._dang_cho >= self.do_dai_hang_doi_toi_da

    def ghi_nhan_tu_choi(self) -> None:
        """Ghi nhận thời điểm một yêu cầu bị từ chối do hàng đợi đầy."""
        self._tu_choi_timestamps.append(time.time())

    def ghi_nhan_thoi_gian(self, thoi_gian_giay: float) -> None:
        """Lưu lại thời gian hoàn thành của một yêu cầu local vào lịch sử gần nhất."""
        if thoi_gian_giay > 0:
            self._thoi_gian_xu_ly.append(thoi_gian_giay)

    def can_vao_hang(self) -> bool:
        """Kiểm tra có cần phải xếp hàng chờ do toàn bộ slot đồng thời đã bận hay không."""
        return (
            self._dang_cho > 0
            or self._semaphore.locked()
            or self._dang_chay >= self.so_luong_dong_thoi
        )

    async def bat_dau_chay_ngay(self, ma_yeu_cau: str = "") -> None:
        """Bắt đầu chạy ngay lập tức mà không cần qua hàng đợi chờ (khi có slot rảnh)."""
        await self._semaphore.acquire()
        self._dang_chay += 1

    async def vao_hang(self, ma_yeu_cau: str = "") -> ViTri:
        """Đăng ký yêu cầu vào hàng đợi và nhận vị trí cùng thời gian ước tính."""
        if self.kiem_tra_hang_doi_day():
            self.ghi_nhan_tu_choi()
            logger.warning(
                "[%s] Hàng đợi local đã đầy (%d/%d yêu cầu)",
                ma_yeu_cau,
                self._dang_cho,
                self.do_dai_hang_doi_toi_da,
            )
            raise LoiHangDoiDay(
                f"Hàng đợi xử lý cục bộ đã đầy ({self._dang_cho}/{self.do_dai_hang_doi_toi_da})",
                ma_yeu_cau=ma_yeu_cau,
            )

        self._dang_cho += 1
        vi_tri = self._dang_cho
        uoc_luong = round(vi_tri * self.thoi_gian_cho_trung_vi, 2)
        return ViTri(vi_tri=vi_tri, uoc_luong_giay=uoc_luong)

    async def cho_den_luot(self, ma_yeu_cau: str = "") -> None:
        """Chờ đợi chiếm quyền semaphore để bắt đầu thực thi yêu cầu."""
        await self._semaphore.acquire()
        self._dang_cho = max(0, self._dang_cho - 1)
        self._dang_chay += 1

    def giai_phong(self, thoi_gian_giay: float | None = None) -> None:
        """Giải phóng quyền thực thi và ghi nhận thời gian chạy hoàn tất."""
        self._dang_chay = max(0, self._dang_chay - 1)
        self._semaphore.release()
        if thoi_gian_giay is not None:
            self.ghi_nhan_thoi_gian(thoi_gian_giay)

    def huy_cho(self) -> None:
        """Rút yêu cầu ra khỏi hàng đợi khi bị hủy hoặc gặp lỗi trước khi chạy."""
        self._dang_cho = max(0, self._dang_cho - 1)

    @asynccontextmanager
    async def quan_ly_hang_doi(self, ma_yeu_cau: str = "") -> AsyncIterator[ViTri]:
        """Context manager quản lý toàn bộ vòng đời xếp hàng và thực thi local."""
        vi_tri = await self.vao_hang(ma_yeu_cau)
        da_chay = False
        t0 = 0.0
        try:
            await self.cho_den_luot(ma_yeu_cau)
            da_chay = True
            t0 = time.perf_counter()
            yield vi_tri
        finally:
            if da_chay:
                thoi_gian_chay = time.perf_counter() - t0
                self.giai_phong(thoi_gian_chay)
            else:
                self.huy_cho()

    def trang_thai(self) -> TrangThaiHangDoi:
        """Trả về thông tin trạng thái hoạt động hiện tại của hàng đợi."""
        return TrangThaiHangDoi(
            dang_chay=self.dang_chay,
            dang_cho=self.dang_cho,
            thoi_gian_cho_trung_vi=self.thoi_gian_cho_trung_vi,
            so_bi_tu_choi_1_gio=self.so_bi_tu_choi_1_gio,
            do_dai_toi_da=self.do_dai_hang_doi_toi_da,
        )


# Đối tượng điều phối mặc định cho toàn bộ ứng dụng
dieu_phoi_mac_dinh = DieuPhoi()
