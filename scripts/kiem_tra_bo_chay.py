"""Kịch bản kiểm tra kết nối và trạng thái bộ chạy mô hình cục bộ (Ollama / LM Studio).

Ghi chú quan trọng: đây là một trong hai kịch bản DUY NHẤT được phép gọi thẳng bộ chạy
và litellm ngoài router.py, vì chúng là công cụ chẩn đoán chạy tay, không nằm trong ứng dụng.
"""

import ipaddress
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

# Cấu hình encoding utf-8 để in tiếng Việt chính xác trên Windows / Git Bash
sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục backend vào sys.path để nạp cấu hình hệ thống
thu_muc_goc = Path(__file__).resolve().parents[1]
backend_dir = thu_muc_goc / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import cau_hinh


def kiem_tra_dia_chi_an_toan(dia_chi: str) -> None:
    """Kiểm tra và in cảnh báo nếu địa chỉ bộ chạy trỏ tới 0.0.0.0 hoặc IP công cộng."""
    try:
        parsed = urlparse(dia_chi)
        host = parsed.hostname or ""
        if host == "0.0.0.0":
            print("CẢNH BÁO BẢO MẬT: DIA_CHI_BO_CHAY trỏ tới 0.0.0.0 (nguy cơ lộ giao diện mạng).")
            return
        ip = ipaddress.ip_address(host)
        if ip.is_global:
            print(
                f"CẢNH BÁO BẢO MẬT: DIA_CHI_BO_CHAY trỏ tới địa chỉ công cộng ({host}), "
                "vi phạm quy tắc chỉ dùng loopback hoặc mạng nội bộ!"
            )
    except ValueError:
        # Không phải định dạng IP thuần túy (ví dụ: localhost, host.docker.internal)
        pass


def dinh_dang_dung_luong(so_byte: int) -> str:
    """Chuyển đổi số byte sang định dạng MB hoặc GB dễ đọc."""
    if so_byte >= 1024**3:
        return f"{so_byte / (1024**3):.2f} GB"
    return f"{so_byte / (1024**2):.1f} MB"


def dinh_dang_thoi_gian_con_lai(chuoi_iso: str | None) -> str:
    """Tính toán thời gian còn lại trước khi mô hình bị giải phóng khỏi VRAM/RAM."""
    if not chuoi_iso:
        return "Không thời hạn"
    try:
        thoi_gian_het_han = datetime.fromisoformat(chuoi_iso)
        bay_gio = datetime.now(timezone.utc)
        so_giay = (thoi_gian_het_han - bay_gio).total_seconds()
        if so_giay <= 0:
            return "Sắp giải phóng"
        phut = int(so_giay // 60)
        giay = int(so_giay % 60)
        return f"{phut}m {giay}s"
    except Exception:
        return chuoi_iso


def kiem_tra_ollama(
    goc_url: str,
    ho_so_ten: str,
    danh_sach_model: list[tuple[str, str]],
) -> tuple[bool, bool, list[str]]:
    """Kiểm tra kết nối và đối chiếu danh sách mô hình cài đặt trên Ollama qua /api/tags."""
    print(f"\n=== KIỂM TRA BỘ CHẠY OLLAMA (Hồ sơ GPU: {ho_so_ten}) ===")
    url_tags = f"{goc_url}/api/tags"
    try:
        with httpx.Client(timeout=10.0) as client:
            phan_hoi = client.get(url_tags)
            if phan_hoi.status_code != 200:
                print(f"LỖI: Gọi {url_tags} thất bại với mã HTTP {phan_hoi.status_code}.")
                return False, False, []
            du_lieu = phan_hoi.json()
    except Exception as loi:
        print(f"LỖI: Không thể kết nối tới bộ chạy Ollama tại {goc_url}: {loi}")
        return False, False, []

    cac_the_co_san: set[str] = set()
    for item in du_lieu.get("models", []):
        ten = item.get("name", "")
        the_model = item.get("model", "")
        if ten:
            cac_the_co_san.add(ten)
            cac_the_co_san.add(ten.removesuffix(":latest"))
        if the_model:
            cac_the_co_san.add(the_model)
            cac_the_co_san.add(the_model.removesuffix(":latest"))

    print(f"\nBảng đối chiếu mô hình hồ sơ {ho_so_ten}:")
    print(f"{'Bậc':<8} | {'Thẻ mô hình':<30} | {'Trạng thái':<12}")
    print("-" * 56)

    cac_model_thieu: list[str] = []
    for bac, the_yeu_cau in danh_sach_model:
        co_san = the_yeu_cau in cac_the_co_san or f"{the_yeu_cau}:latest" in cac_the_co_san
        trang_thai = "ĐÃ CÓ" if co_san else "THIẾU"
        if not co_san:
            cac_model_thieu.append(the_yeu_cau)
        print(f"{bac:<8} | {the_yeu_cau:<30} | {trang_thai:<12}")

    if cac_model_thieu:
        print("\nCác mô hình còn thiếu, cần chạy lệnh sau:")
        for the_thieu in cac_model_thieu:
            print(f"ollama pull {the_thieu}")
        return True, False, cac_model_thieu

    return True, True, []


def kiem_tra_ollama_ps(goc_url: str, so_model_nap_cung_luc: int) -> None:
    """Kiểm tra các mô hình đang nằm trong bộ nhớ Ollama qua GET /api/ps."""
    print("\n=== CÁC MÔ HÌNH ĐANG NẰM TRONG BỘ NHỚ (/api/ps) ===")
    url_ps = f"{goc_url}/api/ps"
    try:
        with httpx.Client(timeout=10.0) as client:
            phan_hoi = client.get(url_ps)
            if phan_hoi.status_code != 200:
                print(f"Lỗi: Gọi {url_ps} trả về mã HTTP {phan_hoi.status_code}.")
                return
            du_lieu = phan_hoi.json()
    except Exception as loi:
        print(f"Không thể truy vấn {url_ps}: {loi}")
        return

    danh_sach = du_lieu.get("models", [])
    if not danh_sach:
        print("(Không có mô hình nào đang nạp trong bộ nhớ)")
        return

    print(f"{'Tên':<24} | {'Dung lượng':<12} | {'VRAM':<12} | {'Còn lại':<15}")
    print("-" * 70)
    for item in danh_sach:
        ten = item.get("name", "")
        dung_luong = dinh_dang_dung_luong(item.get("size", 0))
        dung_luong_vram = dinh_dang_dung_luong(item.get("size_vram", 0))
        con_lai = dinh_dang_thoi_gian_con_lai(item.get("expires_at"))
        print(f"{ten:<24} | {dung_luong:<12} | {dung_luong_vram:<12} | {con_lai:<15}")

    if so_model_nap_cung_luc == 1 and len(danh_sach) > 1:
        print(
            "\nCẢNH BÁO: OLLAMA_MAX_LOADED_MODELS chưa đặt bằng 1 "
            f"(GPU 8 GB sẽ tràn VRAM sang RAM và chậm hẳn). Hiện có {len(danh_sach)} model đang nạp."
        )


def kiem_tra_lmstudio(
    dia_chi_url: str,
    danh_sach_model: list[tuple[str, str]],
) -> tuple[bool, bool, list[str]]:
    """Kiểm tra kết nối và đối chiếu danh sách mô hình trên LM Studio qua /models."""
    print(f"\n=== KIỂM TRA BỘ CHẠY LM STUDIO ===")
    url_models = f"{dia_chi_url.rstrip('/')}/models"
    try:
        with httpx.Client(timeout=10.0) as client:
            phan_hoi = client.get(url_models)
            if phan_hoi.status_code != 200:
                print(f"LỖI: Gọi {url_models} trả về mã HTTP {phan_hoi.status_code}.")
                return False, False, []
            du_lieu = phan_hoi.json()
    except Exception as loi:
        print(f"LỖI: Không thể kết nối tới LM Studio tại {dia_chi_url}: {loi}")
        return False, False, []

    cac_id_co_san: set[str] = {item.get("id", "") for item in du_lieu.get("data", [])}
    cac_model_thieu: list[str] = []

    print(f"{'Bậc':<8} | {'Tên mô hình':<30} | {'Trạng thái':<12}")
    print("-" * 56)
    for bac, the_yeu_cau in danh_sach_model:
        co_san = the_yeu_cau in cac_id_co_san
        trang_thai = "ĐÃ CÓ" if co_san else "THIẾU"
        if not co_san:
            cac_model_thieu.append(the_yeu_cau)
        print(f"{bac:<8} | {the_yeu_cau:<30} | {trang_thai:<12}")

    if cac_model_thieu:
        print("\nCác mô hình còn thiếu:")
        for the_thieu in cac_model_thieu:
            print(f"lms get {the_thieu}")
        print("Nhắc nhở: Bạn cũng có thể tìm và tải mô hình trực tiếp trong giao diện LM Studio.")
        return True, False, cac_model_thieu

    return True, True, []


def _yeu_cau_chat_thu(
    loai_bo_chay: str,
    dia_chi_url: str,
    model_chinh: str,
    num_ctx: int,
    keep_alive: str,
) -> tuple[str, dict[str, object]]:
    """Tạo endpoint và thân yêu cầu chat thử theo từng loại bộ chạy.

    Ollama dùng /api/chat vì giao diện /v1 tương thích OpenAI bỏ qua keep_alive và
    options.num_ctx: gọi qua /v1 sẽ nạp model với ngữ cảnh mặc định, có thể tràn VRAM.
    """
    tin_nhan = [{"role": "user", "content": "Xin chào"}]
    if loai_bo_chay == "ollama":
        goc_url = dia_chi_url.rstrip("/").removesuffix("/v1").rstrip("/")
        return f"{goc_url}/api/chat", {
            "model": model_chinh,
            "messages": tin_nhan,
            "stream": True,
            "keep_alive": keep_alive,
            "options": {"num_ctx": num_ctx, "num_predict": 8},
        }
    return f"{dia_chi_url.rstrip('/')}/chat/completions", {
        "model": model_chinh,
        "messages": tin_nhan,
        "max_tokens": 8,
        "stream": True,
    }


def _co_token_trong_dong(loai_bo_chay: str, dong: str) -> bool:
    """Nhận diện dòng phát đầu tiên có nội dung (NDJSON của Ollama hoặc SSE của LM Studio)."""
    if loai_bo_chay == "ollama":
        return dong.strip().startswith("{")
    return dong.startswith("data: ") and not dong.endswith("[DONE]")


def thu_nghiem_chat(
    loai_bo_chay: str,
    dia_chi_url: str,
    model_chinh: str,
    num_ctx: int,
    keep_alive: str,
) -> None:
    """Gọi thử model bậc chính (đúng num_ctx, keep_alive) để đo thời gian tới token đầu tiên."""
    print(f"\n--- Thử nghiệm chat (Bậc chính: {model_chinh}, num_ctx {num_ctx}) ---")
    endpoint, du_lieu_gui = _yeu_cau_chat_thu(
        loai_bo_chay, dia_chi_url, model_chinh, num_ctx, keep_alive
    )
    bat_dau = time.perf_counter()
    thoi_gian_token_dau: float | None = None
    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("POST", endpoint, json=du_lieu_gui) as phan_hoi:
                if phan_hoi.status_code != 200:
                    print(f"Yêu cầu chat thử trả về mã lỗi HTTP {phan_hoi.status_code}.")
                    return
                for dong in phan_hoi.iter_lines():
                    if _co_token_trong_dong(loai_bo_chay, dong):
                        thoi_gian_token_dau = time.perf_counter() - bat_dau
                        break
    except httpx.HTTPError as loi:
        print(f"Lỗi khi gọi chat thử: {loi}")
        return

    if thoi_gian_token_dau is None:
        print("Không nhận được token phản hồi nào.")
        return
    print(f"Thời gian tới token đầu tiên (TTFT): {thoi_gian_token_dau:.2f} giây.")
    if thoi_gian_token_dau > 5.0:
        print("Giải thích: đây là thời gian nạp model vào VRAM, lần sau sẽ nhanh.")


def chay_kiem_tra() -> int:
    """Điều phối toàn bộ quy trình kiểm tra bộ chạy cục bộ."""
    dia_chi_bo_chay = cau_hinh.bo_chay.dia_chi
    loai_bo_chay = cau_hinh.bo_chay.loai.lower()
    ho_so_gpu = cau_hinh.ho_so_gpu_dang_chon

    kiem_tra_dia_chi_an_toan(dia_chi_bo_chay)

    danh_sach_model = [(b.bac, b.model) for b in cau_hinh.bac_local]
    model_chinh = cau_hinh.bac_local[0].model if cau_hinh.bac_local else ""

    bo_chay_song = False
    du_model = False
    cac_model_thieu: list[str] = []

    if loai_bo_chay == "ollama":
        goc_url = dia_chi_bo_chay.rstrip("/").removesuffix("/v1").rstrip("/")
        bo_chay_song, du_model, cac_model_thieu = kiem_tra_ollama(
            goc_url,
            ho_so_gpu,
            danh_sach_model,
        )
        if bo_chay_song:
            kiem_tra_ollama_ps(goc_url, cau_hinh.so_model_nap_cung_luc)
    elif loai_bo_chay == "lmstudio":
        bo_chay_song, du_model, cac_model_thieu = kiem_tra_lmstudio(
            dia_chi_bo_chay,
            danh_sach_model,
        )
    else:
        print(f"Loại bộ chạy không được hỗ trợ: '{loai_bo_chay}'")
        return 1

    if bo_chay_song and model_chinh in cac_model_thieu:
        print(f"\nBỏ qua thử nghiệm chat: mô hình bậc chính '{model_chinh}' chưa được tải.")
    elif bo_chay_song:
        thu_nghiem_chat(
            loai_bo_chay,
            dia_chi_bo_chay,
            model_chinh,
            cau_hinh.bac_local[0].num_ctx,
            cau_hinh.local_chung.keep_alive,
        )

    # Mã thoát 1 nếu thiếu model hoặc bộ chạy không phản hồi
    if not bo_chay_song or not du_model:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(chay_kiem_tra())
