"""Bộ kiểm thử cho hệ thống giám sát sức khỏe bộ chạy backend/app/giam_sat/suc_khoe.py."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import (
    CauHinhBacLocal,
    CauHinhBoChay,
    CauHinhCaiDatChung,
    CauHinhHeThong,
    CauHinhLocalChung,
)
from app.core.xac_thuc import NguoiDung, lay_nguoi_dung_hien_tai
from app.giam_sat.suc_khoe import (
    kiem_tra_bo_chay_dinh_ky,
    lay_thong_tin_bo_chay,
    tinh_so_giay_con_lai,
)
from app.main import app

URL_PS = "http://localhost:11434/api/ps"
URL_SHOW = "http://localhost:11434/api/show"
MODEL_CHINH = "qwen3.5:4b-q8_0"
MODEL_NHO = "qwen3.5:2b-q8_0"


def tao_cau_hinh_giam_sat(num_ctx_chinh: int = 16384) -> CauHinhHeThong:
    """Tạo đối tượng CauHinhHeThong độc lập phục vụ kiểm thử giám sát."""
    return CauHinhHeThong(
        bac_local=[
            CauHinhBacLocal(bac="chinh", model=MODEL_CHINH, num_ctx=num_ctx_chinh),
            CauHinhBacLocal(bac="nho", model=MODEL_NHO, num_ctx=8192),
        ],
        so_model_nap_cung_luc=1,
        chuoi_dam_may=[],
        che_do_dinh_tuyen="local_truoc",
        cai_dat_chung=CauHinhCaiDatChung(),
        bo_chay=CauHinhBoChay(loai="ollama", dia_chi="http://localhost:11434", timeout_giay=10),
        ho_so_gpu={},
        ho_so_gpu_dang_chon="gpu8",
        dung_luong_vram_gb=8,
        local_chung=CauHinhLocalChung(keep_alive="30m", nhiet_do=0.3),
        database_url=None,
        moi_truong="test",
        ngan_sach_ngay_usd=10.0,
        so_luong_dong_thoi=1,
        do_dai_hang_doi_toi_da=20,
        timeout_giay=60,
        ghi_noi_dung=False,
        xac_thuc_gia=True,
        app_secret=None,
        cors_origins=["http://localhost:4200"],
    )


def test_tinh_dung_thoi_gian_con_lai_keep_alive() -> None:
    """Kiểm tra tính đúng thời gian còn lại của keep_alive từ chuỗi ISO 8601."""
    # 1. Thời điểm tương lai 120 giây
    tuong_lai = datetime.now(timezone.utc) + timedelta(seconds=120)
    con_lai = tinh_so_giay_con_lai(tuong_lai.isoformat())
    assert con_lai is not None
    assert 115.0 <= con_lai <= 125.0

    # 2. Định dạng có 9 chữ số nano giây chuẩn RFC3339 của Go/Ollama
    tuong_lai_nano = (datetime.now(timezone.utc) + timedelta(seconds=60)).strftime(
        "%Y-%m-%dT%H:%M:%S.123456789Z"
    )
    con_lai_nano = tinh_so_giay_con_lai(tuong_lai_nano)
    assert con_lai_nano is not None
    assert 55.0 <= con_lai_nano <= 65.0

    # 3. Thời điểm quá khứ (đã hết hạn) trả về 0.0
    qua_khu = datetime.now(timezone.utc) - timedelta(seconds=30)
    assert tinh_so_giay_con_lai(qua_khu.isoformat()) == 0.0

    # 4. Giá trị None hoặc chuỗi rỗng trả về None
    assert tinh_so_giay_con_lai(None) is None
    assert tinh_so_giay_con_lai("") is None


@respx.mock
async def test_phat_hien_lech_ngu_canh(respx_mock: respx.MockRouter) -> None:
    """Phát hiện đúng lệch ngữ cảnh giữa cấu hình num_ctx và thực tế từ /api/ps và /api/show."""
    cfg = tao_cau_hinh_giam_sat(num_ctx_chinh=16384)

    # Giả lập /api/ps trả về model chính đang nạp với context_length = 4096 (lệch cấu hình 16384)
    respx_mock.get(URL_PS).mock(
        return_value=httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": MODEL_CHINH,
                        "model": MODEL_CHINH,
                        "size": 4725049344,
                        "size_vram": 4725049344,
                        "context_length": 4096,
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                    }
                ]
            },
        )
    )
    respx_mock.post(URL_SHOW).mock(
        return_value=httpx.Response(200, json={"model_info": {"qwen.context_length": 4096}})
    )

    kq = await lay_thong_tin_bo_chay(cfg)
    assert kq.co_lech is True
    assert len(kq.model_dang_nap) == 1
    assert kq.model_dang_nap[0].ten == MODEL_CHINH
    assert kq.model_dang_nap[0].kich_thuoc_vram_byte == 4725049344
    assert kq.vram.vram_con_trong_gb is not None

    b1_info = next(nc for nc in kq.ngu_canh if nc.bac == "chinh")
    assert b1_info.num_ctx_cau_hinh == 16384
    assert b1_info.num_ctx_thuc_te == 4096
    assert b1_info.co_lech is True


@respx.mock
async def test_bo_chay_gap_su_co_tac_vu_nen_khong_nem_loi(respx_mock: respx.MockRouter) -> None:
    """Bộ chạy gặp sự cố (mất mạng, lỗi kết nối) thì tác vụ nền cảnh báo, không ném lỗi."""
    cfg = tao_cau_hinh_giam_sat()
    respx_mock.get(URL_PS).mock(side_effect=httpx.ConnectError("Connection refused"))

    # Tác vụ nền không văng lỗi ngoại lệ
    await kiem_tra_bo_chay_dinh_ky(cfg)

    # Lấy thông tin trạng thái trả về lỗi được kiểm soát an toàn
    kq = await lay_thong_tin_bo_chay(cfg)
    assert kq.vram.vram_con_trong_gb is None
    assert kq.vram.ly_do is not None
    assert "Không kết nối được bộ chạy" in kq.vram.ly_do


def test_api_giam_sat_bo_chay_phan_quyen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra phân quyền API /api/v1/giam-sat/bo-chay chỉ cho phép vai trò quan_tri."""
    client = TestClient(app)

    # 1. Khi hủy override và tắt xác thực giả (xac_thuc_gia=False), chưa gửi token -> 401
    from app.config import cau_hinh as cau_hinh_app
    monkeypatch.setattr(cau_hinh_app, "xac_thuc_gia", False)
    app.dependency_overrides.pop(lay_nguoi_dung_hien_tai, None)
    res_unauth = client.get("/api/v1/giam-sat/bo-chay")
    assert res_unauth.status_code == 401

    # 2. Vai trò cán bộ thông thường (nguoi_dung) -> 403
    monkeypatch.setattr(cau_hinh_app, "xac_thuc_gia", True)
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: NguoiDung(
        id=2, vai_tro="nguoi_dung", email="canbo@vidu.com"
    )
    res_forbidden = client.get("/api/v1/giam-sat/bo-chay")
    assert res_forbidden.status_code == 403

    # 3. Vai trò quan_tri -> 200 kèm cấu trúc dữ liệu đầy đủ
    app.dependency_overrides[lay_nguoi_dung_hien_tai] = lambda: NguoiDung(
        id=1, vai_tro="quan_tri", email="admin@vidu.com"
    )
    res_ok = client.get("/api/v1/giam-sat/bo-chay")
    assert res_ok.status_code == 200
    du_lieu = res_ok.json()
    assert "ho_so_gpu" in du_lieu
    assert "model_dang_nap" in du_lieu
    assert "ngu_canh" in du_lieu
    assert "vram" in du_lieu
    assert "co_lech" in du_lieu
