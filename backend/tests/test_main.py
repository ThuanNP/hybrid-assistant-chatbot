"""Bộ kiểm thử cho điểm nhập FastAPI backend/app/main.py."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod


def test_health_tra_phien_ban_tu_pyproject() -> None:
    """/health trả 200 kèm phien_ban đọc từ backend/pyproject.toml."""
    with TestClient(main_mod.app) as client:
        phan_hoi = client.get("/health")

    assert phan_hoi.status_code == 200
    assert phan_hoi.json()["phien_ban"] == main_mod.doc_phien_ban()


def test_khoi_dong_khong_bi_chan_khi_bo_chay_hong(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hâm nóng chạy nền: bộ chạy hỏng hoặc chậm không làm hỏng khởi động."""

    async def kiem_tra_cham_roi_hong() -> None:
        await asyncio.sleep(0.05)
        raise RuntimeError("bộ chạy không phản hồi")

    monkeypatch.setattr(main_mod, "kiem_tra_khi_khoi_dong", kiem_tra_cham_roi_hong)
    with TestClient(main_mod.app) as client:
        assert client.get("/health").status_code == 200
