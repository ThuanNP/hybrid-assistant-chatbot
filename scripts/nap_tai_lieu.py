#!/usr/bin/env python3
"""Kịch bản dòng lệnh nạp tài liệu kho tri thức RAG hoặc cập nhật hết hiệu lực.

Cách dùng:
- Nạp thư mục hoặc tệp:
    python scripts/nap_tai_lieu.py data/mau/
    docker compose exec backend python /srv/scripts/nap_tai_lieu.py /srv/data/mau/
- Đánh dấu hết hiệu lực văn bản:
    python scripts/nap_tai_lieu.py --het-hieu-luc <ma> --thay-the <ma_moi>
    docker compose exec backend python /srv/scripts/nap_tai_lieu.py --het-hieu-luc LUAT-28-2004-QH11 --thay-the LUAT-61-2024-QH15
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Đảm bảo app có thể import từ backend
goc_backend = Path(__file__).resolve().parent.parent / "backend"
if str(goc_backend) not in sys.path:
    sys.path.insert(0, str(goc_backend))
if "/srv/backend" not in sys.path:
    sys.path.insert(0, "/srv/backend")

from app.rag.nap_tai_lieu import (
    KetQuaNap,
    cap_nhat_het_hieu_luc,
    nap_mot_tai_lieu,
)
from app.rag.nhung import (
    dat_lai_tat_ca_vector,
    nhung_doan_chua_co_vector,
)


def in_bang_ket_qua(danh_sach_kq: list[KetQuaNap]) -> None:
    """In bảng tổng hợp kết quả nạp tài liệu ra màn hình console."""
    cot_tep = 68
    cot_doan = 9
    cot_trang_thai = 12
    cot_ly_do = 35

    duong_ke = "=" * (cot_tep + cot_doan + cot_trang_thai + cot_ly_do + 9)
    print("\n" + duong_ke)
    print(
        f"| {'Tệp':<{cot_tep}} "
        f"| {'Số đoạn':<{cot_doan}} "
        f"| {'Kết quả':<{cot_trang_thai}} "
        f"| {'Lý do':<{cot_ly_do}} |"
    )
    print(duong_ke)

    tong_nap = 0
    tong_bo_qua = 0
    tong_tu_choi = 0

    for kq in danh_sach_kq:
        ten_rut_gon = kq.ten_tep if len(kq.ten_tep) <= cot_tep else kq.ten_tep[:cot_tep - 3] + "..."
        ly_do_hien_thi = kq.ly_do or "-"
        if len(ly_do_hien_thi) > cot_ly_do:
            ly_do_hien_thi = ly_do_hien_thi[:cot_ly_do - 3] + "..."

        print(
            f"| {ten_rut_gon:<{cot_tep}} "
            f"| {kq.so_doan:<{cot_doan}} "
            f"| {kq.trang_thai:<{cot_trang_thai}} "
            f"| {ly_do_hien_thi:<{cot_ly_do}} |"
        )

        if kq.trang_thai == "ĐÃ NẠP":
            tong_nap += 1
        elif kq.trang_thai == "BỎ QUA":
            tong_bo_qua += 1
        elif kq.trang_thai == "TỪ CHỐI":
            tong_tu_choi += 1

    print(duong_ke)
    print(
        f"Tổng cộng: {len(danh_sach_kq)} tệp | "
        f"ĐÃ NẠP: {tong_nap} | BỎ QUA: {tong_bo_qua} | TỪ CHỐI: {tong_tu_choi}\n"
    )


async def xu_ly_nap_duong_dan(duong_dan_nhap: str) -> None:
    """Quét và nạp toàn bộ tệp tài liệu trong thư mục hoặc tệp đơn lẻ."""
    duong_dan = Path(duong_dan_nhap)
    if not duong_dan.exists():
        print(f"Lỗi: Không tìm thấy đường dẫn '{duong_dan_nhap}'", file=sys.stderr)
        sys.exit(1)

    danh_sach_tep: list[Path] = []
    if duong_dan.is_file():
        if not duong_dan.name.endswith(".meta.yaml"):
            danh_sach_tep.append(duong_dan)
    else:
        # Bỏ qua tệp siêu dữ liệu *.meta.yaml
        for p in sorted(duong_dan.iterdir()):
            if p.is_file() and not p.name.endswith(".meta.yaml"):
                danh_sach_tep.append(p)

    if not danh_sach_tep:
        print(f"Không có tài liệu nào cần xử lý trong '{duong_dan_nhap}'.")
        return

    print(f"Bắt đầu xử lý {len(danh_sach_tep)} tài liệu từ: {duong_dan}...")
    ket_qua_list: list[KetQuaNap] = []

    for t in danh_sach_tep:
        sys.stdout.write(f"Đang xử lý: {t.name}...\r")
        sys.stdout.flush()
        kq = await nap_mot_tai_lieu(t)
        ket_qua_list.append(kq)

    sys.stdout.write(" " * 80 + "\r")
    in_bang_ket_qua(ket_qua_list)


async def xu_ly_het_hieu_luc(ma_tai_lieu: str, van_ban_thay_the: str) -> None:
    """Xử lý cập nhật trạng thái hết hiệu lực cho tài liệu."""
    print(f"Cập nhật tài liệu '{ma_tai_lieu}' sang trạng thái 'het_hieu_luc'...")
    thanh_cong = await cap_nhat_het_hieu_luc(ma_tai_lieu, van_ban_thay_the)
    if thanh_cong:
        print(
            f"Thành công: Đã đánh dấu '{ma_tai_lieu}' hết hiệu lực, "
            f"thay thế bằng '{van_ban_thay_the}'."
        )
    else:
        print(f"Lỗi: Không tìm thấy tài liệu có mã '{ma_tai_lieu}'.", file=sys.stderr)
        sys.exit(1)


async def main_async() -> None:
    """Điểm vào bất đồng bộ chính cho kịch bản dòng lệnh."""
    parser = argparse.ArgumentParser(description="Công cụ nạp và quản lý tài liệu RAG.")
    parser.add_argument("duong_dan", nargs="?", help="Đường dẫn tới tệp hoặc thư mục tài liệu.")
    parser.add_argument("--het-hieu-luc", help="Mã tài liệu cần đánh dấu hết hiệu lực.")
    parser.add_argument("--thay-the", help="Mã tài liệu thay thế (bắt buộc khi dùng --het-hieu-luc).")
    parser.add_argument(
        "--nhung-lai",
        action="store_true",
        help="Đặt lại toàn bộ vector hiện có và nạp lại vector nhúng cho toàn bộ kho tài liệu.",
    )

    args = parser.parse_args()

    if args.het_hieu_luc:
        ma_hhl = args.het_hieu_luc
        ma_tt = args.thay_the
        if not ma_tt:
            print("Lỗi: Bắt buộc truyền --thay-the <ma_moi> khi sử dụng --het-hieu-luc", file=sys.stderr)
            sys.exit(1)
        await xu_ly_het_hieu_luc(ma_hhl, ma_tt)
        return

    if not args.duong_dan and not args.nhung_lai:
        parser.print_help()
        sys.exit(1)

    if args.duong_dan:
        await xu_ly_nap_duong_dan(args.duong_dan)

    if args.nhung_lai:
        print("\nĐặt lại toàn bộ vector nhúng hiện có trong cơ sở dữ liệu...")
        so_dat_lai = await dat_lai_tat_ca_vector()
        print(f"Đã đặt lại vector của {so_dat_lai} đoạn về NULL.")

    print("\nBắt đầu tạo vector nhúng cho các đoạn tài liệu chưa có vector...")
    so_doan_nhung = await nhung_doan_chua_co_vector(tien_do=True)
    if so_doan_nhung > 0:
        print(f"Hoàn thành: Đã tạo vector nhúng thành công cho {so_doan_nhung} đoạn.")
    else:
        print("Tất cả các đoạn tài liệu đều đã có vector nhúng, không cần xử lý thêm.")


def main() -> None:
    """Điểm khởi chạy đồng bộ."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
