"""Bộ kiểm thử đơn vị cho bộ chạy cục bộ bo_chay_local.py."""

import json
from typing import Any
import httpx
import pytest
import respx

from app.config import (
    CauHinhBacLocal,
    CauHinhBoChay,
    CauHinhCaiDatChung,
    CauHinhHeThong,
    CauHinhLocalChung,
)
from app.core.loi import LoiDauVao, LoiHetBacLocal
from app.llm.bo_chay_local import goi_local


def tao_cau_hinh_kiem_thu(
    so_model_nap_cung_luc: int = 1,
    nguong_hang_doi: int = 3,
    loai_bo_chay: str = "ollama",
) -> CauHinhHeThong:
    """Tạo đối tượng CauHinhHeThong độc lập dùng riêng cho bộ kiểm thử."""
    return CauHinhHeThong(
        bac_local=[
            CauHinhBacLocal(bac="chinh", model="qwen3.5:4b-q8_0", num_ctx=16384),
            CauHinhBacLocal(bac="nho", model="qwen3.5:2b-q8_0", num_ctx=8192),
        ],
        so_model_nap_cung_luc=so_model_nap_cung_luc,
        chuoi_dam_may=[],
        che_do_dinh_tuyen="local_truoc",
        cai_dat_chung=CauHinhCaiDatChung(
            so_lan_thu_lai_moi_tang=2,
            giay_gian_cach_dau=0.5,
            gioi_han_token_ra=1024,
            ngu_canh_du_phong_token=512,
        ),
        bo_chay=CauHinhBoChay(
            loai=loai_bo_chay,
            dia_chi="http://localhost:11434/v1",
            timeout_giay=120,
        ),
        ho_so_gpu={},
        ho_so_gpu_dang_chon="gpu8",
        local_chung=CauHinhLocalChung(
            keep_alive="30m",
            nhiet_do=0.3,
            nguong_hang_doi_ha_cap=nguong_hang_doi,
        ),
        database_url="postgresql+psycopg://user:pass@localhost:5432/test",
        moi_truong="test",
        ngan_sach_ngay_usd=10.0,
        so_luong_dong_thoi=5,
        do_dai_hang_doi_toi_da=50,
        timeout_giay=60,
        ghi_noi_dung=False,
        xac_thuc_gia=True,
        app_secret="test_secret",
        cors_origins=["http://localhost:4200"],
    )


@respx.mock
async def test_ha_cap_khi_bac_1_qua_han(respx_mock: respx.MockRouter) -> None:
    """Hạ cấp sang bậc 2 khi bậc 1 quá hạn phản hồi (TimeoutException)."""

    def phan_hoi_side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            raise httpx.ReadTimeout("Bậc 1 quá thời gian phản hồi")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Phản hồi từ bậc 2"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=phan_hoi_side_effect
    )

    cfg = tao_cau_hinh_kiem_thu()
    kq = await goi_local(
        [{"role": "user", "content": "Xin chào"}],
        ma_yeu_cau="req-timeout",
        cau_hinh_he_thong=cfg,
    )

    assert kq.bac == "nho"
    assert kq.model == "qwen3.5:2b-q8_0"
    assert kq.noi_dung == "Phản hồi từ bậc 2"


@respx.mock
async def test_ha_cap_khi_bac_1_tra_503(respx_mock: respx.MockRouter) -> None:
    """Hạ cấp sang bậc 2 khi bộ chạy trả mã lỗi 503 (hoặc lỗi 5xx)."""

    def phan_hoi_side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            return httpx.Response(503, text="Service Unavailable: VRAM full")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Phản hồi từ bậc 2 sau 503"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 6},
            },
        )

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=phan_hoi_side_effect
    )

    cfg = tao_cau_hinh_kiem_thu()
    kq = await goi_local(
        [{"role": "user", "content": "Xin chào"}],
        ma_yeu_cau="req-503",
        cau_hinh_he_thong=cfg,
    )

    assert kq.bac == "nho"
    assert kq.model == "qwen3.5:2b-q8_0"
    assert "sau 503" in kq.noi_dung


@respx.mock
async def test_khong_ha_cap_khi_tra_400_nem_loi_dau_vao(respx_mock: respx.MockRouter) -> None:
    """Không hạ cấp khi bộ chạy trả mã lỗi 400 do yêu cầu sai, ném LoiDauVao."""
    so_lan_goi_bac_2 = 0

    def phan_hoi_side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal so_lan_goi_bac_2
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            return httpx.Response(400, text="Bad Request: Tham số không hợp lệ")
        so_lan_goi_bac_2 += 1
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Không được gọi"}}] }
        )

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=phan_hoi_side_effect
    )

    cfg = tao_cau_hinh_kiem_thu()
    with pytest.raises(LoiDauVao) as thong_tin_loi:
        await goi_local(
            [{"role": "user", "content": "Yêu cầu sai"}],
            ma_yeu_cau="req-400",
            cau_hinh_he_thong=cfg,
        )

    assert thong_tin_loi.value.ma_trang_thai == 400
    assert so_lan_goi_bac_2 == 0


@respx.mock
async def test_bo_qua_bac_1_khi_hang_doi_dai_va_so_model_nap_cung_luc_2(
    respx_mock: respx.MockRouter,
) -> None:
    """Bỏ qua bậc 1 khi hàng đợi vượt ngưỡng và hệ thống nạp được 2 model cùng lúc."""
    goi_bac_1 = False

    def phan_hoi_side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal goi_bac_1
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            goi_bac_1 = True
            return httpx.Response(200, json={"choices": [{"message": {"content": "Bậc 1"}}]})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Bậc 2 do hàng đợi dài"}}]},
        )

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=phan_hoi_side_effect
    )

    cfg = tao_cau_hinh_kiem_thu(so_model_nap_cung_luc=2, nguong_hang_doi=3)
    kq = await goi_local(
        [{"role": "user", "content": "Hàng đợi dài"}],
        ma_yeu_cau="req-hang-doi-2",
        do_dai_hang_doi=5,
        cau_hinh_he_thong=cfg,
    )

    assert kq.bac == "nho"
    assert kq.model == "qwen3.5:2b-q8_0"
    assert not goi_bac_1


@respx.mock
async def test_khong_bo_qua_bac_1_vi_hang_doi_khi_so_model_nap_cung_luc_1(
    respx_mock: respx.MockRouter,
) -> None:
    """Không bỏ qua bậc 1 vì hàng đợi dài khi so_model_nap_cung_luc = 1."""
    goi_bac_1 = False

    def phan_hoi_side_effect(request: httpx.Request) -> httpx.Response:
        nonlocal goi_bac_1
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            goi_bac_1 = True
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Bậc 1 vẫn xử lý"}}]},
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "Bậc 2"}}]})

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=phan_hoi_side_effect
    )

    cfg = tao_cau_hinh_kiem_thu(so_model_nap_cung_luc=1, nguong_hang_doi=3)
    kq = await goi_local(
        [{"role": "user", "content": "Không bỏ qua bậc 1"}],
        ma_yeu_cau="req-hang-doi-1",
        do_dai_hang_doi=5,
        cau_hinh_he_thong=cfg,
    )

    assert kq.bac == "chinh"
    assert kq.model == "qwen3.5:4b-q8_0"
    assert goi_bac_1


@respx.mock
async def test_keep_alive_nam_o_cap_cao_nhat_khong_nam_trong_options(
    respx_mock: respx.MockRouter,
) -> None:
    """Xác minh keep_alive nằm ở cấp cao nhất của thân JSON, không nằm trong options."""
    than_yeu_cau_nhan_duoc: dict[str, Any] = {}

    def bat_than_yeu_cau(request: httpx.Request) -> httpx.Response:
        nonlocal than_yeu_cau_nhan_duoc
        than_yeu_cau_nhan_duoc = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=bat_than_yeu_cau
    )

    cfg = tao_cau_hinh_kiem_thu()
    await goi_local(
        [{"role": "user", "content": "Kiểm tra keep_alive"}],
        ma_yeu_cau="req-keep-alive",
        cau_hinh_he_thong=cfg,
    )

    assert "keep_alive" in than_yeu_cau_nhan_duoc
    assert "options" in than_yeu_cau_nhan_duoc
    assert "keep_alive" not in than_yeu_cau_nhan_duoc["options"]
    assert than_yeu_cau_nhan_duoc["keep_alive"] == "30m"
    assert than_yeu_cau_nhan_duoc["options"]["num_ctx"] == 16384


@respx.mock
async def test_het_hai_bac_nem_loi_het_bac_local_du_hai_ly_do(
    respx_mock: respx.MockRouter,
) -> None:
    """Ném LoiHetBacLocal khi cả hai bậc thất bại, chứa đầy đủ lý do từng bậc."""

    def ca_hai_that_bai(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("model") == "qwen3.5:4b-q8_0":
            return httpx.Response(500, text="Lỗi nội bộ bậc 1")
        return httpx.Response(503, text="Bậc 2 quá tải")

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=ca_hai_that_bai
    )

    cfg = tao_cau_hinh_kiem_thu()
    with pytest.raises(LoiHetBacLocal) as thong_tin_loi:
        await goi_local(
            [{"role": "user", "content": "Cả hai bậc lỗi"}],
            ma_yeu_cau="req-het-bac",
            cau_hinh_he_thong=cfg,
        )

    loi = thong_tin_loi.value
    assert loi.ly_do_bac_1 is not None
    assert loi.ly_do_bac_2 is not None
    assert "500" in loi.ly_do_bac_1
    assert "503" in loi.ly_do_bac_2


@respx.mock
async def test_boc_sse_dung_dung_o_done(respx_mock: respx.MockRouter) -> None:
    """Bóc dữ liệu SSE đúng chuẩn OpenAI, bỏ qua dòng rỗng/chú thích và dừng ở [DONE]."""
    noi_dung_sse = (
        "data: {\"choices\": [{\"delta\": {\"content\": \"Xin\"}}]}\n\n"
        ": dong chu thich can bo qua\n\n"
        "\n\n"
        "data: {\"choices\": [{\"delta\": {\"content\": \" chào\"}}]}\n\n"
        "data: [DONE]\n\n"
        "data: {\"choices\": [{\"delta\": {\"content\": \" không được đọc\"}}]}\n\n"
    )

    respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            text=noi_dung_sse,
        )
    )

    cfg = tao_cau_hinh_kiem_thu()
    luong = await goi_local(
        [{"role": "user", "content": "Phát theo dòng"}],
        ma_yeu_cau="req-sse",
        phat_theo_dong=True,
        cau_hinh_he_thong=cfg,
    )

    cac_mau: list[str] = []
    async for chunk in luong:
        if chunk.noi_dung:
            cac_mau.append(chunk.noi_dung)

    assert cac_mau == ["Xin", " chào"]
    assert "không được đọc" not in cac_mau
