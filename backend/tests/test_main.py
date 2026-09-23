"""Bộ kiểm thử cho điểm nhập FastAPI backend/app/main.py."""

import asyncio
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod

THU_MUC_BACKEND = Path(__file__).resolve().parents[1]


def test_prod_tat_tai_lieu_api() -> None:
    """MOI_TRUONG=prod: /docs, /redoc, /openapi.json đều trả 404.

    Chạy ở tiến trình con vì cờ prod được đọc một lần khi nạp app.main.
    """
    ma_lenh = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "print(*(c.get(p).status_code for p in ('/docs', '/redoc', '/openapi.json')))\n"
    )
    moi_truong = {
        **os.environ,
        "MOI_TRUONG": "prod",
        "XAC_THUC_GIA": "false",
        "GHI_NOI_DUNG": "false",
        "APP_SECRET": secrets.token_hex(32),
        "PYTHONIOENCODING": "utf-8",
    }
    kq = subprocess.run(
        [sys.executable, "-c", ma_lenh],
        cwd=THU_MUC_BACKEND,
        env=moi_truong,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert kq.returncode == 0, kq.stderr[-500:]
    assert kq.stdout.split()[-3:] == ["404", "404", "404"]


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
