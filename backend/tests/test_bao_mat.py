"""Bộ kiểm thử kiểm tra an toàn và chống phơi lộ cổng bộ chạy mô hình local (Ollama / LM Studio).

Kiểm tra:
1. Nhận diện an toàn: 127.0.0.1, localhost, ::1, host.docker.internal.
2. Nhận diện an toàn: 172.17.0.1 (địa chỉ cầu nối Docker Cách B).
3. Nhận diện phơi lộ: 0.0.0.0, :11434.
4. Nhận diện phơi lộ: dải IP mạng LAN nội bộ (10.x, 192.168.x).
5. Nhận diện phơi lộ: địa chỉ IP công cộng (203.0.113.x, 8.8.8.8).
6. Môi trường prod kèm phơi lộ: ứng dụng TỪ CHỐI khởi động (sys.exit) kèm thông điệp ba cách nối.
7. Môi trường dev kèm phơi lộ: chỉ ghi nhật ký cảnh báo, không làm gián đoạn tiến trình.
8. Môi trường prod với cấu hình an toàn: ứng dụng khởi động bình thường.
"""

import pytest

from app.core.bao_mat import kiem_tra_phoi_lo


def test_kiem_tra_phoi_lo_loopback_an_toan() -> None:
    """Các địa chỉ loopback cục bộ (127.0.0.1, localhost, host.docker.internal) là an toàn."""
    assert kiem_tra_phoi_lo(dia_chi="http://127.0.0.1:11434", ollama_host=None, moi_truong="dev") is True
    assert kiem_tra_phoi_lo(dia_chi="http://localhost:11434", ollama_host=None, moi_truong="dev") is True
    assert (
        kiem_tra_phoi_lo(dia_chi="http://host.docker.internal:11434", ollama_host=None, moi_truong="dev")
        is True
    )
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://127.0.0.1:11434",
            ollama_host="127.0.0.1:11434",
            moi_truong="prod",
        )
        is True
    )


def test_kiem_tra_phoi_lo_docker_bridge_an_toan() -> None:
    """Địa chỉ cầu nối Docker 172.17.0.1 (Cách B trên Linux) được coi là hợp lệ nội bộ."""
    assert kiem_tra_phoi_lo(dia_chi="http://172.17.0.1:11434", ollama_host=None, moi_truong="dev") is True
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://172.17.0.1:11434/v1",
            ollama_host="172.17.0.1:11434",
            moi_truong="prod",
        )
        is True
    )


def test_kiem_tra_phoi_lo_0000_nguy_hiem() -> None:
    """Địa chỉ 0.0.0.0 hoặc cú pháp :11434 lắng nghe trên mọi card mạng phải bị coi là phơi lộ."""
    # Kiểm tra qua DIA_CHI_BO_CHAY
    assert kiem_tra_phoi_lo(dia_chi="http://0.0.0.0:11434/v1", ollama_host=None, moi_truong="dev") is False
    assert kiem_tra_phoi_lo(dia_chi="0.0.0.0:11434", ollama_host=None, moi_truong="dev") is False

    # Kiểm tra qua OLLAMA_HOST
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://127.0.0.1:11434",
            ollama_host="0.0.0.0:11434",
            moi_truong="dev",
        )
        is False
    )
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://127.0.0.1:11434",
            ollama_host=":11434",
            moi_truong="dev",
        )
        is False
    )


def test_kiem_tra_phoi_lo_dia_chi_lan_10x_va_192() -> None:
    """Địa chỉ mạng LAN (10.x.x.x, 192.168.x.x) không qua proxy/tường lửa phải bị coi là phơi lộ."""
    assert kiem_tra_phoi_lo(dia_chi="http://10.0.1.5:11434", ollama_host=None, moi_truong="dev") is False
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://127.0.0.1:11434",
            ollama_host="10.10.20.30:11434",
            moi_truong="dev",
        )
        is False
    )
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://192.168.1.18:11434",
            ollama_host=None,
            moi_truong="dev",
        )
        is False
    )


def test_kiem_tra_phoi_lo_dia_chi_cong_cong() -> None:
    """Địa chỉ IP công cộng toàn cầu (public IP) bắt buộc bị nhận diện là phơi lộ nguy hiểm."""
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://203.0.113.195:11434",
            ollama_host=None,
            moi_truong="dev",
        )
        is False
    )
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://8.8.8.8:11434",
            ollama_host=None,
            moi_truong="dev",
        )
        is False
    )


def test_kiem_tra_phoi_lo_prod_tu_choi_khoi_dong_0000() -> None:
    """Ở môi trường prod, cấu hình 0.0.0.0 bắt buộc làm ứng dụng từ chối khởi động (sys.exit)."""
    with pytest.raises(SystemExit) as thong_tin_thoat:
        kiem_tra_phoi_lo(
            dia_chi="http://0.0.0.0:11434/v1",
            ollama_host=None,
            moi_truong="prod",
        )

    thong_diep = str(thong_tin_thoat.value)
    assert "LỖI CẤU HÌNH BẢO MẬT" in thong_diep
    assert "Cách A" in thong_diep
    assert "Cách B" in thong_diep
    assert "Cách C" in thong_diep
    assert "127.0.0.1" in thong_diep
    assert "deploy/nginx-ollama.conf" in thong_diep


def test_kiem_tra_phoi_lo_prod_tu_choi_khoi_dong_lan() -> None:
    """Ở môi trường prod, trỏ trực tiếp vào IP LAN cũng bị từ chối khởi động."""
    with pytest.raises(SystemExit) as thong_tin_thoat:
        kiem_tra_phoi_lo(
            dia_chi="http://10.0.0.10:11434",
            ollama_host=None,
            moi_truong="prod",
        )

    thong_diep = str(thong_tin_thoat.value)
    assert "LỖI CẤU HÌNH BẢO MẬT" in thong_diep
    assert "DIA_CHI_BO_CHAY=http://10.0.0.10:11434" in thong_diep


def test_kiem_tra_phoi_lo_prod_tu_choi_khoi_dong_dia_chi_cong_cong() -> None:
    """Ở môi trường prod, trỏ vào IP công cộng bị từ chối khởi động."""
    with pytest.raises(SystemExit) as thong_tin_thoat:
        kiem_tra_phoi_lo(
            dia_chi="http://203.0.113.1:11434",
            ollama_host=None,
            moi_truong="prod",
        )

    thong_diep = str(thong_tin_thoat.value)
    assert "LỖI CẤU HÌNH BẢO MẬT" in thong_diep


def test_kiem_tra_phoi_lo_prod_an_toan_khoi_dong_binh_thuong() -> None:
    """Ở môi trường prod, cấu hình loopback hoặc host.docker.internal khởi động bình thường."""
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://host.docker.internal:11434/v1",
            ollama_host=None,
            moi_truong="prod",
        )
        is True
    )
    assert (
        kiem_tra_phoi_lo(
            dia_chi="http://127.0.0.1:11434",
            ollama_host=None,
            moi_truong="prod",
        )
        is True
    )
