"""Các lược đồ dữ liệu Pydantic phục vụ nạp và truy xuất kho tri thức RAG."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SieuDuLieuTaiLieu(BaseModel):
    """Siêu dữ liệu tài liệu kho tri thức dùng chung cho nạp dữ liệu và API.

    Các trường bắt buộc không được gán mặc định; nếu thiếu dữ liệu sẽ bị từ chối.
    Khi tình trạng là 'het_hieu_luc', bắt buộc phải cung cấp văn bản thay thế.
    """

    ma_tai_lieu: str = Field(..., min_length=1, description="Mã định danh duy nhất của tài liệu")
    tieu_de: str = Field(..., min_length=1, description="Tiêu đề tài liệu")
    tinh_trang: Literal["con_hieu_luc", "het_hieu_luc", "du_thao"] = Field(
        ..., description="Tình trạng hiệu lực của tài liệu"
    )
    pham_vi_doc: list[str] = Field(..., min_length=1, description="Danh sách phòng ban/vai trò được xem")
    ngay_ban_hanh: date = Field(..., description="Ngày ban hành văn bản")
    model_nhung: str = Field(..., min_length=1, description="Tên mô hình nhúng dùng tạo vector")

    # Các trường tuỳ chọn
    nguon: str | None = None
    loai_van_ban: str | None = None
    van_ban_thay_the: str | None = None
    ngay_het_hieu_luc: date | None = None
    don_vi_quan_ly: str | None = None
    bam_noi_dung: str | None = None
    nguoi_nap: str | None = None

    @model_validator(mode="after")
    def kiem_tra_van_ban_thay_the(self) -> "SieuDuLieuTaiLieu":
        """Văn bản hết hiệu lực bắt buộc phải có thông tin văn bản thay thế."""
        if self.tinh_trang == "het_hieu_luc" and (
            not self.van_ban_thay_the or not self.van_ban_thay_the.strip()
        ):
            raise ValueError("Văn bản hết hiệu lực bắt buộc phải có văn bản thay thế.")
        return self


class NguonThamChieu(BaseModel):
    """Cấu trúc một nguồn trích dẫn tham chiếu cho lượt trả lời của trợ lý."""

    ma_tai_lieu: str
    tieu_de_muc: str
    doan_id: int
    diem: float
