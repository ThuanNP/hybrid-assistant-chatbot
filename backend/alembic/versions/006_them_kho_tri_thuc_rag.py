"""Thêm kho tri thức RAG: bảng tai_lieu, doan, pgvector và cấu hình tìm kiếm tiếng Việt.

Revision ID: 006_them_kho_tri_thuc_rag
Revises: 005_them_do_dai_hang_doi_luot
Create Date: 2026-09-24 09:15:00.000000

GHI CHÚ VỀ CẤU HÌNH TÌM KIẾM TIẾNG VIỆT:
Tiếng Việt là ngôn ngữ đơn lập (isolating language), các âm tiết/từ không có biến đổi
hình thái ngữ pháp (không thêm tiếp vĩ ngữ chia thì hay số nhiều như -ing, -ed, -s...
trong tiếng Anh). Do đó, cấu hình tách từ tiếng Anh (english configuration với bộ
Porter stemmer) tuyệt đối KHÔNG được dùng vì sẽ cắt xén méo mó các từ tiếng Việt và
loại bỏ sai hư từ. Hệ thống cấu hình 'tieng_viet' kế thừa từ 'simple' kết hợp từ điển
'unaccent' để giữ trọn vẹn từ ngữ, đồng thời cho phép tìm kiếm linh hoạt cả khi gõ
có dấu lẫn không dấu.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Định danh bản sửa đổi của Alembic
revision: str = "006_them_kho_tri_thuc_rag"
down_revision: str | None = "005_them_do_dai_hang_doi_luot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Tạo extensions, cấu hình FTS tiếng Việt, bảng tai_lieu, doan và chỉ mục."""
    # 1. Kích hoạt tiện ích mở rộng vector và unaccent
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 2. Tạo cấu hình tìm kiếm toàn văn tiếng Việt (simple + unaccent)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'tieng_viet'
            ) THEN
                CREATE TEXT SEARCH CONFIGURATION tieng_viet (COPY = simple);
                ALTER TEXT SEARCH CONFIGURATION tieng_viet
                    ALTER MAPPING FOR hword, hword_part, word
                    WITH unaccent, simple;
            END IF;
        END $$;
        """
    )

    # 3. Tạo bảng tai_lieu
    op.create_table(
        "tai_lieu",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ma_tai_lieu", sa.String(length=100), nullable=False),
        sa.Column("tieu_de", sa.Text(), nullable=False),
        sa.Column("nguon", sa.String(length=255), nullable=True),
        sa.Column("loai_van_ban", sa.String(length=100), nullable=True),
        sa.Column("tinh_trang", sa.String(length=50), nullable=False),
        sa.Column(
            "pham_vi_doc", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column("van_ban_thay_the", sa.String(length=255), nullable=True),
        sa.Column("ngay_ban_hanh", sa.Date(), nullable=False),
        sa.Column("ngay_het_hieu_luc", sa.Date(), nullable=True),
        sa.Column("don_vi_quan_ly", sa.String(length=255), nullable=True),
        sa.Column("model_nhung", sa.String(length=100), nullable=False),
        sa.Column("bam_noi_dung", sa.String(length=64), nullable=True),
        sa.Column("nguoi_nap", sa.String(length=100), nullable=True),
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
        sa.CheckConstraint(
            "tinh_trang IN ('con_hieu_luc', 'het_hieu_luc', 'du_thao')",
            name="ck_tai_lieu_tinh_trang",
        ),
        sa.CheckConstraint(
            "(tinh_trang != 'het_hieu_luc') OR (van_ban_thay_the IS NOT NULL AND van_ban_thay_the != '')",
            name="ck_tai_lieu_van_ban_thay_the",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ma_tai_lieu"),
    )
    op.create_index(
        "ix_tai_lieu_ma_tai_lieu", "tai_lieu", ["ma_tai_lieu"], unique=False
    )

    # 4. Tạo bảng doan
    op.execute(
        """
        CREATE TABLE doan (
            id SERIAL PRIMARY KEY,
            tai_lieu_id INTEGER NOT NULL REFERENCES tai_lieu(id) ON DELETE CASCADE,
            thu_tu INTEGER NOT NULL,
            tieu_de_muc TEXT NOT NULL,
            duong_dan_muc TEXT,
            noi_dung TEXT NOT NULL,
            so_token INTEGER NOT NULL DEFAULT 0,
            vector vector(1024),
            tsv tsvector
        );
        """
    )

    # 5. Tạo các chỉ mục cho bảng doan
    # Btree trên (tai_lieu_id, thu_tu)
    op.create_index(
        "ix_doan_tai_lieu_id_thu_tu",
        "doan",
        ["tai_lieu_id", "thu_tu"],
        unique=False,
    )
    # HNSW trên vector với vector_cosine_ops
    op.execute(
        "CREATE INDEX ix_doan_vector_hnsw ON doan USING hnsw (vector vector_cosine_ops);"
    )
    # GIN trên tsv
    op.execute("CREATE INDEX ix_doan_tsv_gin ON doan USING gin (tsv);")

    # 6. Tạo trigger tự động sinh cột tsv bằng cấu hình tieng_viet
    op.execute(
        """
        CREATE OR REPLACE FUNCTION doan_tsv_trigger() RETURNS trigger AS $$
        BEGIN
            new.tsv := to_tsvector(
                'tieng_viet',
                coalesce(new.tieu_de_muc, '') || ' ' || coalesce(new.noi_dung, '')
            );
            RETURN new;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_doan_tsv_update
        BEFORE INSERT OR UPDATE OF tieu_de_muc, noi_dung ON doan
        FOR EACH ROW EXECUTE FUNCTION doan_tsv_trigger();
        """
    )


def downgrade() -> None:
    """Thu hồi toàn bộ thay đổi của migration 006."""
    op.execute("DROP TRIGGER IF EXISTS trg_doan_tsv_update ON doan;")
    op.execute("DROP FUNCTION IF EXISTS doan_tsv_trigger();")
    op.execute("DROP TABLE IF EXISTS doan CASCADE;")
    op.execute("DROP TABLE IF EXISTS tai_lieu CASCADE;")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS tieng_viet;")
