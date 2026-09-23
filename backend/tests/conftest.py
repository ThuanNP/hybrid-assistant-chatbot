"""Cấu hình các fixture dùng chung cho bộ kiểm thử pytest."""

import asyncio
import sys
from collections.abc import AsyncIterator

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

# Đặt WindowsSelectorEventLoopPolicy trên Windows vì psycopg async không chạy với Proactor
if sys.platform == "win32":
    if not isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.csdl import NguoiDungModel, lay_sessionmaker_async
from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.main import app


@pytest.fixture(autouse=True)
def override_xac_thuc_mac_dinh() -> Any:
    """Tự động override lay_nguoi_dung_hien_tai cho các bài test kế thừa từ Giai đoạn 1-4."""
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: NguoiDung()
    yield
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)


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
            email="can_bo@vidu.com",
            mat_khau_bam=None,
            ho_ten="Cán bộ kiểm thử",
            vai_tro="nguoi_dung",
            bac="free",
            phong_ban="CNTT",
            dang_hoat_dong=True,
        )
        phien_csdl.add(nd_model)
        await phien_csdl.commit()

    return NguoiDung(
        id=1,
        email="can_bo@vidu.com",
        ho_ten="Cán bộ kiểm thử",
        vai_tro="nguoi_dung",
        bac="free",
        phong_ban="CNTT",
    )
