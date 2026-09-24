"""Thêm cột tu_choi và diem_cao_nhat vào bảng luot.

Revision ID: 007_them_tu_choi_luot
Revises: 006_them_kho_tri_thuc_rag
Create Date: 2026-09-24 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Định danh bản sửa đổi của Alembic (tối đa 32 ký tự theo alembic_version)
revision: str = "007_them_tu_choi_luot"
down_revision: str | None = "006_them_kho_tri_thuc_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Thêm cột tu_choi và diem_cao_nhat vào bảng luot."""
    op.add_column(
        "luot",
        sa.Column(
            "tu_choi",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "luot",
        sa.Column(
            "diem_cao_nhat",
            sa.Float(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Thu hồi thay đổi của migration 007."""
    op.drop_column("luot", "diem_cao_nhat")
    op.drop_column("luot", "tu_choi")
