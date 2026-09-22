"""Cấu hình thực thi di chuyển lược đồ cơ sở dữ liệu Alembic."""

import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Đặt WindowsSelectorEventLoopPolicy trên Windows vì psycopg async không chạy với Proactor
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.config import cau_hinh
from app.core.csdl import Base, chuan_hoa_url_csdl

# Đọc cấu hình tệp alembic.ini
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Gán URL kết nối cơ sở dữ liệu đã chuẩn hóa từ cấu hình hệ thống
url_csdl = chuan_hoa_url_csdl(cau_hinh.database_url)
config.set_main_option("sqlalchemy.url", url_csdl)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy di chuyển ở chế độ offline sinh câu lệnh SQL."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Thực thi di chuyển trong ngữ cảnh kết nối đồng bộ được uỷ quyền."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Khởi tạo AsyncEngine và thực thi di chuyển bất đồng bộ."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Chạy di chuyển ở chế độ online kết nối cơ sở dữ liệu thực."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
