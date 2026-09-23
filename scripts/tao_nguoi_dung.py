"""Kịch bản tạo tài khoản người dùng mới trong hệ thống.

Sử dụng:
    python scripts/tao_nguoi_dung.py --email nv01@vidu.com --ho-ten "Nguyễn Văn A" --vai-tro nguoi_dung --phong-ban KINH_DOANH
"""

import argparse
import asyncio
import os
import re
import secrets
import string
import sys
from pathlib import Path

# Đảm bảo đường dẫn module backend được nạp khi chạy từ thư mục bất kỳ
THU_MUC_GOC = Path(__file__).resolve().parents[1]
DUONG_DAN_BACKEND = THU_MUC_GOC / "backend"
if str(DUONG_DAN_BACKEND) not in sys.path:
    sys.path.insert(0, str(DUONG_DAN_BACKEND))
if "/srv/backend" not in sys.path and os.path.exists("/srv/backend"):
    sys.path.insert(0, "/srv/backend")

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.csdl import NguoiDungModel, lay_sessionmaker_async

BIEU_THUC_EMAIL = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
VAI_TRO_HOP_LE = {"quan_tri", "nguoi_dung", "chi_doc"}
PHONG_BAN_HOP_LE = {"KINH_DOANH", "KY_THUAT_AN_TOAN", "CHAM_SOC_KHACH_HANG", "CNTT"}

_bo_bam_mat_khau = CryptContext(schemes=["bcrypt"], deprecated="auto")


def sinh_mat_khau_ngau_nhien(do_dai: int = 12) -> str:
    """Sinh chuỗi mật khẩu ngẫu nhiên an toàn gồm chữ hoa, chữ thường và chữ số."""
    ky_tu = string.ascii_letters + string.digits + "@#$%"
    return "".join(secrets.choice(ky_tu) for _ in range(do_dai))


async def tao_nguoi_dung(
    email_tho: str,
    ho_ten: str,
    vai_tro: str,
    phong_ban: str,
    mat_khau_tu_chon: str | None = None,
) -> str:
    """Tạo người dùng mới, lưu vào CSDL và trả về mật khẩu khởi tạo."""
    email = email_tho.strip().lower()

    if not BIEU_THUC_EMAIL.match(email):
        raise ValueError(f"Email không đúng định dạng: {email_tho}")

    if vai_tro not in VAI_TRO_HOP_LE:
        danh_sach = ", ".join(sorted(VAI_TRO_HOP_LE))
        raise ValueError(f"Vai trò không hợp lệ: '{vai_tro}'. Phải là một trong: {danh_sach}")

    if phong_ban not in PHONG_BAN_HOP_LE:
        danh_sach = ", ".join(sorted(PHONG_BAN_HOP_LE))
        raise ValueError(f"Phòng ban không hợp lệ: '{phong_ban}'. Phải là một trong: {danh_sach}")

    mat_khau = mat_khau_tu_chon if mat_khau_tu_chon else sinh_mat_khau_ngau_nhien()
    mat_khau_bam = _bo_bam_mat_khau.hash(mat_khau)

    maker = lay_sessionmaker_async()
    async with maker() as phien, phien.begin():
        cau_lenh = select(NguoiDungModel).where(NguoiDungModel.email == email)
        da_co = (await phien.scalars(cau_lenh)).first()
        if da_co is not None:
            raise ValueError(f"Email đã tồn tại trong hệ thống: {email}")

        nguoi_moi = NguoiDungModel(
            email=email,
            mat_khau_bam=mat_khau_bam,
            ho_ten=ho_ten.strip(),
            vai_tro=vai_tro,
            bac="free",
            phong_ban=phong_ban,
            dang_hoat_dong=True,
        )
        phien.add(nguoi_moi)

    return mat_khau


def main() -> None:
    """Hàm nhập chính xử lý tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description="Tạo người dùng mới cho Trợ lý AI Nội bộ.")
    parser.add_argument("--email", required=True, help="Địa chỉ email đăng nhập")
    parser.add_argument("--ho-ten", required=True, help="Họ và tên cán bộ công nhân viên")
    parser.add_argument(
        "--vai-tro",
        default="nguoi_dung",
        choices=["quan_tri", "nguoi_dung", "chi_doc"],
        help="Vai trò người dùng (mặc định: nguoi_dung)",
    )
    parser.add_argument(
        "--phong-ban",
        default="CNTT",
        choices=["KINH_DOANH", "KY_THUAT_AN_TOAN", "CHAM_SOC_KHACH_HANG", "CNTT"],
        help="Phòng ban trực thuộc (mặc định: CNTT)",
    )
    parser.add_argument(
        "--mat-khau",
        default=None,
        help="Mật khẩu tùy chọn (nếu không cung cấp, hệ thống tự sinh ngẫu nhiên)",
    )

    args = parser.parse_args()

    try:
        mat_khau = asyncio.run(
            tao_nguoi_dung(
                email_tho=args.email,
                ho_ten=args.ho_ten,
                vai_tro=args.vai_tro,
                phong_ban=args.phong_ban,
                mat_khau_tu_chon=args.mat_khau,
            )
        )
        print(f"Tạo người dùng thành công: {args.email.strip().lower()}")
        print(f"Mật khẩu khởi tạo: {mat_khau}")
    except ValueError as err:
        print(f"LỖI: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:  # noqa: BLE001
        print(f"LỖI HỆ THỐNG: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
