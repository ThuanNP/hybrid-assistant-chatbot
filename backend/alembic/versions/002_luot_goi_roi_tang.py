"""Bổ sung cột rơi tầng và mục đích cho bảng luot_goi.

Revision ID: 002_luot_goi_roi_tang
Revises: 001_khoi_tao_bon_bang
Create Date: 2026-09-23 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "002_luot_goi_roi_tang"
down_revision: str | None = "001_khoi_tao_bon_bang"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Thêm roi_tang, ly_do_that_bai_tang_dau và muc_dich vào luot_goi."""
    op.add_column(
        "luot_goi",
        sa.Column("roi_tang", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    # Chỉ lưu loại lỗi (ví dụ LoiTamThoi, HANG_DOI_DAY), không lưu nội dung tin nhắn
    op.add_column(
        "luot_goi",
        sa.Column("ly_do_that_bai_tang_dau", sa.String(length=100), nullable=True),
    )
    # chat: lượt hỏi của người dùng; tieu_de: lời gọi nền đặt tiêu đề, không tính vào KPI
    op.add_column(
        "luot_goi",
        sa.Column(
            "muc_dich",
            sa.String(length=20),
            server_default=sa.text("'chat'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Thu hồi ba cột đã thêm."""
    op.drop_column("luot_goi", "muc_dich")
    op.drop_column("luot_goi", "ly_do_that_bai_tang_dau")
    op.drop_column("luot_goi", "roi_tang")
