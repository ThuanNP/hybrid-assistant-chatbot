#!/usr/bin/env python3
"""Kịch bản hiệu chuẩn ngưỡng từ chối RAG (PROMPT 29).

Chạy hiệu chuẩn:
- Ngoài container: uv run --frozen python scripts/hieu_chuan_nguong.py
- Trong container: docker compose exec backend python /srv/scripts/hieu_chuan_nguong.py
"""

import asyncio
import io
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Đảm bảo UTF-8 trên Windows console
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

# Thiết lập đường dẫn import backend
duong_dan_tep = Path(__file__).resolve()
goc_du_an = duong_dan_tep.parent.parent
goc_backend = goc_du_an / "backend"

if str(goc_backend) not in sys.path:
    sys.path.insert(0, str(goc_backend))
if "/srv/backend" not in sys.path:
    sys.path.insert(0, "/srv/backend")

# Xác định thư mục dữ liệu gốc (trên host hoặc trong container)
thu_muc_goc = goc_du_an
if not (thu_muc_goc / "eval").exists() and Path("/srv/eval").exists():
    thu_muc_goc = Path("/srv")

from sqlalchemy import func, select  # noqa: E402

from app.core.csdl import TaiLieuModel, lay_sessionmaker_async  # noqa: E402
from app.core.xac_thuc import NguoiDung  # noqa: E402
from app.llm.router import _doc_cau_hinh_rag  # noqa: E402
from app.rag.nguong import lay_diem_cao_nhat  # noqa: E402
from app.rag.tai_xep_hang import tai_xep_hang  # noqa: E402
from app.rag.truy_hoi import truy_hoi_lai  # noqa: E402


def doc_danh_sach_cau_hoi(duong_dan: Path) -> list[str]:
    """Đọc từng dòng câu hỏi trong tệp văn bản, bỏ dòng trống và chú thích."""
    if not duong_dan.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp câu hỏi: {duong_dan}")
    cac_dong = duong_dan.read_text(encoding="utf-8").splitlines()
    danh_sach = [d.strip() for d in cac_dong if d.strip() and not d.strip().startswith("#")]
    if len(danh_sach) < 10:
        raise ValueError(
            f"Tệp {duong_dan.name} có {len(danh_sach)} câu hỏi, ít hơn yêu cầu tối thiểu (10 câu)."
        )
    return danh_sach


async def lay_so_tai_lieu_trong_kho() -> int:
    """Đếm tổng số tài liệu hiện có trong bảng tai_lieu."""
    factory = lay_sessionmaker_async()
    async with factory() as phien:
        kq = await phien.scalar(select(func.count(TaiLieuModel.id)))
        return int(kq or 0)


async def danh_gia_nhom(
    danh_sach_cau_hoi: list[str],
    nguoi_dung: NguoiDung,
) -> list[dict[str, Any]]:
    """Chạy truy hồi và tái xếp hạng cho từng câu hỏi, ghi nhận điểm cao nhất."""
    ket_qua: list[dict[str, Any]] = []
    for cau in danh_sach_cau_hoi:
        ung_vien_list = await truy_hoi_lai(cau, nguoi=nguoi_dung)
        tai_xep = tai_xep_hang(cau, ung_vien_list)
        diem_cao = lay_diem_cao_nhat(tai_xep)
        ma_tai_lieu_top1 = tai_xep[0].ma_tai_lieu if tai_xep else ""
        tieu_de_top1 = tai_xep[0].tieu_de_muc if tai_xep else ""

        ket_qua.append(
            {
                "cau_hoi": cau,
                "diem_cao_nhat": round(diem_cao, 4),
                "ma_tai_lieu_top1": ma_tai_lieu_top1,
                "tieu_de_top1": tieu_de_top1,
            }
        )
    return ket_qua


async def chay_hieu_chuan() -> None:
    """Thực thi toàn bộ quy trình hiệu chuẩn ngưỡng từ chối."""
    tep_trong_kho = thu_muc_goc / "eval" / "cau_hoi_co_trong_kho.txt"
    tep_ngoai_kho = thu_muc_goc / "eval" / "cau_hoi_ngoai_kho.txt"
    tep_xuat_json = thu_muc_goc / "docs" / "hieu-chuan-nguong.json"

    print("=" * 80)
    print(" BẮT ĐẦU HIỆU CHUẨN NGƯỠNG TỪ CHỐI RAG (PROMPT 29)")
    print("=" * 80)

    cau_trong_kho = doc_danh_sach_cau_hoi(tep_trong_kho)
    cau_ngoai_kho = doc_danh_sach_cau_hoi(tep_ngoai_kho)
    print(f"Đã đọc {len(cau_trong_kho)} câu trong kho và {len(cau_ngoai_kho)} câu ngoài kho.")

    # Người dùng mẫu cố định thuộc phòng KY_THUAT_AN_TOAN:
    # Đọc được tài liệu dùng chung (LUAT-61-2024-QH15, HD-DMTMN-2025),
    # Không đọc được QD-DICH-VU-DIEN-2024.
    nguoi_dung_mau = NguoiDung(
        id=999,
        email="mau_hieu_chuan@evnhcmc.vn",
        ho_ten="Cán bộ Kỹ thuật An toàn Kiểm định",
        vai_tro="nguoi_dung",
        phong_ban="KY_THUAT_AN_TOAN",
        pham_vi_doc=["KY_THUAT_AN_TOAN"],
    )

    print("\n1. Đang đánh giá nhóm câu hỏi CÓ trong kho...")
    kq_trong = await danh_gia_nhom(cau_trong_kho, nguoi_dung_mau)
    for idx, item in enumerate(kq_trong, 1):
        print(f"  [{idx:02d}] Điểm: {item['diem_cao_nhat']:>6.2f} | {item['cau_hoi'][:50]}...")

    print("\n2. Đang đánh giá nhóm câu hỏi NGOÀI kho...")
    kq_ngoai = await danh_gia_nhom(cau_ngoai_kho, nguoi_dung_mau)
    for idx, item in enumerate(kq_ngoai, 1):
        print(f"  [{idx:02d}] Điểm: {item['diem_cao_nhat']:>6.2f} | {item['cau_hoi'][:50]}...")

    diem_thap_nhat_trong_kho = min(x["diem_cao_nhat"] for x in kq_trong)
    diem_cao_nhat_ngoai_kho = max(x["diem_cao_nhat"] for x in kq_ngoai)
    bien_an_toan = round(diem_thap_nhat_trong_kho - diem_cao_nhat_ngoai_kho, 4)
    nguong_de_xuat = round((diem_thap_nhat_trong_kho + diem_cao_nhat_ngoai_kho) / 2, 4)

    print("\n" + "=" * 80)
    print(" KẾT QUẢ TÍNH TOÁN HIỆU CHUẨN BỐN CON SỐ")
    print("=" * 80)
    print(f"1. Điểm thấp nhất nhóm trong kho : {diem_thap_nhat_trong_kho:.4f}")
    print(f"2. Điểm cao nhất nhóm ngoài kho  : {diem_cao_nhat_ngoai_kho:.4f}")
    print(f"3. Biên an toàn (hiệu hai số)    : {bien_an_toan:.4f}")
    print(f"4. Ngưỡng đề xuất (trung điểm)   : {nguong_de_xuat:.4f}")
    print("=" * 80)

    # Kiểm tra hiện tượng chồng lấn
    if bien_an_toan <= 0:
        print("\n[CẢNH BÁO CHỒNG LẤN NGHIÊM TRỌNG]: Biên an toàn <= 0!")
        print("Dấu hiệu kho chưa đủ phân biệt hoặc việc cắt đoạn chưa tốt.")
        cau_chong_lan_ngoai = [x for x in kq_ngoai if x["diem_cao_nhat"] >= diem_thap_nhat_trong_kho]
        cau_chong_lan_trong = [x for x in kq_trong if x["diem_cao_nhat"] <= diem_cao_nhat_ngoai_kho]
        print("Các câu ngoài kho bị điểm cao:")
        for c in cau_chong_lan_ngoai:
            print(f"  - ({c['diem_cao_nhat']}) {c['cau_hoi']}")
        print("Các câu trong kho bị điểm thấp:")
        for c in cau_chong_lan_trong:
            print(f"  - ({c['diem_cao_nhat']}) {c['cau_hoi']}")
    elif bien_an_toan < 0.05:
        print("\n[CẢNH BÁO]: Biên an toàn dưới 0.05 - biên hẹp, phải hiệu chuẩn lại mỗi khi kho thay đổi đáng kể.")

    # Ghi nhận kết quả ra tệp docs/hieu-chuan-nguong.json
    so_tai_lieu = await lay_so_tai_lieu_trong_kho()
    rag_cfg = _doc_cau_hinh_rag()
    model_nhung = str(rag_cfg.get("model_nhung", "bge-m3"))

    du_lieu_json = {
        "ngay": date.today().isoformat(),
        "model_nhung": model_nhung,
        "so_tai_lieu": so_tai_lieu,
        "diem_thap_nhat_trong_kho": diem_thap_nhat_trong_kho,
        "diem_cao_nhat_ngoai_kho": diem_cao_nhat_ngoai_kho,
        "bien_an_toan": bien_an_toan,
        "nguong_de_xuat": nguong_de_xuat,
        "chi_tiet_trong_kho": kq_trong,
        "chi_tiet_ngoai_kho": kq_ngoai,
    }

    tep_xuat_json.parent.mkdir(parents=True, exist_ok=True)
    tep_xuat_json.write_text(
        json.dumps(du_lieu_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nĐã ghi kết quả hiệu chuẩn vào: {tep_xuat_json}")


def main() -> None:
    """Điểm nhập kịch bản."""
    asyncio.run(chay_hieu_chuan())


if __name__ == "__main__":
    main()
