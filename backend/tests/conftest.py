"""Cấu hình các fixture dùng chung cho bộ kiểm thử pytest."""

import asyncio
import sys
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Đặt WindowsSelectorEventLoopPolicy trên Windows vì psycopg async không chạy với Proactor
if sys.platform == "win32":
    if not isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
from app.core.xac_thuc import NguoiDung


@pytest_asyncio.fixture
async def phien_csdl() -> AsyncIterator[AsyncSession]:
    """Fixture cung cấp phiên làm việc bất đồng bộ kết nối cơ sở dữ liệu thật."""
    maker = lay_sessionmaker_async()
    async with maker() as phien:
        yield phien


@pytest_asyncio.fixture
async def nguoi_dung_test(phien_csdl: AsyncSession) -> NguoiDung:
    """Fixture đảm bảo người dùng giả lập id=1 tồn tại trong CSDL cho các kiểm thử."""
    nd_model = await phien_csdl.get(NguoiDungModel, 1)
    if nd_model is None:
        nd_model = NguoiDungModel(
            id=1,
            ten_dang_nhap="can_bo",
            mat_khau_bam=None,
            ho_ten="Cán bộ kiểm thử",
            vai_tro="nguoi_dung",
            bac="chinh",
            phong_ban="CNTT",
            dang_hoat_dong=True,
        )
        phien_csdl.add(nd_model)
        await phien_csdl.commit()

    return NguoiDung(
        id=1,
        ten_dang_nhap="can_bo",
        ho_ten="Cán bộ kiểm thử",
        vai_tro="nguoi_dung",
        bac="chinh",
        phong_ban="CNTT",
    )
