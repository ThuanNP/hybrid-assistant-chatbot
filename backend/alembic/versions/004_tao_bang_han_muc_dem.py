"""Tạo bảng han_muc_dem lưu trữ cửa sổ trượt hạn mức.

Revision ID: 004_tao_bang_han_muc_dem
Revises: 003_xac_thuc_phien_va_kiem_toan
Create Date: 2026-09-24 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "004_tao_bang_han_muc_dem"
down_revision: str | None = "003_xac_thuc_phien_va_kiem_toan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Tạo bảng han_muc_dem và chỉ mục phục vụ kiểm soát hạn mức cửa sổ trượt."""
    op.create_table(
        "han_muc_dem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("khoa", sa.String(length=100), nullable=False),
        sa.Column(
            "thoi_diem",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_han_muc_dem_khoa_thoi_diem",
        "han_muc_dem",
        ["khoa", "thoi_diem"],
    )


def downgrade() -> None:
    """Thu hồi thay đổi của migration 004."""
    op.drop_index("ix_han_muc_dem_khoa_thoi_diem", table_name="han_muc_dem")
    op.drop_table("han_muc_dem")
