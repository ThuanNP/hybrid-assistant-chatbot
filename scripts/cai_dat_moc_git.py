"""Kịch bản cài móc pre-commit chặn commit chứa bí mật.

Móc chạy `gitleaks git --staged` trên vùng staged trước mỗi lần commit và huỷ commit khi
phát hiện bí mật. Móc nằm trong `.git/hooks/` nên chỉ có hiệu lực trên máy cục bộ; mỗi
thành viên phải tự chạy kịch bản này sau khi clone kho mã.

Hướng dẫn đầy đủ: .agents/skills/secrets-gitleaks/SKILL.md
"""

import argparse
import io
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# Cấu hình encoding utf-8 để in tiếng Việt chính xác trên Windows / Git Bash
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

THU_MUC_GOC = Path(__file__).resolve().parents[1]

# Móc viết bằng sh để chạy được trên Git Bash (Windows), Linux và macOS.
NOI_DUNG_MOC = """#!/bin/sh
# Móc pre-commit chặn bí mật, cài bởi scripts/cai_dat_moc_git.py
# Bỏ qua tạm thời (chỉ khi thật cần và phải ghi rõ lý do trong mô tả commit):
#   git commit --no-verify

if ! command -v gitleaks >/dev/null 2>&1; then
    echo "pre-commit: khong tim thay lenh 'gitleaks', bo qua buoc quet bi mat." >&2
    echo "pre-commit: cai dat bang 'winget install gitleaks' hoac 'brew install gitleaks'." >&2
    exit 0
fi

gitleaks git --staged --redact --no-banner
ma_thoat=$?

if [ $ma_thoat -ne 0 ]; then
    echo "" >&2
    echo "pre-commit: DA CHAN COMMIT vi phat hien bi mat trong vung staged." >&2
    echo "pre-commit: thu hoi va xoay vong khoa, chuyen gia tri sang .env, roi commit lai." >&2
    echo "pre-commit: xem .agents/skills/secrets-gitleaks/SKILL.md" >&2
    exit 1
fi

exit 0
"""


def lay_thu_muc_moc() -> Path:
    """Xác định thư mục chứa móc git, hỗ trợ cả worktree và submodule."""
    try:
        ket_qua = subprocess.run(
            ["git", "-C", str(THU_MUC_GOC), "rev-parse", "--git-path", "hooks"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as loi:
        print(f"LỖI: Không xác định được thư mục móc git: {loi}")
        sys.exit(2)

    duong_dan = Path(ket_qua.stdout.strip())
    if not duong_dan.is_absolute():
        duong_dan = THU_MUC_GOC / duong_dan
    return duong_dan


def canh_bao_thieu_gitleaks() -> None:
    """In hướng dẫn cài đặt nếu chưa có gitleaks trong PATH."""
    if shutil.which("gitleaks") is not None:
        return
    print("CẢNH BÁO: Chưa cài 'gitleaks'. Móc vẫn được cài nhưng sẽ bỏ qua bước quét.")
    print("Cài đặt trên Windows: winget install gitleaks")
    print("Cài đặt trên macOS:   brew install gitleaks")


def sao_luu_moc_cu(tep_moc: Path, ghi_de: bool) -> None:
    """Sao lưu móc pre-commit sẵn có, thoát sớm nếu người dùng chưa cho phép ghi đè."""
    if not tep_moc.exists():
        return
    if NOI_DUNG_MOC.strip() in tep_moc.read_text(encoding="utf-8", errors="replace"):
        print(f"Móc đã được cài sẵn và không thay đổi: {tep_moc}")
        return
    if not ghi_de:
        print(f"LỖI: Đã tồn tại móc pre-commit khác tại {tep_moc}.")
        print("Chạy lại với cờ --ghi-de để sao lưu móc cũ và cài đè.")
        sys.exit(1)

    tep_sao_luu = tep_moc.with_suffix(".sao-luu")
    shutil.copy2(tep_moc, tep_sao_luu)
    print(f"Đã sao lưu móc cũ vào: {tep_sao_luu}")


def ghi_moc(tep_moc: Path) -> None:
    """Ghi nội dung móc và cấp quyền thực thi."""
    tep_moc.parent.mkdir(parents=True, exist_ok=True)
    # Ghi newline="\n" vì sh trên Git Bash không chạy được tệp có kết thúc dòng CRLF.
    tep_moc.write_text(NOI_DUNG_MOC, encoding="utf-8", newline="\n")
    quyen_hien_tai = tep_moc.stat().st_mode
    tep_moc.chmod(quyen_hien_tai | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Đã cài móc pre-commit tại: {tep_moc}")


def doc_tham_so() -> argparse.Namespace:
    """Khai báo và đọc tham số dòng lệnh."""
    bo_doc = argparse.ArgumentParser(description="Cài móc pre-commit quét bí mật bằng Gitleaks.")
    bo_doc.add_argument(
        "--ghi-de",
        action="store_true",
        help="Sao lưu và ghi đè móc pre-commit sẵn có.",
    )
    bo_doc.add_argument(
        "--go-bo",
        action="store_true",
        help="Gỡ móc pre-commit do kịch bản này cài đặt.",
    )
    return bo_doc.parse_args()


def go_bo_moc(tep_moc: Path) -> int:
    """Gỡ móc pre-commit nếu đúng là móc do kịch bản này cài."""
    if not tep_moc.exists():
        print("Không có móc pre-commit nào để gỡ.")
        return 0
    if "cai_dat_moc_git.py" not in tep_moc.read_text(encoding="utf-8", errors="replace"):
        print(f"LỖI: {tep_moc} không phải móc do kịch bản này cài, không tự động gỡ.")
        return 1
    tep_moc.unlink()
    print(f"Đã gỡ móc pre-commit: {tep_moc}")
    return 0


def chay_cai_dat() -> int:
    """Điều phối quy trình cài đặt hoặc gỡ bỏ móc."""
    tham_so = doc_tham_so()
    tep_moc = lay_thu_muc_moc() / "pre-commit"

    if tham_so.go_bo:
        return go_bo_moc(tep_moc)

    canh_bao_thieu_gitleaks()
    sao_luu_moc_cu(tep_moc, tham_so.ghi_de)
    ghi_moc(tep_moc)
    print("\nKiểm tra nhanh: thêm một tệp chứa khoá giả vào vùng staged rồi thử commit.")
    return 0


if __name__ == "__main__":
    sys.exit(chay_cai_dat())
