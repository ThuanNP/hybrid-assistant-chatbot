"""Khởi tạo 4 bảng cơ sở dữ liệu: nguoi_dung, hoi_thoai, luot, luot_goi.

Revision ID: 001_khoi_tao_bon_bang
Revises:
Create Date: 2026-09-23 03:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "001_khoi_tao_bon_bang"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Tạo mới 4 bảng cốt lõi và các chỉ mục tương ứng."""
    # 1. Bảng nguoi_dung
    op.create_table(
        "nguoi_dung",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ten_dang_nhap", sa.String(length=100), nullable=False),
        sa.Column("mat_khau_bam", sa.String(length=255), nullable=True),
        sa.Column("ho_ten", sa.String(length=255), nullable=False),
        sa.Column("vai_tro", sa.String(length=50), nullable=False),
        sa.Column("bac", sa.String(length=50), nullable=True),
        sa.Column("phong_ban", sa.String(length=100), nullable=False),
        sa.Column("dang_hoat_dong", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "tao_luc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ten_dang_nhap"),
    )

    # 2. Bảng hoi_thoai
    op.create_table(
        "hoi_thoai",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nguoi_id", sa.Integer(), nullable=False),
        sa.Column("tieu_de", sa.String(length=255), nullable=False),
        sa.Column(
            "tao_luc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "cap_nhat_luc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("da_xoa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["nguoi_id"], ["nguoi_dung.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hoi_thoai_nguoi_id_cap_nhat_luc",
        "hoi_thoai",
        ["nguoi_id", "cap_nhat_luc"],
    )

    # 3. Bảng luot
    op.create_table(
        "luot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hoi_thoai_id", sa.Integer(), nullable=False),
        sa.Column("vai_tro", sa.String(length=20), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("nguon", sa.String(length=20), nullable=True),
        sa.Column("tang", sa.Integer(), nullable=True),
        sa.Column("bac_local", sa.String(length=50), nullable=True),
        sa.Column("model_da_dung", sa.String(length=100), nullable=True),
        sa.Column("token_vao", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("token_ra", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "chi_phi_usd",
            postgresql.DOUBLE_PRECISION(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column("toc_do_tok_s", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("thoi_gian_nap_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("do_tre_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("da_cat_ngu_canh", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("so_luot_bi_cat", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("nhan_du_lieu", sa.String(length=50), nullable=True),
        sa.Column("nguon_tham_chieu", postgresql.JSONB(), nullable=True),
        sa.Column("phien_ban_loi_nhac", sa.String(length=50), nullable=True),
        sa.Column("ma_yeu_cau", sa.String(length=50), nullable=True),
        sa.Column(
            "tao_luc",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["hoi_thoai_id"], ["hoi_thoai.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_luot_hoi_thoai_id_tao_luc",
        "luot",
        ["hoi_thoai_id", "tao_luc"],
    )

    # 4. Bảng luot_goi
    op.create_table(
        "luot_goi",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "thoi_diem",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nguoi_id", sa.String(length=100), nullable=False),
        sa.Column("nguon", sa.String(length=50), nullable=False),
        sa.Column("tang", sa.Integer(), nullable=False),
        sa.Column("bac", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("token_vao", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("token_ra", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "chi_phi_usd",
            postgresql.DOUBLE_PRECISION(),
            server_default=sa.text("0.0"),
            nullable=False,
        ),
        sa.Column("do_tre_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("thoi_gian_nap_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("toc_do_tok_s", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("thanh_cong", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ma_yeu_cau", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_luot_goi_thoi_diem",
        "luot_goi",
        ["thoi_diem"],
    )
    op.create_index(
        "ix_luot_goi_nguoi_id_thoi_diem",
        "luot_goi",
        ["nguoi_id", "thoi_diem"],
    )


def downgrade() -> None:
    """Thu hồi toàn bộ 4 bảng và các chỉ mục liên quan."""
    op.drop_index("ix_luot_goi_nguoi_id_thoi_diem", table_name="luot_goi")
    op.drop_index("ix_luot_goi_thoi_diem", table_name="luot_goi")
    op.drop_table("luot_goi")

    op.drop_index("ix_luot_hoi_thoai_id_tao_luc", table_name="luot")
    op.drop_table("luot")

    op.drop_index("ix_hoi_thoai_nguoi_id_cap_nhat_luc", table_name="hoi_thoai")
    op.drop_table("hoi_thoai")

    op.drop_table("nguoi_dung")
