"""Tạo bảng phien_dang_nhap, nhat_ky_kiem_toan và đổi ten_dang_nhap thành email.

Revision ID: 003_xac_thuc_phien_va_kiem_toan
Revises: 002_luot_goi_roi_tang
Create Date: 2026-09-23 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "003_xac_thuc_phien_va_kiem_toan"
down_revision: str | None = "002_luot_goi_roi_tang"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Đổi ten_dang_nhap sang email, tạo bảng phien_dang_nhap và nhat_ky_kiem_toan."""
    # 1. Đổi tên cột ten_dang_nhap thành email trong bảng nguoi_dung (giữ nguyên unique constraint)
    op.alter_column("nguoi_dung", "ten_dang_nhap", new_column_name="email")

    # 2. Cập nhật dữ liệu cũ: chuyển email không có @ sang dạng email@vidu.com
    op.execute(
        sa.text(
            "UPDATE nguoi_dung SET email = email || '@vidu.com' WHERE email NOT LIKE '%@%'"
        )
    )

    # 3. Đổi bậc cũ 'chinh' thành 'free'
    op.execute(
        sa.text(
            "UPDATE nguoi_dung SET bac = 'free' WHERE bac = 'chinh' OR bac IS NULL"
        )
    )

    # 4. Đồng bộ chuỗi tự tăng (sequence) của bảng nguoi_dung
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('nguoi_dung', 'id'), coalesce(max(id), 0) + 1, false) FROM nguoi_dung"
        )
    )

    # 5. Tạo bảng phien_dang_nhap
    op.create_table(
        "phien_dang_nhap",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nguoi_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_bam", sa.String(length=255), nullable=False),
        sa.Column("het_han_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "thu_hoi",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "tao_luc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["nguoi_id"], ["nguoi_dung.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_phien_dang_nhap_nguoi_id",
        "phien_dang_nhap",
        ["nguoi_id"],
    )
    op.create_index(
        "ix_phien_dang_nhap_refresh_token_bam",
        "phien_dang_nhap",
        ["refresh_token_bam"],
    )

    # 6. Tạo bảng nhat_ky_kiem_toan
    op.create_table(
        "nhat_ky_kiem_toan",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "thoi_diem",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nguoi_id", sa.Integer(), nullable=True),
        sa.Column("hanh_dong", sa.String(length=100), nullable=False),
        sa.Column("chi_tiet", postgresql.JSONB(), nullable=True),
        sa.Column("ma_yeu_cau", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nhat_ky_kiem_toan_thoi_diem",
        "nhat_ky_kiem_toan",
        ["thoi_diem"],
    )


def downgrade() -> None:
    """Thu hồi thay đổi của migration 003."""
    op.drop_index("ix_nhat_ky_kiem_toan_thoi_diem", table_name="nhat_ky_kiem_toan")
    op.drop_table("nhat_ky_kiem_toan")

    op.drop_index("ix_phien_dang_nhap_refresh_token_bam", table_name="phien_dang_nhap")
    op.drop_index("ix_phien_dang_nhap_nguoi_id", table_name="phien_dang_nhap")
    op.drop_table("phien_dang_nhap")

    op.alter_column("nguoi_dung", "email", new_column_name="ten_dang_nhap")
