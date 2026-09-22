"""Điểm nhập chính khởi chạy ứng dụng FastAPI."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import tomllib
from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse

from app.chat.su_kien_sse import YeuCauChatStream, tao_luong_su_kien
from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.llm.bo_chay_local import kiem_tra_khi_khoi_dong

logger = logging.getLogger(__name__)

# Header chuẩn Server-Sent Events ngăn proxy và nginx đệm luồng dữ liệu
HEADER_SSE = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

# pyproject.toml là nguồn duy nhất của số phiên bản backend (.agents/rules/versioning.md)
DUONG_DAN_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def doc_phien_ban() -> str:
    """Đọc số phiên bản từ backend/pyproject.toml."""
    with DUONG_DAN_PYPROJECT.open("rb") as tep:
        return str(tomllib.load(tep)["project"]["version"])


PHIEN_BAN = doc_phien_ban()


def _ghi_loi_tac_vu_nen(tac_vu: asyncio.Task[None]) -> None:
    """Ghi nhật ký lỗi của tác vụ nền thay vì để lỗi bị bỏ qua lặng lẽ."""
    if tac_vu.cancelled():
        return
    loi = tac_vu.exception()
    if loi is not None:
        logger.error("Kiểm tra bộ chạy lúc khởi động thất bại: %r", loi)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Hâm nóng bậc 1 và so ngữ cảnh ở chế độ nền để không chặn khởi động."""
    tac_vu = asyncio.create_task(kiem_tra_khi_khoi_dong())
    tac_vu.add_done_callback(_ghi_loi_tac_vu_nen)
    yield
    tac_vu.cancel()


app = FastAPI(title="Trợ lý AI nội bộ", version=PHIEN_BAN, lifespan=lifespan)


@app.get("/health")
async def kiem_tra_song() -> dict[str, str]:
    """Chỉ xác nhận tiến trình còn sống; không truy cập cơ sở dữ liệu hay bộ chạy."""
    return {"trang_thai": "song", "phien_ban": PHIEN_BAN}


@app.post("/api/v1/chat/stream")
async def chat_stream(
    yeu_cau: YeuCauChatStream,
    request: Request,
    nguoi: Annotated[NguoiDung, Depends(lay_nguoi_dung_hien_tai)],
) -> StreamingResponse:
    """Endpoint phát phản hồi hội thoại theo dòng (SSE) qua chuỗi định tuyến lai."""
    return StreamingResponse(
        tao_luong_su_kien(yeu_cau, request, nguoi),
        media_type="text/event-stream",
        headers=HEADER_SSE,
    )
