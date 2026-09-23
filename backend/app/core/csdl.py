"""Quản lý kết nối cơ sở dữ liệu PostgreSQL (SQLAlchemy 2 async, psycopg).

Cung cấp session factory bất đồng bộ, dependency lay_phien() cho FastAPI,
engine đồng bộ cho kho dữ liệu lượt gọi, và định nghĩa 4 bảng ORM cốt lõi:
nguoi_dung, hoi_thoai, luot, luot_goi.
"""

import os
import sys
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import cau_hinh

# Đặt WindowsSelectorEventLoopPolicy trên Windows vì psycopg async không chạy với Proactor
if sys.platform == "win32":
    import asyncio

    if not isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def chuan_hoa_url_csdl(url: str | None) -> str:
    """Chuẩn hóa URL kết nối PostgreSQL cho cả môi trường container và máy phát triển."""
    if not url:
        raise RuntimeError("DATABASE_URL chưa được cấu hình trong hệ thống")

    url_chuan = url
    # Trên máy Windows ngoài container, localhost thường ưu tiên IPv6 ::1 gây nghẽn kết nối
    if not os.path.exists("/.dockerenv"):
        url_chuan = url_chuan.replace("@localhost:", "@127.0.0.1:").replace(
            "@db:", "@127.0.0.1:"
        )
    return url_chuan


class Base(DeclarativeBase):
    """Lớp cơ sở cho toàn bộ các mô hình bảng ORM trong hệ thống."""



class NguoiDungModel(Base):
    """Bảng lưu trữ thông tin cán bộ công nhân viên sử dụng hệ thống."""

    __tablename__ = "nguoi_dung"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ten_dang_nhap: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    mat_khau_bam: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ho_ten: Mapped[str] = mapped_column(String(255), nullable=False)
    vai_tro: Mapped[str] = mapped_column(String(50), nullable=False)
    bac: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phong_ban: Mapped[str] = mapped_column(String(100), nullable=False)
    dang_hoat_dong: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    tao_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    hoi_thoai_list: Mapped[list["HoiThoaiModel"]] = relationship(
        back_populates="nguoi_dung", cascade="all, delete-orphan"
    )


class HoiThoaiModel(Base):
    """Bảng lưu trữ phiên hội thoại giữa người dùng và trợ lý AI."""

    __tablename__ = "hoi_thoai"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nguoi_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nguoi_dung.id"), nullable=False
    )
    tieu_de: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Cuộc trò chuyện mới"
    )
    tao_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    cap_nhat_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    da_xoa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    nguoi_dung: Mapped["NguoiDungModel"] = relationship(back_populates="hoi_thoai_list")
    luot_list: Mapped[list["LuotModel"]] = relationship(
        back_populates="hoi_thoai",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_hoi_thoai_nguoi_id_cap_nhat_luc", "nguoi_id", "cap_nhat_luc"),
    )


class LuotModel(Base):
    """Bảng lưu trữ từng lượt trao đổi (tin nhắn) trong một phiên hội thoại."""

    __tablename__ = "luot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hoi_thoai_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hoi_thoai.id", ondelete="CASCADE"),
        nullable=False,
    )
    vai_tro: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # he_thong | nguoi_dung | tro_ly
    noi_dung: Mapped[str] = mapped_column(Text, nullable=False)
    nguon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tang: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bac_local: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_da_dung: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_vao: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    token_ra: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    chi_phi_usd: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, default=0.0, server_default=text("0.0"), nullable=False
    )
    toc_do_tok_s: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    thoi_gian_nap_ms: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    do_tre_ms: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    da_cat_ngu_canh: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    so_luot_bi_cat: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    nhan_du_lieu: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nguon_tham_chieu: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    phien_ban_loi_nhac: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ma_yeu_cau: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    hoi_thoai: Mapped["HoiThoaiModel"] = relationship(back_populates="luot_list")

    __table_args__ = (
        Index("ix_luot_hoi_thoai_id_tao_luc", "hoi_thoai_id", "tao_luc"),
    )


class LuotGoiModel(Base):
    """Bảng ghi nhận lịch sử các lượt gọi mô hình phục vụ theo dõi ngân sách và chi phí."""

    __tablename__ = "luot_goi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thoi_diem: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    nguoi_id: Mapped[str] = mapped_column(String(100), nullable=False)
    nguon: Mapped[str] = mapped_column(String(50), nullable=False)
    tang: Mapped[int] = mapped_column(Integer, nullable=False)
    bac: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    token_vao: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    token_ra: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    chi_phi_usd: Mapped[float] = mapped_column(
        DOUBLE_PRECISION, default=0.0, server_default=text("0.0"), nullable=False
    )
    do_tre_ms: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    thoi_gian_nap_ms: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    toc_do_tok_s: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0.0"), nullable=False
    )
    thanh_cong: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    ma_yeu_cau: Mapped[str] = mapped_column(String(50), nullable=False)
    roi_tang: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    ly_do_that_bai_tang_dau: Mapped[str | None] = mapped_column(String(100), nullable=True)
    muc_dich: Mapped[str] = mapped_column(
        String(20), default="chat", server_default=text("'chat'"), nullable=False
    )

    __table_args__ = (
        Index("ix_luot_goi_thoi_diem", "thoi_diem"),
        Index("ix_luot_goi_nguoi_id_thoi_diem", "nguoi_id", "thoi_diem"),
    )


# Quản lý vòng đời Async Engine và Sessionmaker
_async_engine: AsyncEngine | None = None
_async_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def lay_engine_async() -> AsyncEngine:
    """Khởi tạo hoặc tái sử dụng AsyncEngine duy nhất cho ứng dụng."""
    global _async_engine
    if _async_engine is None:
        url = chuan_hoa_url_csdl(cau_hinh.database_url)
        _async_engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _async_engine


def lay_sessionmaker_async() -> async_sessionmaker[AsyncSession]:
    """Khởi tạo hoặc lấy factory phiên làm việc bất đồng bộ."""
    global _async_sessionmaker
    if _async_sessionmaker is None:
        engine = lay_engine_async()
        _async_sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_sessionmaker


async def lay_phien() -> AsyncIterator[AsyncSession]:
    """Dependency cung cấp phiên làm việc bất đồng bộ cho FastAPI endpoints."""
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        yield phien


# Engine đồng bộ phục vụ riêng cho các phương thức đồng bộ của KhoLuotGoi
_sync_engine = None


def lay_engine_dong_bo():
    """Khởi tạo hoặc lấy sync engine cho các thao tác đồng bộ."""
    global _sync_engine
    if _sync_engine is None:
        url = chuan_hoa_url_csdl(cau_hinh.database_url)
        _sync_engine = create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _sync_engine
