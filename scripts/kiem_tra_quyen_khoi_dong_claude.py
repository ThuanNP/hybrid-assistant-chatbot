"""Kiểm tra người kích hoạt workflow Claude có quyền ghi trên kho mã hay không."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

QUYEN_DUOC_PHEP = frozenset({"admin", "maintain", "write"})


def tach_chu_so_huu_va_ten_kho(kho_day_du: str) -> tuple[str, str]:
    """Tách chuỗi owner/repo và báo lỗi sớm nếu định dạng không hợp lệ."""
    chu_so_huu, dau_gach, ten_kho = kho_day_du.partition("/")
    if not dau_gach or not chu_so_huu or not ten_kho:
        raise ValueError("GITHUB_REPOSITORY phải có định dạng owner/repo.")
    return chu_so_huu, ten_kho


def doc_muc_quyen(du_lieu: object) -> str | None:
    """Đọc mức quyền từ JSON phản hồi của GitHub API."""
    if not isinstance(du_lieu, dict):
        return None
    muc_quyen = du_lieu.get("permission")
    if not isinstance(muc_quyen, str):
        return None
    return muc_quyen


def co_quyen_khoi_dong_claude(muc_quyen: str | None) -> bool:
    """Chỉ cho phép Claude chạy khi người kích hoạt có quyền ghi trở lên."""
    return muc_quyen in QUYEN_DUOC_PHEP


def lay_muc_quyen_nguoi_dung(
    chu_so_huu: str,
    ten_kho: str,
    ten_nguoi_dung: str,
    github_token: str,
) -> str | None:
    """Truy vấn GitHub API để lấy mức quyền của người dùng trong kho mã."""
    duong_dan = (
        "https://api.github.com/repos/"
        f"{quote(chu_so_huu)}/{quote(ten_kho)}/collaborators/{quote(ten_nguoi_dung)}/permission"
    )
    yeu_cau = Request(
        duong_dan,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + github_token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "hybrid-assistant-chatbot-claude-workflow",
        },
    )
    try:
        with urlopen(yeu_cau, timeout=10.0) as phan_hoi:
            du_lieu = json.load(phan_hoi)
    except HTTPError as loi:
        if loi.code == 404:
            return None
        raise
    return doc_muc_quyen(du_lieu)


def ghi_output(duoc_phep: bool, ly_do: str) -> None:
    """Ghi output cho GitHub Actions để các bước sau dùng lại."""
    duong_dan_output = os.environ.get("GITHUB_OUTPUT")
    if not duong_dan_output:
        return
    noi_dung = "true" if duoc_phep else "false"
    with Path(duong_dan_output).open("a", encoding="utf-8") as tep_output:
        tep_output.write(f"duoc_phep={noi_dung}\n")
        tep_output.write("ly_do<<__GITHUB_OUTPUT__\n")
        tep_output.write(f"{ly_do}\n")
        tep_output.write("__GITHUB_OUTPUT__\n")


def main() -> int:
    """Thoát 0 khi người kích hoạt được phép hoặc bị bỏ qua an toàn."""
    kho_day_du = os.environ["GITHUB_REPOSITORY"]
    ten_nguoi_dung = os.environ["GITHUB_ACTOR"]
    github_token = os.environ["GITHUB_TOKEN"]

    chu_so_huu, ten_kho = tach_chu_so_huu_va_ten_kho(kho_day_du)
    muc_quyen = lay_muc_quyen_nguoi_dung(chu_so_huu, ten_kho, ten_nguoi_dung, github_token)

    if co_quyen_khoi_dong_claude(muc_quyen):
        thong_bao = (
            f"Nguoi kich hoat '{ten_nguoi_dung}' co quyen '{muc_quyen}', "
            "cho phep chay Claude Code."
        )
        print(thong_bao)
        ghi_output(duoc_phep=True, ly_do=thong_bao)
        return 0

    thong_bao = (
        f"Nguoi kich hoat '{ten_nguoi_dung}' khong co quyen ghi tren kho "
        f"({muc_quyen or 'khong xac dinh'}), bo qua Claude Code an toan."
    )
    print(thong_bao)
    ghi_output(duoc_phep=False, ly_do=thong_bao)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
