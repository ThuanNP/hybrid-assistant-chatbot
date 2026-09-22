"""Kịch bản quét bí mật bị ghim cứng trong mã nguồn và lịch sử git bằng Gitleaks.

Phục vụ quy tắc tuyệt đối 4 trong AGENTS.md. Kịch bản phân loại phát hiện thành hai mức:

- NGHIEM_TRONG: tệp được git theo dõi, bí mật đã hoặc sắp lọt vào kho mã.
- CUC_BO: tệp đã nằm trong .gitignore (ví dụ .env), bí mật chỉ tồn tại trên máy.

Chỉ mức NGHIEM_TRONG làm kịch bản trả mã thoát khác 0.

Hướng dẫn đầy đủ: .agents/skills/secrets-gitleaks/SKILL.md
"""

import argparse
import io
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Cấu hình encoding utf-8 để in tiếng Việt chính xác trên Windows / Git Bash
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

THU_MUC_GOC = Path(__file__).resolve().parents[1]

MUC_NGHIEM_TRONG = "NGHIEM_TRONG"
MUC_CUC_BO = "CUC_BO"


@dataclass
class PhatHien:
    """Một phát hiện bí mật do Gitleaks báo cáo, đã được che giá trị."""

    duong_dan: str
    dong: int
    luat: str
    mo_ta: str
    commit: str
    muc_do: str


def kiem_tra_gitleaks() -> str:
    """Xác định đường dẫn tệp thực thi gitleaks, thoát sớm nếu chưa cài đặt."""
    duong_dan = shutil.which("gitleaks")
    if duong_dan is None:
        print("LỖI: Không tìm thấy lệnh 'gitleaks' trong PATH.")
        print("Cài đặt trên Windows: winget install gitleaks")
        print("Cài đặt trên macOS:   brew install gitleaks")
        sys.exit(2)
    return duong_dan


def _lenh_gitleaks(duong_dan_gitleaks: str, pham_vi: str, tep_bao_cao: Path) -> list[str]:
    """Dựng câu lệnh Gitleaks cho một phạm vi quét.

    Dùng --exit-code 0 để mã thoát khác 0 chỉ còn mang nghĩa lỗi thực thi, còn việc
    có rò rỉ hay không được quyết định bằng nội dung tệp báo cáo JSON.

    Đích quét là "." kèm cwd đặt tại thư mục gốc: truyền đường dẫn tuyệt đối sẽ làm
    Gitleaks báo cáo đường dẫn tuyệt đối, khiến danh sách loại trừ trong .gitleaks.toml
    và lệnh `git check-ignore` đều không khớp được.
    """
    return [
        duong_dan_gitleaks,
        pham_vi,
        ".",
        "--redact",
        "--no-banner",
        "--exit-code",
        "0",
        "--report-format",
        "json",
        "--report-path",
        str(tep_bao_cao),
    ]


def chay_mot_pham_vi(duong_dan_gitleaks: str, pham_vi: str) -> list[dict[str, object]]:
    """Chạy Gitleaks cho một phạm vi ('git' hoặc 'dir') và trả về danh sách phát hiện thô."""
    with tempfile.TemporaryDirectory() as thu_muc_tam:
        tep_bao_cao = Path(thu_muc_tam) / "gitleaks.json"
        lenh = _lenh_gitleaks(duong_dan_gitleaks, pham_vi, tep_bao_cao)
        try:
            ket_qua = subprocess.run(
                lenh,
                cwd=str(THU_MUC_GOC),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError as loi:
            print(f"LỖI: Không thể khởi chạy gitleaks: {loi}")
            sys.exit(2)

        if not tep_bao_cao.exists():
            print(f"LỖI: Gitleaks không tạo được báo cáo cho phạm vi '{pham_vi}'.")
            print(ket_qua.stderr.strip())
            sys.exit(2)

        noi_dung = tep_bao_cao.read_text(encoding="utf-8").strip()

    if not noi_dung:
        return []
    return json.loads(noi_dung)


def chuan_hoa_duong_dan(gia_tri: object) -> str:
    """Đưa đường dẫn về dạng dấu gạch chéo xuôi, bỏ tiền tố './' để so khớp nhất quán."""
    duong_dan = str(gia_tri).replace("\\", "/")
    return duong_dan.removeprefix("./")


def doc_so_nguyen(gia_tri: object) -> int:
    """Đọc số nguyên từ trường JSON chưa xác định kiểu, trả 0 nếu không đọc được."""
    if isinstance(gia_tri, int):
        return gia_tri
    if isinstance(gia_tri, str) and gia_tri.isdigit():
        return int(gia_tri)
    return 0


def rut_gon_duong_dan(duong_dan: str, do_rong: int) -> str:
    """Rút gọn đường dẫn quá dài bằng cách giữ phần đuôi, vì tên tệp nằm ở cuối."""
    if len(duong_dan) <= do_rong:
        return duong_dan
    return "..." + duong_dan[-(do_rong - 3) :]


def lay_tep_bi_bo_qua(cac_duong_dan: set[str]) -> set[str]:
    """Hỏi git xem những đường dẫn nào nằm trong .gitignore."""
    if not cac_duong_dan:
        return set()
    ket_qua = subprocess.run(
        ["git", "-C", str(THU_MUC_GOC), "check-ignore", "--stdin"],
        input="\n".join(sorted(cac_duong_dan)),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return {dong.strip().replace("\\", "/") for dong in ket_qua.stdout.splitlines() if dong.strip()}


def chuan_hoa_phat_hien(
    cac_ban_ghi: list[dict[str, object]],
    cac_tep_bi_bo_qua: set[str],
) -> list[PhatHien]:
    """Chuyển bản ghi JSON của Gitleaks thành danh sách PhatHien kèm mức độ."""
    danh_sach: list[PhatHien] = []
    for ban_ghi in cac_ban_ghi:
        duong_dan = chuan_hoa_duong_dan(ban_ghi.get("File", ""))
        muc_do = MUC_CUC_BO if duong_dan in cac_tep_bi_bo_qua else MUC_NGHIEM_TRONG
        danh_sach.append(
            PhatHien(
                duong_dan=duong_dan,
                dong=doc_so_nguyen(ban_ghi.get("StartLine")),
                luat=str(ban_ghi.get("RuleID", "")),
                mo_ta=str(ban_ghi.get("Description", "")),
                commit=str(ban_ghi.get("Commit", ""))[:8],
                muc_do=muc_do,
            )
        )
    return danh_sach


def gom_phat_hien(duong_dan_gitleaks: str, pham_vi: str) -> list[PhatHien]:
    """Chạy các phạm vi được yêu cầu, khử trùng lặp và gán mức độ cho từng phát hiện."""
    cac_pham_vi = ["git", "dir"] if pham_vi == "ca-hai" else [pham_vi]
    cac_ban_ghi: list[dict[str, object]] = []
    for mot_pham_vi in cac_pham_vi:
        print(f"Đang quét phạm vi '{mot_pham_vi}' ...")
        cac_ban_ghi.extend(chay_mot_pham_vi(duong_dan_gitleaks, mot_pham_vi))

    cac_duong_dan = {chuan_hoa_duong_dan(bg.get("File", "")) for bg in cac_ban_ghi}
    cac_tep_bi_bo_qua = lay_tep_bi_bo_qua(cac_duong_dan)
    tat_ca = chuan_hoa_phat_hien(cac_ban_ghi, cac_tep_bi_bo_qua)

    da_thay: set[tuple[str, int, str, str]] = set()
    ket_qua: list[PhatHien] = []
    for ph in tat_ca:
        khoa = (ph.duong_dan, ph.dong, ph.luat, ph.commit)
        if khoa in da_thay:
            continue
        da_thay.add(khoa)
        ket_qua.append(ph)
    return ket_qua


def in_bang(cac_phat_hien: list[PhatHien]) -> None:
    """In bảng kết quả ra màn hình, nhóm theo mức độ."""
    if not cac_phat_hien:
        print("\nKẾT QUẢ: Không phát hiện bí mật nào.")
        return

    for muc_do, tieu_de in ((MUC_NGHIEM_TRONG, "NGHIÊM TRỌNG"), (MUC_CUC_BO, "CỤC BỘ")):
        nhom = [ph for ph in cac_phat_hien if ph.muc_do == muc_do]
        if not nhom:
            continue
        print(f"\n=== {tieu_de} ({len(nhom)} phát hiện) ===")
        print(f"{'Tệp':<56} | {'Dòng':>5} | {'Luật':<24} | {'Commit':<8}")
        print("-" * 104)
        for ph in nhom:
            ten = rut_gon_duong_dan(ph.duong_dan, 56)
            print(f"{ten:<56} | {ph.dong:>5} | {ph.luat[:24]:<24} | {ph.commit:<8}")


def _dong_markdown(ph: PhatHien) -> str:
    """Dựng một dòng bảng Markdown cho phát hiện."""
    commit = ph.commit if ph.commit else "-"
    return f"| `{ph.duong_dan}` | {ph.dong} | `{ph.luat}` | {commit} | {ph.mo_ta} |"


def dung_bao_cao_markdown(cac_phat_hien: list[PhatHien]) -> str:
    """Dựng báo cáo Markdown. Giá trị bí mật đã bị Gitleaks che, không đưa vào báo cáo."""
    thoi_diem = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    so_nghiem_trong = sum(1 for ph in cac_phat_hien if ph.muc_do == MUC_NGHIEM_TRONG)
    so_cuc_bo = len(cac_phat_hien) - so_nghiem_trong

    cac_dong = [
        "# Báo cáo quét bí mật",
        "",
        f"- Thời điểm quét: {thoi_diem}",
        f"- Phát hiện nghiêm trọng (tệp được git theo dõi): {so_nghiem_trong}",
        f"- Phát hiện cục bộ (tệp đã nằm trong .gitignore): {so_cuc_bo}",
        "",
        "Báo cáo này là tài liệu mật, lưu trong `secret/`, không commit vào kho mã.",
        "",
    ]

    for muc_do, tieu_de in ((MUC_NGHIEM_TRONG, "Nghiêm trọng"), (MUC_CUC_BO, "Cục bộ")):
        nhom = [ph for ph in cac_phat_hien if ph.muc_do == muc_do]
        if not nhom:
            continue
        cac_dong.append(f"## {tieu_de}")
        cac_dong.append("")
        cac_dong.append("| Tệp | Dòng | Luật | Commit | Mô tả |")
        cac_dong.append("| :--- | ---: | :--- | :--- | :--- |")
        cac_dong.extend(_dong_markdown(ph) for ph in nhom)
        cac_dong.append("")

    if not cac_phat_hien:
        cac_dong.append("Không phát hiện bí mật nào.")
        cac_dong.append("")
    return "\n".join(cac_dong)


def ghi_ket_qua(cac_phat_hien: list[PhatHien], dinh_dang: str, dau_ra: str | None) -> None:
    """Xuất kết quả theo định dạng được chọn."""
    if dinh_dang == "bang":
        in_bang(cac_phat_hien)
        return

    if dinh_dang == "json":
        noi_dung = json.dumps([ph.__dict__ for ph in cac_phat_hien], ensure_ascii=False, indent=2)
    else:
        noi_dung = dung_bao_cao_markdown(cac_phat_hien)

    if dau_ra is None:
        print(noi_dung)
        return

    tep_dau_ra = Path(dau_ra)
    tep_dau_ra.parent.mkdir(parents=True, exist_ok=True)
    tep_dau_ra.write_text(noi_dung, encoding="utf-8")
    print(f"Đã ghi báo cáo vào: {tep_dau_ra}")


def doc_tham_so() -> argparse.Namespace:
    """Khai báo và đọc tham số dòng lệnh."""
    bo_doc = argparse.ArgumentParser(description="Quét bí mật bị ghim cứng bằng Gitleaks.")
    bo_doc.add_argument(
        "--pham-vi",
        choices=["git", "dir", "ca-hai"],
        default="ca-hai",
        help="Phạm vi quét: lịch sử git, cây làm việc, hoặc cả hai (mặc định).",
    )
    bo_doc.add_argument(
        "--dinh-dang",
        choices=["bang", "json", "markdown"],
        default="bang",
        help="Định dạng kết quả (mặc định: bang).",
    )
    bo_doc.add_argument(
        "--dau-ra",
        default=None,
        help="Đường dẫn tệp xuất báo cáo. Bỏ trống thì in ra màn hình.",
    )
    return bo_doc.parse_args()


def chay_quet() -> int:
    """Điều phối toàn bộ quy trình quét và trả về mã thoát."""
    tham_so = doc_tham_so()
    duong_dan_gitleaks = kiem_tra_gitleaks()
    cac_phat_hien = gom_phat_hien(duong_dan_gitleaks, tham_so.pham_vi)
    ghi_ket_qua(cac_phat_hien, tham_so.dinh_dang, tham_so.dau_ra)

    so_nghiem_trong = sum(1 for ph in cac_phat_hien if ph.muc_do == MUC_NGHIEM_TRONG)
    if so_nghiem_trong > 0:
        print(f"\nTHẤT BẠI: {so_nghiem_trong} bí mật nằm trong tệp được git theo dõi.")
        print("Thu hồi và xoay vòng khoá ngay, sau đó xem references/remediation-guide.md.")
        return 1

    so_cuc_bo = len(cac_phat_hien) - so_nghiem_trong
    if so_cuc_bo > 0:
        print(f"\nĐẠT: Không có bí mật trong kho mã ({so_cuc_bo} phát hiện ở tệp đã .gitignore).")
    return 0


if __name__ == "__main__":
    sys.exit(chay_quet())
