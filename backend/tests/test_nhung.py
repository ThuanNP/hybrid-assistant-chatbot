"""Bộ kiểm thử cho tính năng tạo vector nhúng (Embedding) - Giai đoạn 6 (PROMPT 27).

Tuân thủ nghiêm ngặt:
- Quy tắc 1: Một cửa duy nhất goi_nhung() trong router.py, router không import httpx.
- Các đường dẫn endpoint /api/embed và /embeddings chỉ được xuất hiện trong bo_chay_local.py
  (ngoài chú thích hướng dẫn bảo vệ cổng bộ chạy trong core/bao_mat.py).
- Quy tắc kỹ thuật 7: Ghi nhận LuotGoi với muc_dich = 'nhung'.
- Lỗi model nhúng: Suy giảm có kiểm soát mức 2, trả về che_do_truy_hoi = 'chi_tu_khoa'.
- Sai số chiều: Từ chối ghi nhận vào cơ sở dữ liệu.
"""

import ast
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.llm.bo_chay_local import (
    BoChayLMStudio,
    BoChayOllama,
    KetQuaNhungLocal,
)
from app.llm.chi_phi import KhoLuotGoiBoNho, chuan_hoa_muc_dich
from app.llm.router import goi_nhung, lay_the_nhung_theo_ho_so
from app.rag.nhung import nhung_cau_hoi


def test_tuan_thu_quy_tac_mot_cua_va_duong_dan_suy_luan() -> None:
    """1. Kiểm tra tĩnh:

    - /api/embed và /embeddings chỉ xuất hiện trong bo_chay_local.py (ngoài chú thích trong core/bao_mat.py).
    - router.py tuyệt đối không import httpx.
    """
    app_dir = Path(__file__).resolve().parent.parent / "app"

    # a. Kiểm tra cấm import httpx trong router.py
    router_file = app_dir / "llm" / "router.py"
    router_content = router_file.read_text(encoding="utf-8")
    tree = ast.parse(router_content, filename=str(router_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "httpx", "router.py KHÔNG ĐƯỢC PHÉP import httpx trực tiếp!"
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "httpx", "router.py KHÔNG ĐƯỢC PHÉP import từ httpx!"

    # b. Kiểm tra /api/embed và /embeddings chỉ nằm trong bo_chay_local.py (hoặc chú thích trong core/bao_mat.py)
    mau_endpoint = re.compile(r"/api/embed|/embeddings")
    for tep_py in app_dir.rglob("*.py"):
        duong_dan_tuong_doi = tep_py.relative_to(app_dir).as_posix()
        if duong_dan_tuong_doi in ("llm/bo_chay_local.py", "core/bao_mat.py"):
            continue
        noi_dung = tep_py.read_text(encoding="utf-8")
        cac_dong = noi_dung.splitlines()
        for idx, dong in enumerate(cac_dong, start=1):
            assert not mau_endpoint.search(dong), (
                f"Phát hiện endpoint nhúng '{dong.strip()}' tại {duong_dan_tuong_doi}:{idx}. "
                "Theo Quy tắc 1, endpoint này CHỈ ĐƯỢC PHÉP xuất hiện trong bo_chay_local.py!"
            )


@pytest.mark.asyncio
@respx.mock
async def test_bo_chay_ollama_nhung() -> None:
    """2. BoChayOllama gọi đúng POST /api/embed với keep_alive ở cấp cao nhất."""
    mock_route = respx.post("http://127.0.0.1:11434/api/embed").respond(
        status_code=200,
        json={
            "model": "bge-m3-cpu:567m-fp16",
            "embeddings": [[0.1] * 1024, [0.2] * 1024],
            "prompt_eval_count": 15,
        },
    )

    runner = BoChayOllama(dia_chi="http://127.0.0.1:11434/v1")
    kq = await runner.nhung(
        model="bge-m3-cpu:567m-fp16",
        van_ban=["Đoạn văn 1", "Đoạn văn 2"],
        keep_alive="30m",
        ma_yeu_cau="yc_test_ollama",
    )

    assert mock_route.called
    yeu_cau = mock_route.calls.last.request
    body = httpx.Request(
        yeu_cau.method, yeu_cau.url, headers=yeu_cau.headers, content=yeu_cau.content
    ).read()
    import json
    du_lieu = json.loads(body.decode("utf-8"))

    assert du_lieu["model"] == "bge-m3-cpu:567m-fp16"
    assert du_lieu["input"] == ["Đoạn văn 1", "Đoạn văn 2"]
    assert du_lieu["keep_alive"] == "30m"
    assert kq.so_chieu == 1024
    assert len(kq.vectors) == 2
    assert kq.token_vao == 15


@pytest.mark.asyncio
@respx.mock
async def test_bo_chay_lmstudio_nhung() -> None:
    """3. BoChayLMStudio gọi đúng POST /v1/embeddings và sắp xếp theo index."""
    mock_route = respx.post("http://localhost:1234/v1/embeddings").respond(
        status_code=200,
        json={
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": [0.2] * 1024, "index": 1},
                {"object": "embedding", "embedding": [0.1] * 1024, "index": 0},
            ],
            "model": "bge-m3:567m-fp16",
            "usage": {"prompt_tokens": 20, "total_tokens": 20},
        },
    )

    runner = BoChayLMStudio(dia_chi="http://localhost:1234/v1")
    kq = await runner.nhung(
        model="bge-m3:567m-fp16",
        van_ban=["Văn bản A", "Văn bản B"],
        ma_yeu_cau="yc_test_lms",
    )

    assert mock_route.called
    assert kq.so_chieu == 1024
    assert len(kq.vectors) == 2
    # Đã sắp xếp theo index 0 rồi 1
    assert kq.vectors[0][0] == 0.1
    assert kq.vectors[1][0] == 0.2
    assert kq.token_vao == 20


@pytest.mark.asyncio
async def test_router_goi_nhung_chia_lo_va_ghi_luot_goi() -> None:
    """4. router.goi_nhung chia lô 32 đoạn và ghi nhận LuotGoi với muc_dich='nhung'."""
    mock_runner = AsyncMock()

    async def mock_nhung(model: str, lo: list[str], **kwargs: Any) -> KetQuaNhungLocal:
        return KetQuaNhungLocal(
            vectors=[[0.05] * 1024 for _ in lo],
            model=model,
            so_chieu=1024,
            do_tre_ms=50.0,
            token_vao=len(lo) * 10,
        )

    mock_runner.nhung.side_effect = mock_nhung
    kho = KhoLuotGoiBoNho()

    # 35 đoạn văn bản -> chia thành 2 lô (32 và 3)
    danh_sach_vb = [f"Đoạn văn thứ {i}" for i in range(35)]

    kq = await goi_nhung(
        danh_sach_vb,
        ma_yeu_cau="yc_nhung_35",
        bo_chay=mock_runner,
        kho_luot_goi=kho,
        kich_thuoc_lo=32,
    )

    assert mock_runner.nhung.call_count == 2
    assert len(kq.vectors) == 35
    assert kq.so_chieu == 1024
    assert kq.token_vao == 350

    # Kiểm tra bản ghi LuotGoi
    tat_ca_luot = kho.lay_tat_ca()
    assert len(tat_ca_luot) == 1
    lg = tat_ca_luot[0]
    assert lg.muc_dich == "nhung"
    assert lg.nguon == "local"
    assert lg.tang == 0
    assert lg.thanh_cong is True
    assert lg.ma_yeu_cau == "yc_nhung_35"


@pytest.mark.asyncio
async def test_nhung_cau_hoi_thanh_cong_va_suy_giam_khi_loi() -> None:
    """5. nhung_cau_hoi:

    - Thành công -> che_do_truy_hoi = 'lai'
    - Lỗi -> lùi về che_do_truy_hoi = 'chi_tu_khoa' (suy giảm mức 2), vector = None.
    """
    # a. Ca thành công
    mock_runner_ok = AsyncMock()
    mock_runner_ok.nhung.return_value = KetQuaNhungLocal(
        vectors=[[0.1] * 1024],
        model="bge-m3-cpu:567m-fp16",
        so_chieu=1024,
        do_tre_ms=30.0,
        token_vao=8,
    )

    kq_ok = await nhung_cau_hoi("Tiêu chuẩn kỹ thuật điện lưới", bo_chay=mock_runner_ok)
    assert kq_ok.che_do_truy_hoi == "lai"
    assert kq_ok.vector is not None
    assert len(kq_ok.vector) == 1024

    # b. Ca lỗi: model nhúng không phản hồi
    mock_runner_loi = AsyncMock()
    mock_runner_loi.nhung.side_effect = RuntimeError("Bộ chạy Ollama bị ngắt kết nối")

    kq_loi = await nhung_cau_hoi(
        "Cách tính biểu giá điện",
        bo_chay=mock_runner_loi,
        cau_hinh_rag={"so_chieu": 1024, "model_nhung": "bge-m3"},
    )
    assert kq_loi.che_do_truy_hoi == "chi_tu_khoa"
    assert kq_loi.vector is None

    # Hỗ trợ unpack trực tiếp: vector, che_do = await nhung_cau_hoi(...)
    vector, che_do = kq_loi
    assert vector is None
    assert che_do == "chi_tu_khoa"


@pytest.mark.asyncio
async def test_tu_choi_khi_sai_so_chieu() -> None:
    """6. Từ chối ghi và ném lỗi/suy giảm khi số chiều vector khác 1024 cấu hình."""
    # Giả lập model nhúng trả về 768 chiều (ví dụ nhầm sang nomic-embed-text)
    mock_runner_sai_chieu = AsyncMock()
    mock_runner_sai_chieu.nhung.return_value = KetQuaNhungLocal(
        vectors=[[0.1] * 768],
        model="sai-model",
        so_chieu=768,
        do_tre_ms=25.0,
        token_vao=5,
    )

    # nhung_cau_hoi sẽ phát hiện lệch số chiều và lùi về chi_tu_khoa
    kq = await nhung_cau_hoi(
        "Kiểm tra câu hỏi lệch số chiều",
        bo_chay=mock_runner_sai_chieu,
        cau_hinh_rag={"so_chieu": 1024, "model_nhung": "bge-m3"},
    )
    assert kq.che_do_truy_hoi == "chi_tu_khoa"
    assert kq.vector is None


@pytest.mark.asyncio
async def test_lay_the_nhung_theo_ho_so() -> None:
    """7. Kiểm tra hàm ánh xạ thẻ nhúng đúng theo hồ sơ GPU."""
    rag_cfg = {
        "the_nhung_theo_ho_so": {
            "gpu6": "bge-m3-cpu:567m-fp16",
            "gpu8": "bge-m3-cpu:567m-fp16",
            "gpu12": "bge-m3:567m-fp16",
            "gpu16": "bge-m3:567m-fp16",
            "gpu24": "bge-m3:567m-fp16",
        }
    }
    assert lay_the_nhung_theo_ho_so("gpu6", rag_cfg) == "bge-m3-cpu:567m-fp16"
    assert lay_the_nhung_theo_ho_so("gpu8", rag_cfg) == "bge-m3-cpu:567m-fp16"
    assert lay_the_nhung_theo_ho_so("gpu12", rag_cfg) == "bge-m3:567m-fp16"
    assert lay_the_nhung_theo_ho_so("gpu24", rag_cfg) == "bge-m3:567m-fp16"


def test_chuan_hoa_muc_dich_nhung() -> None:
    """8. Kiểm tra hàm chuan_hoa_muc_dich hỗ trợ mục đích 'nhung'."""
    assert chuan_hoa_muc_dich("nhung") == "nhung"
    assert chuan_hoa_muc_dich("chat") == "chat"
    assert chuan_hoa_muc_dich("tieu_de") == "tieu_de"
    assert chuan_hoa_muc_dich("danh_gia") == "danh_gia"
    assert chuan_hoa_muc_dich("khong_xac_dinh") == "chat"
