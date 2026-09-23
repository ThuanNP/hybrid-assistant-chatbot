"""Tiện ích thời gian theo giờ Việt Nam cho số liệu "hôm nay" và bộ lọc ngày."""

from datetime import date, datetime, time, timedelta, timezone

__all__ = ["MUI_GIO_VN", "hom_nay_vn", "khoang_ngay_vn"]

# Việt Nam không dùng giờ mùa hè nên độ lệch cố định UTC+7 là đủ, không cần gói tzdata
# (Python trên Windows không kèm cơ sở dữ liệu múi giờ).
MUI_GIO_VN = timezone(timedelta(hours=7), "ICT")


def hom_nay_vn() -> date:
    """Ngày hiện tại theo giờ Việt Nam."""
    return datetime.now(MUI_GIO_VN).date()


def khoang_ngay_vn(ngay: date) -> tuple[datetime, datetime]:
    """Trả [đầu ngày, đầu ngày kế tiếp) của một ngày theo giờ Việt Nam, quy về UTC."""
    dau_ngay = datetime.combine(ngay, time.min, tzinfo=MUI_GIO_VN)
    return dau_ngay.astimezone(timezone.utc), (dau_ngay + timedelta(days=1)).astimezone(
        timezone.utc
    )
