"""Thêm cột do_dai_hang_doi vào bảng luot.

Revision ID: 005_them_do_dai_hang_doi_luot
Revises: 004_tao_bang_han_muc_dem
Create Date: 2026-09-24 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "005_them_do_dai_hang_doi_luot"
down_revision: str | None = "004_tao_bang_han_muc_dem"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Thêm cột do_dai_hang_doi vào bảng luot."""
    op.add_column(
        "luot",
        sa.Column(
            "do_dai_hang_doi",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Thu hồi thay đổi của migration 005."""
    op.drop_column("luot", "do_dai_hang_doi")
