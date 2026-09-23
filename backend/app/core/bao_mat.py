"""Bảo vệ dữ liệu nhạy cảm và các móc kiểm duyệt nội dung."""

from typing import Any

from pydantic import BaseModel, Field


class KetQuaKiemDuyet(BaseModel):
    """Kết quả kiểm tra kiểm duyệt nội dung đầu vào hoặc phản hồi đầu ra."""

    cho_qua: bool = Field(
        default=True, description="Cờ cho phép tiếp tục luồng xử lý hoặc lưu trữ"
    )
    ly_do: str | None = Field(
        default=None, description="Lý do từ chối nếu nội dung vi phạm chính sách"
    )
    noi_dung_thay_the: str | None = Field(
        default=None, description="Nội dung đã được khử nhạy cảm hoặc thay thế an toàn"
    )


async def kiem_duyet_dau_vao(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt nội dung người dùng nhập vào trước khi dựng ngữ cảnh hội thoại.

    Điểm tích hợp kiểm duyệt ở Giai đoạn 5, gắn sẵn tại đây để không phải sửa luồng.
    Giai đoạn hiện tại luôn trả cho_qua=True.
    """
    _ = (noi_dung, nguoi)
    return KetQuaKiemDuyet(cho_qua=True, ly_do=None, noi_dung_thay_the=None)


async def kiem_duyet_dau_ra(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt phản hồi mô hình sinh ra trên toàn văn trước khi lưu CSDL và trả về.

    Điểm tích hợp kiểm duyệt ở Giai đoạn 5, gắn sẵn tại đây để không phải sửa luồng.
    Giai đoạn hiện tại luôn trả cho_qua=True.
    """
    _ = (noi_dung, nguoi)
    return KetQuaKiemDuyet(cho_qua=True, ly_do=None, noi_dung_thay_the=None)


# ---------------------------------------------------------------------------
# BỐI CẢNH BẢO MẬT BỘ CHẠY CỤC BỘ (OLLAMA / LM STUDIO):
# Máy chủ Ollama KHÔNG CÓ CƠ CHẾ XÁC THỰC. API của nó không chỉ phục vụ sinh văn
# bản mà còn cho phép: tải model (/api/pull), tạo model (/api/create), sao chép
# (/api/copy), đẩy (/api/push) và xoá model (/api/delete). Mặc định Ollama chỉ
# nghe ở 127.0.0.1 nên an toàn; rủi ro phát sinh khi mở rộng để container hoặc
# máy khác gọi được (lộ GPU miễn phí, bị tải tràn ổ cứng hoặc xoá model).
# LM Studio có rủi ro tương tự khi bật "Serve on Local Network".
# ---------------------------------------------------------------------------

THONG_DIEP_BA_CACH_NOI_AN_TOAN = """
LỖI CẤU HÌNH BẢO MẬT: Phát hiện cổng bộ chạy cục bộ bị phơi lộ ({dia_chi_phoi_lo}).
Máy chủ Ollama KHÔNG có xác thực. API cho phép tải, tạo, sao chép, đẩy và xoá model.
Trong môi trường MOI_TRUONG=prod, ứng dụng TỪ CHỐI khởi động để bảo vệ an toàn hệ thống.

Vui lòng áp dụng một trong ba cách nối an toàn sau (xếp theo thứ tự ưu tiên):
  Cách A - GIỮ 127.0.0.1 (mặc định của Ollama, ưu tiên số 1):
    - Windows/macOS với Docker Desktop: Giữ nguyên OLLAMA_HOST=127.0.0.1:11434. Container
      gọi qua http://host.docker.internal:11434, Docker Desktop tự chuyển tới loopback máy.
    - Linux (Docker Engine): Backend dùng network_mode: host hoặc chạy backend ngoài container.
  Cách B - Chỉ dùng trên máy chủ Linux:
    - Bind vào địa chỉ cầu nối Docker (thường 172.17.0.1, xem bằng 'ip addr show docker0'),
      KHÔNG bind 0.0.0.0, kèm luật ufw chỉ cho dải mạng Docker vào cổng 11434.
    - Trên Windows: Dùng PowerShell quản trị tạo New-NetFirewallRule hạn chế dải RemoteAddress.
  Cách C - Buộc phải mở rộng hơn:
    - Đặt Nginx phía trước, bật Basic Auth hoặc mTLS, CHẶN các đường quản trị:
      /api/pull, /api/create, /api/delete, /api/push, /api/copy.
    - Chỉ cho qua các endpoint suy luận: /api/chat, /v1/chat/completions, /v1/embeddings,
      /api/embed, /api/tags, /api/ps, /api/show. Tham khảo mẫu tại deploy/nginx-ollama.conf.
"""


def _trich_xuat_host(dia_chi: str) -> str:
    """Trích xuất hostname hoặc IP từ URL hoặc chuỗi địa chỉ host:port."""
    dia_chi_chuan = dia_chi.strip()
    if not dia_chi_chuan:
        return ""
    if dia_chi_chuan.startswith(":"):
        return "0.0.0.0"
    if "://" not in dia_chi_chuan:
        dia_chi_chuan = f"http://{dia_chi_chuan}"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(dia_chi_chuan)
        return parsed.hostname or ""
    except Exception:
        return dia_chi.split(":")[0].strip()


def _la_dia_chi_phoi_lo(host: str) -> bool:
    """Xác định hostname/IP có phải là địa chỉ phơi lộ nguy hiểm hay không.

    Địa chỉ an toàn: loopback (127.0.0.1, localhost, ::1), host.docker.internal,
    và dải cầu nối nội bộ Docker (172.17.0.1 hoặc mạng docker0 172.17.0.0/16).
    Mọi địa chỉ 0.0.0.0, IP công cộng, hoặc dải LAN khác đều coi là phơi lộ.
    """
    import ipaddress

    host_chuan = host.strip().lower()
    if not host_chuan:
        return False
    if host_chuan in {"localhost", "host.docker.internal"}:
        return False
    if host_chuan in {"0.0.0.0", "::"}:
        return True

    try:
        ip = ipaddress.ip_address(host_chuan)
        if ip.is_loopback:
            return False
        # Dải cầu nối Docker mặc định (172.17.0.0/16) được chấp nhận cho Cách B
        if ip == ipaddress.ip_address("172.17.0.1") or ip in ipaddress.ip_network("172.17.0.0/16"):
            return False
        if ip.is_global or ip.is_unspecified or ip.is_private:
            return True
    except ValueError:
        # Tên miền không phải IP chuẩn và không nằm trong danh sách an toàn
        return True
    return False


def kiem_tra_phoi_lo(
    dia_chi: str | None = None,
    ollama_host: str | None = None,
    moi_truong: str | None = None,
) -> bool:
    """Kiểm tra nguy cơ phơi lộ cổng bộ chạy mô hình local (Ollama / LM Studio).

    Chạy trong lifespan lúc khởi động. Phát hiện 0.0.0.0, địa chỉ công cộng, hoặc
    địa chỉ LAN không được phép. Môi trường prod phát hiện phơi lộ sẽ từ chối khởi động.
    """
    import logging
    import os
    import sys

    from app.config import cau_hinh

    logger = logging.getLogger(__name__)

    dia_chi_chinh = dia_chi if dia_chi is not None else cau_hinh.bo_chay.dia_chi
    bien_ollama_host = (
        ollama_host if ollama_host is not None else os.environ.get("OLLAMA_HOST")
    )
    env_moi_truong = moi_truong if moi_truong is not None else cau_hinh.moi_truong

    cac_dia_chi_can_kiem_tra: list[tuple[str, str]] = []
    if dia_chi_chinh:
        cac_dia_chi_can_kiem_tra.append(("DIA_CHI_BO_CHAY", dia_chi_chinh))
    if bien_ollama_host:
        cac_dia_chi_can_kiem_tra.append(("OLLAMA_HOST", bien_ollama_host))

    for nguon, gia_tri in cac_dia_chi_can_kiem_tra:
        host = _trich_xuat_host(gia_tri)
        if _la_dia_chi_phoi_lo(host):
            thong_diep = THONG_DIEP_BA_CACH_NOI_AN_TOAN.format(
                dia_chi_phoi_lo=f"{nguon}={gia_tri}"
            )
            logger.warning(
                "CẢNH BÁO BẢO MẬT: Phát hiện cổng bộ chạy local có nguy cơ bị phơi lộ: "
                "%s=%s (host: %s)",
                nguon,
                gia_tri,
                host,
            )
            if env_moi_truong == "prod":
                logger.critical(thong_diep)
                sys.exit(thong_diep)
            return False

    return True
