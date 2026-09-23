"""Bộ kiểm thử cho mô-đun quản trị cấu hình backend/app/config.py."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.config import (
    CauHinhHeThong,
    _dieu_chinh_dia_chi_ngoai_container,
    _kiem_tra_chuoi_dam_may,
    _kiem_tra_the_model_local,
    _kiem_tra_tinh_hop_le_ho_so_gpu,
    nap_cau_hinh,
)


def test_tu_choi_the_thieu_luong_tu_hoa() -> None:
    """Từ chối thẻ model local nếu thiếu dấu hai chấm hoặc thiếu lượng tử hoá."""
    # Thiếu lượng tử hoá (chỉ có :7b)
    assert not _kiem_tra_the_model_local("model_test:7b")
    # Thiếu dấu hai chấm
    assert not _kiem_tra_the_model_local("model_test-q4_k_m")
    # Thẻ đúng quy chuẩn
    assert _kiem_tra_the_model_local("model_test:7b-q4_k_m")
    assert _kiem_tra_the_model_local("model_test:4b-q8_0")

    du_lieu_ho_so: dict[str, Any] = {
        "gpu8": {
            "chinh": {"model": "model_sai:7b", "num_ctx": 8192},
            "nho": {"model": "model_dung:2b-q4_0", "num_ctx": 4096},
            "num_parallel": 1,
            "so_model_nap_cung_luc": 1,
        }
    }
    with pytest.raises(ValueError) as thong_tin_loi:
        _kiem_tra_tinh_hop_le_ho_so_gpu(du_lieu_ho_so, "gpu8")

    assert "thẻ model phải ghi đầy đủ" in str(thong_tin_loi.value)


def test_tu_choi_bac_nho_co_num_ctx_lon_hon_chinh() -> None:
    """Từ chối nếu bậc nho có num_ctx lớn hơn bậc chinh."""
    du_lieu_ho_so: dict[str, Any] = {
        "gpu8": {
            "chinh": {"model": "model_chinh:4b-q8_0", "num_ctx": 4096},
            "nho": {"model": "model_nho:2b-q8_0", "num_ctx": 8192},
            "num_parallel": 1,
            "so_model_nap_cung_luc": 1,
        }
    }
    with pytest.raises(ValueError) as thong_tin_loi:
        _kiem_tra_tinh_hop_le_ho_so_gpu(du_lieu_ho_so, "gpu8")

    assert "num_ctx của bậc nho phải nhỏ hơn hoặc bằng bậc chinh" in str(thong_tin_loi.value)


def test_tu_choi_ho_so_gpu_la(monkeypatch: pytest.MonkeyPatch) -> None:
    """Từ chối khởi động nếu HO_SO_GPU không nằm trong các khoá đã khai báo."""
    monkeypatch.setenv("HO_SO_GPU", "gpu99")
    with pytest.raises(ValueError) as thong_tin_loi:
        nap_cau_hinh()

    thong_diep = str(thong_tin_loi.value)
    assert "HO_SO_GPU không hợp lệ" in thong_diep
    assert "gpu99" in thong_diep


def test_tu_choi_che_do_dinh_tuyen_la(monkeypatch: pytest.MonkeyPatch) -> None:
    """Từ chối khởi động nếu CHE_DO_DINH_TUYEN không hợp lệ."""
    monkeypatch.setenv("CHE_DO_DINH_TUYEN", "che_do_la_lung")
    with pytest.raises(ValueError) as thong_tin_loi:
        nap_cau_hinh()

    thong_diep = str(thong_tin_loi.value)
    assert "CHE_DO_DINH_TUYEN không hợp lệ" in thong_diep
    assert "che_do_la_lung" in thong_diep


def test_tu_choi_so_model_nap_cung_luc_sai() -> None:
    """Từ chối nếu so_model_nap_cung_luc khác 1 và 2."""
    du_lieu_ho_so: dict[str, Any] = {
        "gpu8": {
            "chinh": {"model": "model_chinh:4b-q8_0", "num_ctx": 8192},
            "nho": {"model": "model_nho:2b-q8_0", "num_ctx": 4096},
            "num_parallel": 1,
            "so_model_nap_cung_luc": 3,
        }
    }
    with pytest.raises(ValueError) as thong_tin_loi:
        _kiem_tra_tinh_hop_le_ho_so_gpu(du_lieu_ho_so, "gpu8")

    assert "so_model_nap_cung_luc" in str(thong_tin_loi.value)


def test_tu_choi_chuoi_dam_may_sai_thu_tu_hoac_trung() -> None:
    """Từ chối chuỗi đám mây nếu số tầng bị trùng hoặc không tăng dần."""
    # Tầng bị trùng
    chuoi_trung = [
        {"tang": 1, "ten": "a"},
        {"tang": 1, "ten": "b"},
    ]
    with pytest.raises(ValueError) as loi_trung:
        _kiem_tra_chuoi_dam_may(chuoi_trung)
    assert "chuoi_dam_may có tầng bị trùng lặp" in str(loi_trung.value)

    # Tầng không tăng dần
    chuoi_giam = [
        {"tang": 2, "ten": "b"},
        {"tang": 1, "ten": "a"},
    ]
    with pytest.raises(ValueError) as loi_giam:
        _kiem_tra_chuoi_dam_may(chuoi_giam)
    assert "chuoi_dam_may phải có số tầng tăng dần" in str(loi_giam.value)


def test_tang_thieu_khoa_danh_dau_khong_kha_dung(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Tầng thiếu khoá API được đánh dấu kha_dung=False mà không làm dừng khởi động."""
    # Tạo tệp yaml cấu hình kiểm thử tạm thời
    tep_yaml = tmp_path / "models_test.yaml"
    noi_dung_yaml = {
        "bo_chay": {
            "loai": "ollama",
            "dia_chi": "http://localhost:11434/v1",
            "timeout_giay": 120,
        },
        "ho_so_gpu": {
            "gpu8": {
                "chinh": {"model": "m_chinh:4b-q8_0", "num_ctx": 8192},
                "nho": {"model": "m_nho:2b-q8_0", "num_ctx": 4096},
                "num_parallel": 1,
                "so_model_nap_cung_luc": 1,
            }
        },
        "local_chung": {
            "keep_alive": "30m",
            "nhiet_do": 0.3,
            "nguong_hang_doi_ha_cap": 3,
        },
        "chuoi_dam_may": [
            {
                "tang": 1,
                "ten": "dam_may_co_khoa",
                "model": "provider/test-model-1",
                "api_key_env": "TEST_CO_KHOA_KEY",
                "gia_vao_usd_moi_trieu": 1.0,
                "gia_ra_usd_moi_trieu": 2.0,
                "timeout_giay": 60,
                "cua_so_ngu_canh": 128000,
            },
            {
                "tang": 2,
                "ten": "dam_may_thieu_khoa",
                "model": "provider/test-model-2",
                "api_key_env": "TEST_THIEU_KHOA_KEY",
                "gia_vao_usd_moi_trieu": 1.0,
                "gia_ra_usd_moi_trieu": 2.0,
                "timeout_giay": 60,
                "cua_so_ngu_canh": 128000,
            },
        ],
        "cai_dat_chung": {
            "so_lan_thu_lai_moi_tang": 2,
            "giay_gian_cach_dau": 0.5,
            "gioi_han_token_ra": 1024,
            "ngu_canh_du_phong_token": 512,
        },
    }
    with open(tep_yaml, "w", encoding="utf-8") as f:
        yaml.dump(noi_dung_yaml, f)

    monkeypatch.setenv("TEST_CO_KHOA_KEY", "khoa_that_123")
    monkeypatch.delenv("TEST_THIEU_KHOA_KEY", raising=False)
    monkeypatch.setenv("HO_SO_GPU", "gpu8")

    cau_hinh_kq = nap_cau_hinh(duong_dan_yaml=tep_yaml)
    assert cau_hinh_kq.chuoi_dam_may[0].kha_dung is True
    assert cau_hinh_kq.chuoi_dam_may[1].kha_dung is False


def test_ngoai_container_doi_db_thanh_localhost() -> None:
    """Ngoài container thì host db trong DATABASE_URL được chuyển thành localhost."""
    url_goc = "postgresql+psycopg://user:pass@db:5432/app_db"
    _, url_dieu_chinh = _dieu_chinh_dia_chi_ngoai_container(
        dia_chi_bo_chay="http://localhost:11434/v1",
        database_url=url_goc,
        dang_trong_container=False,
    )
    assert url_dieu_chinh == "postgresql+psycopg://user:pass@localhost:5432/app_db"

    # Trong container thì giữ nguyên không đổi
    _, url_trong_container = _dieu_chinh_dia_chi_ngoai_container(
        dia_chi_bo_chay="http://localhost:11434/v1",
        database_url=url_goc,
        dang_trong_container=True,
    )
    assert url_trong_container == url_goc


def test_ngoai_container_doi_host_docker_internal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ngoài container, nếu không phân giải được host.docker.internal thì chuyển về localhost."""
    import app.config as config_mod

    # Giả lập DNS không phân giải được host.docker.internal
    monkeypatch.setattr(config_mod, "_kiem_tra_phan_giai_host", lambda host: False)

    dia_chi_goc = "http://host.docker.internal:11434/v1"
    dia_chi_dieu_chinh, _ = _dieu_chinh_dia_chi_ngoai_container(
        dia_chi_bo_chay=dia_chi_goc,
        database_url="postgresql+psycopg://user:pass@localhost:5432/app_db",
        dang_trong_container=False,
    )
    assert dia_chi_dieu_chinh == "http://localhost:11434/v1"


def test_nap_cau_hinh_he_thong_gpu8_thanh_cong(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nạp cấu hình hệ thống thực tế với hồ sơ gpu8 thành công."""
    monkeypatch.setenv("HO_SO_GPU", "gpu8")
    monkeypatch.setenv("CHE_DO_DINH_TUYEN", "local_truoc")

    cau_hinh_thuc_te: CauHinhHeThong = nap_cau_hinh()
    assert cau_hinh_thuc_te.so_model_nap_cung_luc == 1
    assert cau_hinh_thuc_te.che_do_dinh_tuyen == "local_truoc"
    assert len(cau_hinh_thuc_te.bac_local) == 2
    assert cau_hinh_thuc_te.bac_local[0].bac == "chinh"
    assert cau_hinh_thuc_te.bac_local[1].bac == "nho"
    assert len(cau_hinh_thuc_te.chuoi_dam_may) == 4


def test_tu_choi_loai_bo_chay_la(monkeypatch: pytest.MonkeyPatch) -> None:
    """Từ chối khởi động nếu LOAI_BO_CHAY không phải ollama hoặc lmstudio."""
    monkeypatch.setenv("LOAI_BO_CHAY", "lm_studio")
    with pytest.raises(ValueError) as thong_tin_loi:
        nap_cau_hinh()

    thong_diep = str(thong_tin_loi.value)
    assert "LOAI_BO_CHAY không hợp lệ" in thong_diep
    assert "lm_studio" in thong_diep


def test_the_model_sai_neu_ro_ho_so_va_bac() -> None:
    """Thông báo lỗi thẻ model nêu đúng hồ sơ, bậc và thẻ sai để sửa nhanh."""
    du_lieu_ho_so: dict[str, Any] = {
        "gpu12": {
            "chinh": {"model": "model_dung:9b-q4_K_M", "num_ctx": 8192},
            "nho": {"model": "model_sai:4b", "num_ctx": 4096},
            "num_parallel": 1,
            "so_model_nap_cung_luc": 2,
        }
    }
    with pytest.raises(ValueError) as thong_tin_loi:
        _kiem_tra_tinh_hop_le_ho_so_gpu(du_lieu_ho_so, "gpu12")

    thong_diep = str(thong_tin_loi.value)
    assert "gpu12" in thong_diep
    assert "nho" in thong_diep
    assert "model_sai:4b" in thong_diep


def test_doc_dung_tep_env_duoc_truyen_va_khong_co_bi_mat_mac_dinh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """nap_cau_hinh đọc đúng tệp .env được truyền vào; thiếu bí mật thì để None."""
    for ten_bien in ("HO_SO_GPU", "LOAI_BO_CHAY", "DIA_CHI_BO_CHAY", "DATABASE_URL", "APP_SECRET"):
        monkeypatch.delenv(ten_bien, raising=False)
    tep_env = tmp_path / ".env"
    tep_env.write_text(
        "HO_SO_GPU=gpu12\nLOAI_BO_CHAY=ollama\nDIA_CHI_BO_CHAY=http://localhost:11434/v1\n",
        encoding="utf-8",
    )

    cau_hinh_kq = nap_cau_hinh(duong_dan_env=tep_env)

    assert cau_hinh_kq.ho_so_gpu_dang_chon == "gpu12"
    assert cau_hinh_kq.database_url is None
    assert cau_hinh_kq.app_secret is None


def test_bien_rong_dung_mac_dinh_theo_ho_so(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SO_LUONG_DONG_THOI để trống thì lấy num_parallel của hồ sơ GPU, không làm hỏng khởi động."""
    for ten_bien in ("HO_SO_GPU", "LOAI_BO_CHAY", "SO_LUONG_DONG_THOI", "DO_DAI_HANG_DOI_TOI_DA"):
        monkeypatch.delenv(ten_bien, raising=False)
    tep_env = tmp_path / ".env"
    tep_env.write_text(
        "HO_SO_GPU=gpu16\nLOAI_BO_CHAY=ollama\nSO_LUONG_DONG_THOI=\nDO_DAI_HANG_DOI_TOI_DA=\n",
        encoding="utf-8",
    )

    cau_hinh_kq = nap_cau_hinh(duong_dan_env=tep_env)

    assert cau_hinh_kq.so_luong_dong_thoi == 2
    assert cau_hinh_kq.do_dai_hang_doi_toi_da == 20
