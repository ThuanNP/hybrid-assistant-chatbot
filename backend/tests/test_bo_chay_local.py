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

URL_OLLAMA_CHAT = "http://localhost:11434/api/chat"
URL_LMSTUDIO_CHAT = "http://localhost:1234/v1/chat/completions"
MODEL_CHINH = "m_chinh:4b-q8_0"
MODEL_NHO = "m_nho:2b-q8_0"


def tao_cau_hinh_kiem_thu(
    so_model_nap_cung_luc: int = 1,
    nguong_hang_doi: int = 3,
    loai_bo_chay: str = "ollama",
) -> CauHinhHeThong:
    """Tạo đối tượng CauHinhHeThong độc lập dùng riêng cho bộ kiểm thử."""
    dia_chi = "http://localhost:11434/v1" if loai_bo_chay == "ollama" else "http://localhost:1234/v1"
    return CauHinhHeThong(
        bac_local=[
            CauHinhBacLocal(bac="chinh", model=MODEL_CHINH, num_ctx=16384),
            CauHinhBacLocal(bac="nho", model=MODEL_NHO, num_ctx=8192),
        ],
        so_model_nap_cung_luc=so_model_nap_cung_luc,
        chuoi_dam_may=[],
        che_do_dinh_tuyen="local_truoc",
        cai_dat_chung=CauHinhCaiDatChung(),
        bo_chay=CauHinhBoChay(loai=loai_bo_chay, dia_chi=dia_chi, timeout_giay=120),
        ho_so_gpu={},
        ho_so_gpu_dang_chon="gpu8",
        local_chung=CauHinhLocalChung(
            keep_alive="30m",
            nhiet_do=0.3,
            nguong_hang_doi_ha_cap=nguong_hang_doi,
        ),
        database_url=None,
        moi_truong="test",
        ngan_sach_ngay_usd=10.0,
        so_luong_dong_thoi=5,
        do_dai_hang_doi_toi_da=50,
        timeout_giay=60,
        ghi_noi_dung=False,
        xac_thuc_gia=True,
        app_secret=None,
        cors_origins=["http://localhost:4200"],
    )


def phan_hoi_ollama(noi_dung: str) -> httpx.Response:
    """Phản hồi /api/chat không phát theo dòng của Ollama."""
    return httpx.Response(
        200,
        json={
            "message": {"role": "assistant", "content": noi_dung},
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 5,
            "load_duration": 2_000_000,
            "prompt_eval_duration": 1_000_000,
            "eval_duration": 50_000_000,
        },
    )


def model_cua(request: httpx.Request) -> str:
    """Đọc tên model trong thân yêu cầu."""
    return str(json.loads(request.content).get("model"))


@respx.mock
async def test_ha_cap_khi_bac_1_qua_han(respx_mock: respx.MockRouter) -> None:
    """Hạ cấp sang bậc 2 khi bậc 1 quá hạn phản hồi."""

    def phan_hoi(request: httpx.Request) -> httpx.Response:
        if model_cua(request) == MODEL_CHINH:
            raise httpx.ReadTimeout("Bậc 1 quá thời gian phản hồi")
        return phan_hoi_ollama("Phản hồi từ bậc 2")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=phan_hoi)

    kq = await goi_local(
        [{"role": "user", "content": "Xin chào"}],
        ma_yeu_cau="req-timeout",
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
    )

    assert kq.bac == "nho"
    assert kq.model == MODEL_NHO
    assert kq.noi_dung == "Phản hồi từ bậc 2"
    assert kq.token_vao == 10
    assert kq.token_ra == 5
    assert kq.thoi_gian_nap_ms == 3.0


@respx.mock
async def test_ha_cap_khi_bac_1_tra_503(respx_mock: respx.MockRouter) -> None:
    """Hạ cấp sang bậc 2 khi bộ chạy trả lỗi 5xx."""

    def phan_hoi(request: httpx.Request) -> httpx.Response:
        if model_cua(request) == MODEL_CHINH:
            return httpx.Response(503, text="Service Unavailable: VRAM full")
        return phan_hoi_ollama("Phản hồi từ bậc 2 sau 503")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=phan_hoi)

    kq = await goi_local(
        [{"role": "user", "content": "Xin chào"}],
        ma_yeu_cau="req-503",
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
    )

    assert kq.bac == "nho"
    assert "sau 503" in kq.noi_dung


@respx.mock
async def test_khong_ha_cap_khi_tra_400_nem_loi_dau_vao(respx_mock: respx.MockRouter) -> None:
    """Không hạ cấp khi bộ chạy trả 400 do yêu cầu sai, ném LoiDauVao."""
    so_lan_goi_bac_2 = 0

    def phan_hoi(request: httpx.Request) -> httpx.Response:
        nonlocal so_lan_goi_bac_2
        if model_cua(request) == MODEL_CHINH:
            return httpx.Response(400, text="Bad Request: Tham số không hợp lệ")
        so_lan_goi_bac_2 += 1
        return phan_hoi_ollama("Không được gọi")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=phan_hoi)

    with pytest.raises(LoiDauVao) as thong_tin_loi:
        await goi_local(
            [{"role": "user", "content": "Yêu cầu sai"}],
            ma_yeu_cau="req-400",
            cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
        )

    assert thong_tin_loi.value.ma_trang_thai == 400
    assert so_lan_goi_bac_2 == 0


@respx.mock
async def test_bo_qua_bac_1_khi_hang_doi_dai_va_so_model_nap_cung_luc_2(
    respx_mock: respx.MockRouter,
) -> None:
    """Bỏ qua bậc 1 khi hàng đợi vượt ngưỡng và hệ thống nạp được 2 model cùng lúc."""
    cac_model_da_goi: list[str] = []

    def phan_hoi(request: httpx.Request) -> httpx.Response:
        cac_model_da_goi.append(model_cua(request))
        return phan_hoi_ollama("Bậc 2 do hàng đợi dài")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=phan_hoi)

    kq = await goi_local(
        [{"role": "user", "content": "Hàng đợi dài"}],
        ma_yeu_cau="req-hang-doi-2",
        do_dai_hang_doi=5,
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(so_model_nap_cung_luc=2, nguong_hang_doi=3),
    )

    assert kq.bac == "nho"
    assert cac_model_da_goi == [MODEL_NHO]


@respx.mock
async def test_khong_bo_qua_bac_1_vi_hang_doi_khi_so_model_nap_cung_luc_1(
    respx_mock: respx.MockRouter,
) -> None:
    """Không bỏ qua bậc 1 vì hàng đợi dài khi so_model_nap_cung_luc = 1."""
    cac_model_da_goi: list[str] = []

    def phan_hoi(request: httpx.Request) -> httpx.Response:
        cac_model_da_goi.append(model_cua(request))
        return phan_hoi_ollama("Bậc 1 vẫn xử lý")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=phan_hoi)

    kq = await goi_local(
        [{"role": "user", "content": "Không bỏ qua bậc 1"}],
        ma_yeu_cau="req-hang-doi-1",
        do_dai_hang_doi=5,
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(so_model_nap_cung_luc=1, nguong_hang_doi=3),
    )

    assert kq.bac == "chinh"
    assert cac_model_da_goi == [MODEL_CHINH]


@respx.mock
async def test_keep_alive_nam_o_cap_cao_nhat_khong_nam_trong_options(
    respx_mock: respx.MockRouter,
) -> None:
    """Ollama được gọi qua /api/chat; keep_alive ở cấp cao nhất, num_ctx trong options."""
    than_nhan_duoc: dict[str, Any] = {}

    def bat_than(request: httpx.Request) -> httpx.Response:
        than_nhan_duoc.update(json.loads(request.content))
        return phan_hoi_ollama("OK")

    tuyen_api_chat = respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=bat_than)

    await goi_local(
        [{"role": "user", "content": "Kiểm tra keep_alive"}],
        ma_yeu_cau="req-keep-alive",
        max_tokens=8,
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
    )

    assert tuyen_api_chat.called
    assert than_nhan_duoc["keep_alive"] == "30m"
    assert than_nhan_duoc["think"] is False
    assert "keep_alive" not in than_nhan_duoc["options"]
    assert than_nhan_duoc["options"]["num_ctx"] == 16384
    assert than_nhan_duoc["options"]["num_predict"] == 8


@respx.mock
async def test_het_hai_bac_nem_loi_het_bac_local_du_hai_ly_do(
    respx_mock: respx.MockRouter,
) -> None:
    """Ném LoiHetBacLocal khi cả hai bậc thất bại, chứa đầy đủ lý do từng bậc."""

    def ca_hai_that_bai(request: httpx.Request) -> httpx.Response:
        if model_cua(request) == MODEL_CHINH:
            return httpx.Response(500, text="Lỗi nội bộ bậc 1")
        return httpx.Response(503, text="Bậc 2 quá tải")

    respx_mock.post(URL_OLLAMA_CHAT).mock(side_effect=ca_hai_that_bai)

    with pytest.raises(LoiHetBacLocal) as thong_tin_loi:
        await goi_local(
            [{"role": "user", "content": "Cả hai bậc lỗi"}],
            ma_yeu_cau="req-het-bac",
            cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
        )

    loi = thong_tin_loi.value
    assert loi.ly_do_bac_1 is not None
    assert loi.ly_do_bac_2 is not None
    assert "500" in loi.ly_do_bac_1
    assert "503" in loi.ly_do_bac_2


@respx.mock
async def test_tach_ndjson_ollama_dung_o_done(respx_mock: respx.MockRouter) -> None:
    """Luồng NDJSON của Ollama: tách từng dòng, dừng ở dòng done=true, lấy số token."""
    cac_dong = [
        {"message": {"content": "Xin"}, "done": False},
        {"message": {"content": " chào"}, "done": False},
        {"message": {"content": ""}, "done": True, "prompt_eval_count": 7, "eval_count": 2},
        {"message": {"content": " không được đọc"}, "done": False},
    ]
    noi_dung = "\n".join(json.dumps(d, ensure_ascii=False) for d in cac_dong) + "\n"
    respx_mock.post(URL_OLLAMA_CHAT).mock(
        return_value=httpx.Response(
            200, headers={"Content-Type": "application/x-ndjson"}, text=noi_dung
        )
    )

    luong = await goi_local(
        [{"role": "user", "content": "Phát theo dòng"}],
        ma_yeu_cau="req-ndjson",
        phat_theo_dong=True,
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(),
    )
    cac_mau = [mau async for mau in luong]

    assert [m.noi_dung for m in cac_mau if m.noi_dung] == ["Xin", " chào"]
    assert cac_mau[-1].da_xong
    assert cac_mau[-1].bac == "chinh"
    assert (cac_mau[-1].token_vao, cac_mau[-1].token_ra) == (7, 2)


@respx.mock
async def test_tach_sse_lmstudio_dung_o_done(respx_mock: respx.MockRouter) -> None:
    """Luồng SSE của LM Studio: bỏ qua dòng rỗng và chú thích, dừng ở [DONE]."""
    noi_dung_sse = (
        'data: {"choices": [{"delta": {"content": "Xin"}}]}\n\n'
        ": dong chu thich can bo qua\n\n"
        "\n\n"
        'data: {"choices": [{"delta": {"content": " chào"}}]}\n\n'
        "data: [DONE]\n\n"
        'data: {"choices": [{"delta": {"content": " không được đọc"}}]}\n\n'
    )
    respx_mock.post(URL_LMSTUDIO_CHAT).mock(
        return_value=httpx.Response(
            200, headers={"Content-Type": "text/event-stream"}, text=noi_dung_sse
        )
    )

    luong = await goi_local(
        [{"role": "user", "content": "Phát theo dòng"}],
        ma_yeu_cau="req-sse",
        phat_theo_dong=True,
        cau_hinh_he_thong=tao_cau_hinh_kiem_thu(loai_bo_chay="lmstudio"),
    )
    cac_mau = [mau.noi_dung async for mau in luong if mau.noi_dung]

    assert cac_mau == ["Xin", " chào"]
