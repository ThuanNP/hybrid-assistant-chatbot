"""Bộ kiểm thử tính hợp lệ của hệ thống nhật ký JSON, mã yêu cầu và chỉ số vận hành.

Tuân thủ Quy tắc 4 (không ghi nội dung tin nhắn), Quy tắc 10 (ma_yeu_cau xuyên suốt)
và kiểm tra các yêu cầu định dạng JSON một dòng 22 trường.
"""

import io
import json
import logging
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import ASGITransport

from app.chat.ngu_canh import KetQuaNguCanh
from app.config import nap_cau_hinh
from app.core.nhat_ky import (
    CAC_TRUONG_CO_DINH,
    DinhDangNhatKyJson,
    dat_ma_yeu_cau,
    ghi_nhat_ky_chang,
)
from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.llm.chinh_sach import KetQuaXacDinhChuoi, Tang
from app.llm.router import KetQuaGoi
from app.main import app


@pytest.fixture
def bo_dem_nhat_ky() -> tuple[io.StringIO, logging.Handler, logging.Logger]:
    """Tạo bộ đệm bắt nhật ký định dạng JSON phục vụ kiểm thử."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(DinhDangNhatKyJson())

    test_logger = logging.getLogger("test_nhat_ky_logger")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)
    test_logger.propagate = False

    return stream, handler, test_logger


def test_dinh_dang_json_va_du_22_truong(
    bo_dem_nhat_ky: tuple[io.StringIO, logging.Handler, logging.Logger],
) -> None:
    """Kiểm tra mọi dòng nhật ký sinh ra đều là JSON hợp lệ và đủ 22 trường cố định."""
    stream, _, logger_obj = bo_dem_nhat_ky
    dat_ma_yeu_cau("ma_test_001")

    # 1. Ghi log thường
    logger_obj.info("Thông điệp kiểm thử thông thường")

    # 2. Ghi log qua hàm 7 chặng
    ghi_nhat_ky_chang(
        chang="http_vao",
        thong_diep="Tiếp nhận yêu cầu",
        logger_obj=logger_obj,
        ma_yeu_cau="ma_test_001",
        nguoi_id=1,
        phong_ban="CNTT",
        token_vao=50,
        token_ra=100,
        toc_do_tok_s=25.5,
    )

    noi_dung = stream.getvalue().strip()
    dong_list = [line for line in noi_dung.split("\n") if line.strip()]
    assert len(dong_list) == 2

    for dong in dong_list:
        du_lieu = json.loads(dong)
        assert isinstance(du_lieu, dict)
        for truong in CAC_TRUONG_CO_DINH:
            assert truong in du_lieu, f"Thiếu trường {truong} trong dòng nhật ký JSON"
        assert du_lieu["ma_yeu_cau"] == "ma_test_001"


def test_ma_yeu_cau_xuyen_suot_moi_dong(
    bo_dem_nhat_ky: tuple[io.StringIO, logging.Handler, logging.Logger],
) -> None:
    """Kiểm tra ma_yeu_cau có trong mọi dòng của một lời gọi xuyên suốt các chặng."""
    stream, _, logger_obj = bo_dem_nhat_ky
    ma_yc_rieng = "ma_xuyen_suot"
    dat_ma_yeu_cau(ma_yc_rieng)

    cac_chang = [
        "http_vao",
        "kiem_tra_han_muc",
        "xac_dinh_chuoi",
        "dung_ngu_canh",
        "goi_mo_hinh",
        "luu_hoi_thoai",
        "http_ra",
    ]

    for chang in cac_chang:
        ghi_nhat_ky_chang(
            chang=chang,
            thong_diep=f"Xử lý chặng {chang}",
            logger_obj=logger_obj,
            ma_yeu_cau=ma_yc_rieng,
        )

    noi_dung = stream.getvalue().strip()
    dong_list = [line for line in noi_dung.split("\n") if line.strip()]
    assert len(dong_list) == 7

    for idx, dong in enumerate(dong_list):
        du_lieu = json.loads(dong)
        assert du_lieu["ma_yeu_cau"] == ma_yc_rieng
        assert du_lieu["chang"] == cac_chang[idx]


@pytest.mark.asyncio
async def test_khong_chua_noi_dung_tin_nhan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra nhật ký tuyệt đối không chứa nội dung tin nhắn của người dùng hoặc phản hồi."""
    chuoi_nhay_cam = "CHUOI_KIEM_TRA_123_BI_MAT_HOAN_TOAN"
    cau_tra_loi_mau = "PHAN_HOI_CUA_TRO_LY_CHUA_BI_MAT"

    # Bắt đầu nghe log trên root logger
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(DinhDangNhatKyJson())
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        # Mock chuỗi định tuyến và gọi mô hình để cô lập kiểm thử nhật ký
        kq_chuoi = KetQuaXacDinhChuoi(
            chuoi=[Tang(so=0, ten="local", cua_so_ngu_canh=4096, nguon="local")],
            ly_do_chuoi="local",
        )
        monkeypatch.setattr("app.main.xac_dinh_chuoi", lambda *a, **kw: kq_chuoi)
        monkeypatch.setattr(
            "app.main.dung_ngu_canh",
            lambda *a, **kw: KetQuaNguCanh(danh_sach=[], da_cat=False, so_luot_bi_cat=0),
        )

        kq_goi = KetQuaGoi(
            noi_dung=cau_tra_loi_mau,
            nguon="local",
            tang=0,
            bac_local="chinh",
            ten_model="qwen_test",
            token_vao=15,
            token_ra=25,
            chi_phi_usd=0.0,
            do_tre_ms=150.0,
            thoi_gian_nap_ms=0.0,
            toc_do_tok_s=20.0,
            do_dai_hang_doi=1,
            da_cat_ngu_canh=False,
        )
        monkeypatch.setattr(
            "app.main.goi_mo_hinh",
            AsyncMock(return_value=kq_goi),
        )

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/chat",
                json={"noi_dung": chuoi_nhay_cam},
            )

        assert resp.status_code == 200

        # Kiểm tra nội dung nhật ký đã ghi
        toan_bo_log = stream.getvalue()

        # Tuyệt đối không chứa chuỗi câu hỏi hoặc chuỗi câu trả lời
        assert chuoi_nhay_cam not in toan_bo_log, (
            "Nội dung câu hỏi của người dùng bị rò rỉ vào nhật ký!"
        )
        assert cau_tra_loi_mau not in toan_bo_log, (
            "Nội dung phản hồi của trợ lý bị rò rỉ vào nhật ký!"
        )

        # Nhưng phải ghi nhận độ dài tin nhắn
        assert f"độ dài: {len(chuoi_nhay_cam)}" in toan_bo_log

    finally:
        root_logger.removeHandler(handler)


def test_ghi_noi_dung_prod_tu_choi_khoi_dong(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra cờ GHI_NOI_DUNG=true trong môi trường prod bị từ chối khởi động."""
    monkeypatch.setenv("GHI_NOI_DUNG", "true")
    monkeypatch.setenv("MOI_TRUONG", "prod")

    with pytest.raises(ValueError, match="Cờ GHI_NOI_DUNG=true chỉ được phép bật khi MOI_TRUONG=dev"):
        nap_cau_hinh()


def test_vet_loi_json_hop_le() -> None:
    """Kiểm tra ngoại lệ được định dạng an toàn trong trường vet_loi mà không làm vỡ 1 dòng JSON."""
    import sys

    formatter = DinhDangNhatKyJson()
    try:
        raise RuntimeError("Lỗi giả lập kiểm tra traceback")
    except RuntimeError:
        record = logging.LogRecord(
            name="test_loi",
            level=logging.ERROR,
            pathname=__file__,
            lineno=100,
            msg="Gặp lỗi ngoại lệ",
            args=(),
            exc_info=sys.exc_info(),
        )

    dong_json = formatter.format(record)
    # Xác nhận chỉ có đúng 1 dòng (không có ký tự xuống dòng trần phá vỡ cấu trúc log)
    assert "\n" not in dong_json
    du_lieu = json.loads(dong_json)
    assert du_lieu["muc"] == "ERROR"
    assert "vet_loi" in du_lieu
    assert "RuntimeError: Lỗi giả lập kiểm tra traceback" in du_lieu["vet_loi"]


@pytest.mark.asyncio
async def test_endpoint_chi_so_quan_tri(nguoi_dung_test: NguoiDung) -> None:
    """Kiểm tra endpoint /api/v1/chi-so chỉ cho phép vai trò quan_tri và trả đủ 6 nhóm chỉ số."""
    transport = ASGITransport(app=app)

    # 1. Người dùng thường -> 403 KHONG_CO_QUYEN
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: NguoiDung(
        id=1, email="user@vidu.com", vai_tro="nguoi_dung"
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp_403 = await client.get("/api/v1/chi-so?gio=24")
    assert resp_403.status_code == 403
    assert resp_403.json()["loi"]["ma"] == "KHONG_CO_QUYEN"

    # 2. Quản trị viên -> 200 OK kèm đủ 6 nhóm chỉ số
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: NguoiDung(
        id=2, email="admin@vidu.com", vai_tro="quan_tri"
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp_200 = await client.get("/api/v1/chi-so?gio=24")

    assert resp_200.status_code == 200
    kq = resp_200.json()

    # Kiểm tra đủ 6 nhóm chỉ số
    assert "toc_do_tok_s" in kq
    assert "thoi_gian_nap_ms" in kq
    assert "do_dai_hang_doi" in kq
    assert "ty_le_ha_cap_local" in kq
    assert "ty_le_roi_ra_dam_may" in kq
    assert "ty_le_roi_tang_dam_may" in kq
    assert "ty_le_cat_ngu_canh" in kq
    assert "so_yeu_cau_nhay_cam" in kq

    # Kiểm tra cấu trúc phân vị tốc độ
    assert "local" in kq["toc_do_tok_s"]
    assert "dam_may" in kq["toc_do_tok_s"]
    assert "trung_vi" in kq["toc_do_tok_s"]["local"]
    assert "phan_vi_90" in kq["toc_do_tok_s"]["local"]

    # Kiểm tra cấu trúc nạp model và hàng đợi
    assert "trung_vi" in kq["thoi_gian_nap_ms"]
    assert "ty_le_cho_nap" in kq["thoi_gian_nap_ms"]
    assert "trung_binh" in kq["do_dai_hang_doi"]
    assert "dinh" in kq["do_dai_hang_doi"]
