"""Kịch bản chẩn đoán kiểm tra nguy cơ phơi lộ cổng máy chủ Ollama / LM Studio.

Ngoại lệ quy tắc 1 AGENTS.md: Kịch bản này được phép gọi trực tiếp bộ chạy để
chẩn đoán an toàn mạng, không nằm trong luồng ứng dụng chính.
"""

import argparse
import socket
import sys
from urllib.parse import urlparse

import httpx

# Cấu hình encoding utf-8 để in tiếng Việt chính xác trên Windows / PowerShell
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")


def lay_ip_lan_tu_dong() -> str:
    """Tự động xác định địa chỉ IP LAN của máy bằng socket UDP tới 8.8.8.8."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Không phát sinh gói tin thật trên mạng, chỉ mở socket để lấy IP giao diện
        sock.connect(("8.8.8.8", 80))
        ip_lan = str(sock.getsockname()[0])
    except Exception:  # noqa: BLE001
        ip_lan = "127.0.0.1"
    finally:
        sock.close()
    return ip_lan


def _kiem_tra_dia_chi_hop_le(dia_chi: str) -> str:
    """Chuẩn hoá URL và từ chối các địa chỉ loopback (localhost/127.0.0.1)."""
    dia_chi_chuan = dia_chi.strip()
    if not dia_chi_chuan.startswith("http://") and not dia_chi_chuan.startswith("https://"):
        dia_chi_chuan = f"http://{dia_chi_chuan}"

    parsed = urlparse(dia_chi_chuan)
    host = (parsed.hostname or "").lower()

    if host in {"127.0.0.1", "localhost", "::1"} or host.startswith("127."):
        print("LỖI: Không kiểm tra trên 127.0.0.1 hoặc localhost!")
        print("Từ chính máy chạy bộ chạy, cổng loopback luôn gọi được.")
        print("Phép thử phải hướng vào IP LAN hoặc chạy từ máy khác trong mạng để kiểm tra.")
        sys.exit(2)

    return f"{parsed.scheme}://{parsed.netloc}"


def _thu_ket_noi_tags(dia_chi_goc: str) -> tuple[bool, str]:
    """Thử gửi yêu cầu GET /api/tags với timeout 3 giây."""
    try:
        with httpx.Client(timeout=3.0) as client:
            phan_hoi = client.get(f"{dia_chi_goc}/api/tags")
            if phan_hoi.status_code == 200:
                return True, f"GET /api/tags thành công (HTTP {phan_hoi.status_code})"
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return False, "Kết nối bị từ chối hoặc quá thời gian chờ (ConnectTimeout/ConnectError)"
    except Exception as err:  # noqa: BLE001
        return False, f"Lỗi kết nối: {err}"
    return False, "GET /api/tags không phản hồi thành công"


def _thu_ket_noi_pull(dia_chi_goc: str) -> tuple[bool, str]:
    """Thử gửi yêu cầu POST /api/pull với tên model không tồn tại và timeout 3 giây."""
    try:
        with httpx.Client(timeout=3.0) as client:
            phan_hoi = client.post(
                f"{dia_chi_goc}/api/pull",
                json={"name": "kiem_tra_phoi_lo_khong_ton_tai_9999"},
            )
            # Ollama phản hồi 200/400/404 nghĩa là cổng quản trị mở tiếp nhận xử lý
            if phan_hoi.status_code in {200, 400, 404}:
                return True, f"POST /api/pull tiếp nhận yêu cầu (HTTP {phan_hoi.status_code})"
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return False, "Kết nối bị từ chối hoặc quá thời gian chờ (ConnectTimeout/ConnectError)"
    except Exception as err:  # noqa: BLE001
        return False, f"Lỗi kết nối: {err}"
    return False, "POST /api/pull không kết nối được"


def main() -> None:
    """Điểm nhập phân tích đối số dòng lệnh và tiến hành kiểm tra phơi lộ cổng."""
    bo_phan_tich = argparse.ArgumentParser(
        description="Kiểm tra an toàn cổng bộ chạy Ollama / LM Studio qua giao diện mạng LAN"
    )
    bo_phan_tich.add_argument(
        "--dia-chi",
        type=str,
        default=None,
        help="Địa chỉ HTTP của bộ chạy cần kiểm tra (ví dụ: http://192.168.1.100:11434)",
    )
    bo_phan_tich.add_argument(
        "--tu-dong-ip",
        action="store_true",
        help="Tự động xác định địa chỉ IP LAN của máy hiện tại để kiểm tra cổng 11434",
    )

    args = bo_phan_tich.parse_args()

    dia_chi_kiem_tra = args.dia_chi
    if args.tu_dong_ip or not dia_chi_kiem_tra:
        ip_lan = lay_ip_lan_tu_dong()
        dia_chi_kiem_tra = f"http://{ip_lan}:11434"
        print(f"[*] Tự động xác định địa chỉ IP LAN để kiểm tra: {dia_chi_kiem_tra}")

    dia_chi_goc = _kiem_tra_dia_chi_hop_le(dia_chi_kiem_tra)
    print(f"[*] Đang kiểm tra nguy cơ phơi lộ tại: {dia_chi_goc} (timeout 3 giây)...")

    tags_ok, thong_diep_tags = _thu_ket_noi_tags(dia_chi_goc)
    pull_ok, thong_diep_pull = _thu_ket_noi_pull(dia_chi_goc)

    if tags_ok or pull_ok:
        print("\n" + "=" * 70)
        print("CẢNH BÁO BẢO MẬT: MÁY CHỦ OLLAMA ĐANG BỊ PHƠI LỘ RA MẠNG NGOÀI!")
        print(f"Địa chỉ đích: {dia_chi_goc}")
        if tags_ok:
            print(f" - {thong_diep_tags}")
        if pull_ok:
            print(f" - {thong_diep_pull}")
        print("\nNGUY CƠ:")
        print(" Máy chủ Ollama KHÔNG có xác thực. Kẻ ngoài có thể sử dụng GPU miễn phí,")
        print(" tải model lạ lấp đầy ổ cứng hoặc xoá sạch các model đang phục vụ cán bộ.")
        print("\nBA CÁCH NỐI AN TOÀN ĐỂ KHẮC PHỤC (theo thứ tự ưu tiên):")
        print(" 1. Cách A - GIỮ 127.0.0.1 (Mặc định Ollama, khuyến nghị số 1):")
        print("    - Windows/macOS: Giữ mặc định 127.0.0.1, Docker Desktop tự chuyển tiếp qua")
        print("      http://host.docker.internal:11434 tới loopback của máy.")
        print("    - Linux: Backend dùng network_mode: host hoặc chạy backend ngoài container.")
        print(" 2. Cách B - Chỉ dùng trên máy chủ Linux:")
        print("    - Bind vào địa chỉ cầu nối Docker (172.17.0.1) kèm tường lửa ufw chỉ cho dải Docker.")
        print("    - Trên Windows: Dùng PowerShell tạo New-NetFirewallRule hạn chế RemoteAddress.")
        print(" 3. Cách C - Đặt Nginx reverse proxy phía trước (mẫu deploy/nginx-ollama.conf):")
        print("    - Bật xác thực Basic Auth hoặc mTLS.")
        print("    - CHẶN các đường quản trị: /api/pull, /api/create, /api/delete, /api/push, /api/copy.")
        print("    - Chỉ mở các endpoint suy luận: /api/chat, /v1/chat/completions, /api/tags...")
        print("=" * 70)
        sys.exit(1)

    print(f"\nAN TOÀN: Không thể kết nối tới bộ chạy qua địa chỉ {dia_chi_goc}.")
    print("Cổng 11434 không bị phơi lộ ra ngoài (kết nối bị từ chối hoặc bị chặn bởi tường lửa/proxy).")
    sys.exit(0)


if __name__ == "__main__":
    main()
