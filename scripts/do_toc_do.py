"""Kịch bản chẩn đoán đo tốc độ sinh token và tiêu hao VRAM của bộ chạy mô hình cục bộ.

Ghi chú quan trọng: đây là một trong các kịch bản ngoại lệ được phép gọi thẳng bộ chạy
ngoài router.py (đã được bổ sung vào danh sách ngoại lệ của Quy tắc tuyệt đối 1 trong AGENTS.md),
vì là công cụ chẩn đoán chạy tay, không nằm trong ứng dụng.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Cấu hình stdout utf-8 để in tiếng Việt chính xác trên Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục backend vào sys.path để nạp cấu hình hệ thống
thu_muc_goc = Path(__file__).resolve().parents[1]
backend_dir = thu_muc_goc / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import cau_hinh

# Danh sách câu hỏi nghiệp vụ ngành điện năng (ngắn gọn, súc tích)
DANH_SACH_CAU_HOI = [
    # Câu 1: Ngắn - tra cứu thủ tục
    "Thủ tục sang tên hợp đồng mua bán điện sinh hoạt gồm những giấy tờ gì?",
    # Câu 2: Vừa - biểu giá bậc thang
    "Cách tính tiền điện sinh hoạt bậc thang cho hộ gia đình hiện nay?",
    # Câu 3: Kỹ thuật - kiểm tra công tơ
    "Quy trình xử lý khi công tơ điện tử đo đếm của khách hàng bị cháy hỏng?",
    # Câu 4: Chính sách - điện áp mái
    "Điều kiện kỹ thuật đấu nối điện mặt trời mái nhà tự sản tự tiêu?",
    # Câu 5: Pháp lý - an toàn điện
    "Trường hợp nào bên bán điện được phép ngừng cấp điện khẩn cấp không báo trước?",
]


def _chuan_hoa_dia_chi_chay_tay(dia_chi: str) -> str:
    """Thay thế host.docker.internal bằng localhost và bỏ /v1 ở cuối."""
    url = dia_chi.replace("host.docker.internal", "localhost").replace("db", "localhost")
    return url.rstrip("/").removesuffix("/v1").rstrip("/")


def _doc_vram_model(dia_chi: str, ten_model: str) -> str:
    """Đọc dung lượng VRAM thực tế mô hình đang chiếm dụng từ endpoint /api/ps của Ollama."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{dia_chi}/api/ps")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                for m in models:
                    name = m.get("name", "")
                    if ten_model.split(":")[0] in name or name.split(":")[0] in ten_model:
                        size_vram = m.get("size_vram", 0)
                        if size_vram > 0:
                            return f"{size_vram / (1024**3):.2f} GB"
                if models:
                    size_vram = models[0].get("size_vram", 0)
                    if size_vram > 0:
                        return f"{size_vram / (1024**3):.2f} GB"
    except Exception:
        pass
    return "N/A"


def do_toc_do_model(so_cau: int = 3, max_tokens: int = 30) -> None:
    """Thực thi đo tốc độ mô hình cục bộ và in bảng kết quả chi tiết."""
    dia_chi = _chuan_hoa_dia_chi_chay_tay(cau_hinh.bo_chay.dia_chi)
    ho_so = cau_hinh.ho_so_gpu_dang_chon
    if not cau_hinh.bac_local:
        print("LỖI: Không tìm thấy cấu hình bậc local nào.", flush=True)
        sys.exit(1)

    bac_1 = cau_hinh.bac_local[0]
    model_chinh = bac_1.model
    num_ctx = min(bac_1.num_ctx, 4096)

    print("=" * 78, flush=True)
    print("CHẨN ĐOÁN HIỆU NĂNG BỘ CHẠY MÔ HÌNH CỤC BỘ", flush=True)
    print(f"Địa chỉ bộ chạy: {dia_chi}", flush=True)
    print(f"Hồ sơ GPU:       {ho_so}", flush=True)
    print(f"Mô hình bậc 1:   {model_chinh}", flush=True)
    print(f"Ngữ cảnh num_ctx:{num_ctx} | Giới hạn token sinh: {max_tokens}", flush=True)
    print("=" * 78, flush=True)

    # 1. Kiểm tra kết nối tới bộ chạy
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{dia_chi}/api/tags")
            if r.status_code != 200:
                print(f"LỖI: Bộ chạy phản hồi mã HTTP {r.status_code}", flush=True)
                sys.exit(1)
    except Exception as err:
        print(f"LỖI KẾT NỐI: Không kết nối được tới bộ chạy tại {dia_chi}: {err}", flush=True)
        print("Vui lòng đảm bảo Ollama / LM Studio đang chạy trên máy.", flush=True)
        sys.exit(1)

    # 2. Lượt hâm nóng (warmup) nhanh - 10 tokens
    print("\nĐang thực hiện lượt hâm nóng (warmup)...", flush=True)
    payload_warmup = {
        "model": model_chinh,
        "prompt": "Xin chào",
        "stream": False,
        "options": {"num_ctx": num_ctx, "num_predict": 10},
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            client.post(f"{dia_chi}/api/generate", json=payload_warmup)
        print("-> Đã hâm nóng thành công.\n", flush=True)
    except Exception as err:
        print(f"CẢNH BÁO: Lượt hâm nóng gặp lỗi: {err}", flush=True)

    # 3. Chạy đo câu hỏi nghiệp vụ
    ds_chay = DANH_SACH_CAU_HOI[:so_cau]
    ket_qua: list[dict[str, Any]] = []

    print("-" * 78, flush=True)
    print(
        f"{'STT':<4} | {'Độ dài vào':<11} | {'Token ra':<9} | {'TTFT (ms)':<10} | {'Tốc độ (tok/s)':<15} | {'VRAM':<10}",
        flush=True,
    )
    print("-" * 78, flush=True)

    with httpx.Client(timeout=60.0) as client:
        for idx, cau_hoi in enumerate(ds_chay, 1):
            payload = {
                "model": model_chinh,
                "prompt": cau_hoi,
                "stream": True,
                "options": {"num_ctx": num_ctx, "num_predict": max_tokens},
            }

            t0 = time.perf_counter()
            ttft_ms = 0.0
            token_ra = 0
            tok_s = 0.0

            try:
                with client.stream("POST", f"{dia_chi}/api/generate", json=payload) as response:
                    for line in response.iter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        if ttft_ms == 0.0:
                            ttft_ms = round((time.perf_counter() - t0) * 1000.0, 1)

                        if chunk.get("done"):
                            eval_count = chunk.get("eval_count", 0)
                            eval_duration_ns = chunk.get("eval_duration", 0)
                            token_ra = eval_count
                            if eval_duration_ns > 0 and eval_count > 0:
                                tok_s = round(eval_count / (eval_duration_ns / 1e9), 2)
                            else:
                                tong_giay = max(time.perf_counter() - t0, 0.001)
                                tok_s = round(token_ra / tong_giay, 2)
                            break
            except Exception as err:
                print(f"Lỗi lượt {idx}: {err}", flush=True)
                tok_s = 0.0

            vram_str = _doc_vram_model(dia_chi, model_chinh)
            do_dai_vao = len(cau_hoi)

            item = {
                "stt": idx,
                "do_dai_vao": do_dai_vao,
                "token_ra": token_ra,
                "ttft_ms": ttft_ms,
                "tok_s": tok_s,
                "vram": vram_str,
            }
            ket_qua.append(item)

            print(
                f"{idx:<4} | {do_dai_vao:<11} | {token_ra:<9} | {ttft_ms:<10.1f} | {tok_s:<15.2f} | {vram_str:<10}",
                flush=True,
            )

    print("-" * 78, flush=True)
    # Tính tốc độ trung bình
    ds_tok_s = [k["tok_s"] for k in ket_qua if k["tok_s"] > 0]
    avg_tok_s = round(sum(ds_tok_s) / len(ds_tok_s), 2) if ds_tok_s else 0.0
    print(f"Tốc độ sinh trung bình: {avg_tok_s} tok/s", flush=True)
    print("=" * 78, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đo tốc độ bộ chạy mô hình cục bộ")
    parser.add_argument("--so-cau", type=int, default=3, help="Số lượng câu hỏi cần chạy (mặc định: 3)")
    parser.add_argument("--max-tokens", type=int, default=30, help="Số token tối đa sinh ra mỗi câu (mặc định: 30)")
    args = parser.parse_args()

    do_toc_do_model(so_cau=args.so_cau, max_tokens=args.max_tokens)
