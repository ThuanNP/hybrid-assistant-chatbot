"""Kịch bản kiểm tra kết nối và chứng thực tới các nhà cung cấp đám mây qua LiteLLM.

Ghi chú quan trọng: đây là một trong hai kịch bản DUY NHẤT được phép gọi thẳng bộ chạy
và litellm ngoài router.py, vì chúng là công cụ chẩn đoán chạy tay, không nằm trong ứng dụng.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Cấu hình encoding utf-8 để in tiếng Việt chính xác trên Windows / Git Bash
sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục backend vào sys.path để nạp cấu hình hệ thống
thu_muc_goc = Path(__file__).resolve().parents[1]
backend_dir = thu_muc_goc / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import litellm
from app.config import DUONG_DAN_ENV_MAC_DINH, CauHinhTangDamMay, _doc_bien_gop, cau_hinh

# Tắt thông báo gỡ lỗi mặc định của litellm để bảng kết quả rõ ràng
litellm.suppress_debug_info = True


def lay_khoa_api_tu_moi_truong(ten_bien_khoa: str) -> str | None:
    """Lấy khoá API từ môi trường hoặc tệp .env, trả về None nếu thiếu hoặc là giá trị mẫu."""
    bien_gop = _doc_bien_gop(DUONG_DAN_ENV_MAC_DINH)
    khoa = bien_gop.get(ten_bien_khoa)
    if not khoa or not khoa.strip() or khoa == "dan-khoa-that-vao-day":
        return None
    return khoa.strip()


def kiem_tra_mot_tang(
    tang: CauHinhTangDamMay,
    khoa_api: str | None,
) -> tuple[dict[str, Any], list[str]]:
    """Gọi thử một tầng đám mây bằng litellm và ghi nhận kết quả chi tiết."""
    goi_y: list[str] = []

    if not khoa_api:
        return {
            "tang": tang.tang,
            "ten": tang.ten,
            "model": tang.model,
            "trang_thai": "BỎ QUA (thiếu khoá)",
            "do_tre": "-",
            "token_vao": "-",
            "token_ra": "-",
            "model_thuc": "-",
        }, goi_y

    tham_so_goi: dict[str, Any] = {
        "model": tang.model,
        "messages": [{"role": "user", "content": "Trả lời đúng một từ: xin chào"}],
        "api_key": khoa_api,
        "timeout": tang.timeout_giay,
    }
    if tang.tham_so_them:
        tham_so_goi["extra_body"] = tang.tham_so_them

    bat_dau = time.perf_counter()
    try:
        phan_hoi = litellm.completion(**tham_so_goi)
        do_tre_ms = int((time.perf_counter() - bat_dau) * 1000)
        so_token_vao = "-"
        so_token_ra = "-"
        usage = getattr(phan_hoi, "usage", None)
        if usage:
            so_token_vao = str(getattr(usage, "prompt_tokens", "-"))
            so_token_ra = str(getattr(usage, "completion_tokens", "-"))

        model_thuc = getattr(phan_hoi, "model", None) or tang.model

        return {
            "tang": tang.tang,
            "ten": tang.ten,
            "model": tang.model,
            "trang_thai": "ĐẠT",
            "do_tre": f"{do_tre_ms} ms",
            "token_vao": so_token_vao,
            "token_ra": so_token_ra,
            "model_thuc": model_thuc,
        }, goi_y
    except Exception as loi:
        do_tre_ms = int((time.perf_counter() - bat_dau) * 1000)
        thong_diep_loi = str(loi).lower()
        ma_loi = getattr(loi, "status_code", None)

        la_loi_401 = (
            ma_loi == 401
            or "401" in thong_diep_loi
            or "authentication" in thong_diep_loi
            or "api_key_invalid" in thong_diep_loi
            or isinstance(loi, litellm.exceptions.AuthenticationError)
        )
        la_loi_404_model = (
            ma_loi == 404
            or "404" in thong_diep_loi
            or "model" in thong_diep_loi
            or isinstance(loi, litellm.exceptions.NotFoundError)
        )

        if la_loi_401:
            goi_y.append(f"Tầng {tang.tang} ({tang.ten}): Lỗi 401 -> gợi ý kiểm tra khoá trong .env.")
        elif la_loi_404_model:
            goi_y.append(
                f"Tầng {tang.tang} ({tang.ten}): Lỗi 404/model -> "
                "gợi ý tra danh mục model của nhà cung cấp và sửa config/models.yaml."
            )
        else:
            goi_y.append(f"Tầng {tang.tang} ({tang.ten}): Lỗi kết nối tới nhà cung cấp.")

        return {
            "tang": tang.tang,
            "ten": tang.ten,
            "model": tang.model,
            "trang_thai": "HỎNG",
            "do_tre": f"{do_tre_ms} ms",
            "token_vao": "-",
            "token_ra": "-",
            "model_thuc": "-",
        }, goi_y


def in_bang_ket_qua(danh_sach_ket_qua: list[dict[str, Any]]) -> None:
    """In bảng kết quả kiểm tra các tầng đám mây ra màn hình."""
    tieu_de = (
        f"{'Tầng':<4} | {'Tên':<16} | {'Mô hình khai báo':<30} | "
        f"{'Trạng thái':<20} | {'Độ trễ':<10} | {'Vào':<5} | {'Ra':<5} | {'Mô hình thực dùng'}"
    )
    print("\n" + "=" * len(tieu_de))
    print(tieu_de)
    print("-" * len(tieu_de))

    for kq in danh_sach_ket_qua:
        dong = (
            f"{kq['tang']:<4} | {kq['ten']:<16} | {kq['model']:<30} | "
            f"{kq['trang_thai']:<20} | {kq['do_tre']:<10} | "
            f"{kq['token_vao']:<5} | {kq['token_ra']:<5} | {kq['model_thuc']}"
        )
        print(dong)
    print("=" * len(tieu_de) + "\n")


def chay_kiem_tra() -> int:
    """Điều phối toàn bộ quy trình kiểm tra các nhà cung cấp đám mây."""
    trinh_phan_tich = argparse.ArgumentParser(
        description="Kiểm tra kết nối tới các nhà cung cấp đám mây qua LiteLLM."
    )
    trinh_phan_tich.add_argument(
        "--tang",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Chỉ định tầng kiểm tra (1, 2, 3, 4 hoặc all, mặc định all).",
    )
    tham_so = trinh_phan_tich.parse_args()

    cac_tang = cau_hinh.chuoi_dam_may
    if tham_so.tang != "all":
        so_tang_chon = int(tham_so.tang)
        cac_tang = [t for t in cac_tang if t.tang == so_tang_chon]

    danh_sach_ket_qua: list[dict[str, Any]] = []
    tat_ca_goi_y: list[str] = []

    for tang in cac_tang:
        khoa_api = lay_khoa_api_tu_moi_truong(tang.api_key_env)
        kq, goi_y = kiem_tra_mot_tang(tang, khoa_api)
        danh_sach_ket_qua.append(kq)
        tat_ca_goi_y.extend(goi_y)

    in_bang_ket_qua(danh_sach_ket_qua)

    if tat_ca_goi_y:
        print("Ghi chú & Gợi ý khắc phục:")
        for gy in tat_ca_goi_y:
            print(f"- {gy}")
        print()

    # Mã thoát 1 nếu cả tầng 1 và tầng 2 đều không ĐẠT
    tang_1_dat = any(k["tang"] == 1 and k["trang_thai"] == "ĐẠT" for k in danh_sach_ket_qua)
    tang_2_dat = any(k["tang"] == 2 and k["trang_thai"] == "ĐẠT" for k in danh_sach_ket_qua)

    if not tang_1_dat and not tang_2_dat:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(chay_kiem_tra())
