"""Bộ kiểm thử cho luồng phát sự kiện Server-Sent Events (POST /api/v1/chat/stream).

Kiểm tra 5 kịch bản kỹ thuật cốt lõi:
1. Thứ tự sự kiện: bat_dau -> manh -> xong kèm siêu dữ liệu đầy đủ.
2. Sự kiện hang_doi xuất hiện trước bat_dau khi yêu cầu phải chờ.
3. Lỗi giữa luồng trả về sự kiện loi mang đúng phần dữ liệu đã nhận.
4. Đóng kết nối máy khách giữa chừng huỷ lời gọi và giải phóng semaphore GPU.
5. Header SSE chuẩn và ngăn proxy đệm dữ liệu (X-Accel-Buffering: no).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from app.hang_doi.dieu_phoi import dieu_phoi_mac_dinh
from app.llm.router import KetQuaGoi, ManhPhatRa
from app.main import app


def _phan_tich_dong_sse(van_ban: str) -> list[tuple[str, dict[str, Any]]]:
    """Phân tích chuỗi phản hồi text/event-stream thành danh sách (tên_sự_kiện, dữ_liệu_json)."""
    danh_sach_su_kien: list[tuple[str, dict[str, Any]]] = []
    cac_khoi = van_ban.strip().split("\n\n")

    for khoi in cac_khoi:
        dong_list = [d.strip() for d in khoi.splitlines() if d.strip()]
        if not dong_list:
            continue

        ten_su_kien = ""
        du_lieu_dict: dict[str, Any] = {}

        for dong in dong_list:
            if dong.startswith("event:"):
                ten_su_kien = dong[len("event:"):].strip()
            elif dong.startswith("data:"):
                noi_dung_data = dong[len("data:"):].strip()
                try:
                    du_lieu_dict = json.loads(noi_dung_data)
                except json.JSONDecodeError:
                    du_lieu_dict = {"raw": noi_dung_data}

        if ten_su_kien:
            danh_sach_su_kien.append((ten_su_kien, du_lieu_dict))

    return danh_sach_su_kien


@pytest.mark.asyncio
async def test_stream_thu_tu_su_kien_thanh_cong(monkeypatch: pytest.MonkeyPatch) -> None:
    """1. Thứ tự sự kiện chuẩn: bat_dau -> ít nhất 2 manh -> xong có đủ siêu dữ liệu."""
    async def _mock_stream_thanh_cong(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(
            loai="bat_dau",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
            da_cat_ngu_canh=False,
            so_luot_bi_cat=0,
        )
        yield ManhPhatRa(loai="manh", noi_dung="Xin ")
        yield ManhPhatRa(loai="manh", noi_dung="chào các bạn!")
        kq = KetQuaGoi(
            noi_dung="Xin chào các bạn!",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
            token_vao=15,
            token_ra=25,
            chi_phi_usd=0.0,
            do_tre_ms=180.0,
            thoi_gian_nap_ms=12.0,
            toc_do_tok_s=30.0,
        )
        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq)

    monkeypatch.setattr("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", _mock_stream_thanh_cong)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        phan_hoi = await client.post(
            "/api/v1/chat/stream",
            json={"hoi_thoai_id": 101, "noi_dung": "xin chào"},
        )

    assert phan_hoi.status_code == 200
    su_kien_list = _phan_tich_dong_sse(phan_hoi.text)

    ten_cac_su_kien = [sk[0] for sk in su_kien_list]
    assert ten_cac_su_kien == ["bat_dau", "manh", "manh", "xong"]

    bat_dau_data = su_kien_list[0][1]
    assert bat_dau_data["hoi_thoai_id"] == 101
    assert bat_dau_data["nguon"] == "local"
    assert bat_dau_data["tang"] == 0
    assert bat_dau_data["model"] == "qwen3.5:9b-q4_K_M"
    assert bat_dau_data["da_cat_ngu_canh"] is False
    assert bat_dau_data["so_luot_bi_cat"] == 0

    assert su_kien_list[1][1]["noi_dung"] == "Xin "
    assert su_kien_list[2][1]["noi_dung"] == "chào các bạn!"

    xong_data = su_kien_list[3][1]
    assert xong_data["token_vao"] == 15
    assert xong_data["token_ra"] == 25
    assert xong_data["chi_phi_usd"] == 0.0
    assert xong_data["toc_do_tok_s"] == 30.0
    assert xong_data["do_tre_ms"] == 180.0
    assert xong_data["nguon"] == "local"
    assert xong_data["tang"] == 0
    assert xong_data["bac_local"] == "chinh"
    assert xong_data["model"] == "qwen3.5:9b-q4_K_M"
    assert "Nội dung do AI tạo - qwen3.5:9b-q4_K_M -" in xong_data["nhan_ai"]


@pytest.mark.asyncio
async def test_stream_hang_doi_dung_truoc_bat_dau(monkeypatch: pytest.MonkeyPatch) -> None:
    """2. Khi vào hàng đợi local, sự kiện hang_doi bắt buộc phải đứng trước bat_dau."""
    async def _mock_stream_co_hang_doi(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(loai="hang_doi", vi_tri=2, uoc_luong_giay=6.5)
        yield ManhPhatRa(
            loai="bat_dau",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
        )
        yield ManhPhatRa(loai="manh", noi_dung="Nội dung đã chạy")
        kq = KetQuaGoi(
            noi_dung="Nội dung đã chạy",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
        )
        yield ManhPhatRa(loai="xong", ket_qua=kq)

    monkeypatch.setattr("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", _mock_stream_co_hang_doi)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        phan_hoi = await client.post(
            "/api/v1/chat/stream",
            json={"noi_dung": "kiểm tra hàng đợi"},
        )

    assert phan_hoi.status_code == 200
    su_kien_list = _phan_tich_dong_sse(phan_hoi.text)

    ten_cac_su_kien = [sk[0] for sk in su_kien_list]
    assert ten_cac_su_kien[0] == "hang_doi"
    assert ten_cac_su_kien[1] == "bat_dau"

    hang_doi_data = su_kien_list[0][1]
    assert hang_doi_data["vi_tri"] == 2
    assert hang_doi_data["uoc_luong_giay"] == 6.5


@pytest.mark.asyncio
async def test_stream_loi_sau_hai_manh_khop_phan_da_nhan(monkeypatch: pytest.MonkeyPatch) -> None:
    """3. Lỗi sau 2 mảnh -> sự kiện loi có phan_da_nhan khớp chính xác 2 mảnh đã phát."""
    async def _mock_stream_loi_giua(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(
            loai="bat_dau",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
        )
        yield ManhPhatRa(loai="manh", noi_dung="Phần một. ")
        yield ManhPhatRa(loai="manh", noi_dung="Phần hai.")
        yield ManhPhatRa(loai="loi", noi_dung="Phần một. Phần hai.")

    monkeypatch.setattr("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", _mock_stream_loi_giua)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        phan_hoi = await client.post(
            "/api/v1/chat/stream",
            json={"noi_dung": "yêu cầu gặp lỗi"},
        )

    assert phan_hoi.status_code == 200
    su_kien_list = _phan_tich_dong_sse(phan_hoi.text)

    ten_cac_su_kien = [sk[0] for sk in su_kien_list]
    assert ten_cac_su_kien == ["bat_dau", "manh", "manh", "loi"]

    loi_data = su_kien_list[3][1]
    assert loi_data["phan_da_nhan"] == "Phần một. Phần hai."
    assert "ma_yeu_cau" in loi_data
    assert len(loi_data["ma_yeu_cau"]) == 12


@pytest.mark.asyncio
async def test_stream_dong_ket_noi_giua_chung_giai_phong_semaphore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4. Đóng kết nối giữa chừng -> tác vụ bị huỷ, semaphore của DieuPhoi được giải phóng."""
    dp = dieu_phoi_mac_dinh
    gia_tri_semaphore_ban_dau = dp._semaphore._value
    tac_vu_bi_huy = False

    async def _mock_stream_tre(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        nonlocal tac_vu_bi_huy
        await dp.bat_dau_chay_ngay("yc_test_cancel")
        try:
            yield ManhPhatRa(
                loai="bat_dau",
                nguon="local",
                tang=0,
                bac_local="chinh",
                ten_model="qwen3.5:9b-q4_K_M",
            )
            yield ManhPhatRa(loai="manh", noi_dung="Mảnh đầu tiên")
            await asyncio.sleep(5.0)
            yield ManhPhatRa(loai="manh", noi_dung="Mảnh thứ hai")
        except asyncio.CancelledError:
            tac_vu_bi_huy = True
            raise
        finally:
            dp.giai_phong()

    monkeypatch.setattr("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", _mock_stream_tre)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Máy khách gửi yêu cầu trong một tác vụ bất đồng bộ
        tac_vu_yeu_cau = asyncio.create_task(
            client.post("/api/v1/chat/stream", json={"noi_dung": "ngắt kết nối"})
        )
        # Chờ lời gọi bắt đầu chạy và chiếm quyền semaphore
        await asyncio.sleep(0.1)
        # Giả lập máy khách đóng kết nối / huỷ yêu cầu giữa chừng
        tac_vu_yeu_cau.cancel()
        try:
            await tac_vu_yeu_cau
        except asyncio.CancelledError:
            pass

    await asyncio.sleep(0.05)

    assert tac_vu_bi_huy is True
    assert dp._semaphore._value == gia_tri_semaphore_ban_dau


@pytest.mark.asyncio
async def test_stream_headers_va_x_accel_buffering(monkeypatch: pytest.MonkeyPatch) -> None:
    """5. Kiểm tra đầy đủ header SSE chuẩn và X-Accel-Buffering bằng no."""
    async def _mock_stream_don_gian(*args: Any, **kwargs: Any) -> AsyncIterator[ManhPhatRa]:
        yield ManhPhatRa(
            loai="bat_dau",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
        )
        yield ManhPhatRa(loai="manh", noi_dung="Xin chào")
        kq = KetQuaGoi(
            noi_dung="Xin chào",
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen3.5:9b-q4_K_M",
        )
        yield ManhPhatRa(loai="xong", ket_qua=kq)

    monkeypatch.setattr("app.chat.su_kien_sse.goi_mo_hinh_theo_dong", _mock_stream_don_gian)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        phan_hoi = await client.post(
            "/api/v1/chat/stream",
            json={"noi_dung": "xin chào"},
        )

    assert phan_hoi.status_code == 200
    headers = phan_hoi.headers
    assert headers.get("x-accel-buffering") == "no"
    assert "text/event-stream" in headers.get("content-type", "")
    assert headers.get("cache-control") == "no-cache"
    assert headers.get("connection") == "keep-alive"
