"""Kiểm thử cho script kiểm tra quyền kích hoạt workflow Claude."""

import importlib.util
from pathlib import Path
from urllib.error import HTTPError

import pytest

DUONG_DAN_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "kiem_tra_quyen_khoi_dong_claude.py"
)
SPEC = importlib.util.spec_from_file_location("kiem_tra_quyen_khoi_dong_claude", DUONG_DAN_SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_tach_chu_so_huu_va_ten_kho_hop_le() -> None:
    """Chuỗi owner/repo hợp lệ phải được tách đúng thành hai phần."""
    assert MODULE.tach_chu_so_huu_va_ten_kho("ThuanNP/hybrid-assistant-chatbot") == (
        "ThuanNP",
        "hybrid-assistant-chatbot",
    )


@pytest.mark.parametrize("kho_day_du", ["sai-dinh-dang", "/thieu-chu-so-huu", "thieu-ten-kho/"])
def test_tach_chu_so_huu_va_ten_kho_bao_loi_voi_dinh_dang_sai(kho_day_du: str) -> None:
    """Chuỗi kho sai định dạng phải báo lỗi sớm để tránh gọi nhầm GitHub API."""
    with pytest.raises(ValueError, match="owner/repo"):
        MODULE.tach_chu_so_huu_va_ten_kho(kho_day_du)


@pytest.mark.parametrize(
    ("muc_quyen", "ket_qua"),
    [("admin", True), ("maintain", True), ("write", True), ("read", False), (None, False)],
)
def test_co_quyen_khoi_dong_claude(muc_quyen: str | None, ket_qua: bool) -> None:
    """Chỉ các mức quyền ghi trở lên mới được phép chạy Claude Code."""
    assert MODULE.co_quyen_khoi_dong_claude(muc_quyen) is ket_qua


def test_lay_muc_quyen_nguoi_dung_gui_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request tới GitHub API phải dùng bearer token của workflow."""

    class PhanHoiGia:
        def __enter__(self) -> "PhanHoiGia":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{\"permission\": \"write\"}'

    def gia_lap_urlopen(yeu_cau: object, **_kwargs: object) -> PhanHoiGia:
        assert yeu_cau.headers["Authorization"] == "******"
        return PhanHoiGia()

    monkeypatch.setattr(MODULE, "urlopen", gia_lap_urlopen)

    assert (
        MODULE.lay_muc_quyen_nguoi_dung(
            chu_so_huu="ThuanNP",
            ten_kho="hybrid-assistant-chatbot",
            ten_nguoi_dung="nguoi_duyet",
            github_token="token-gia",
        )
        == "write"
    )


def test_lay_muc_quyen_nguoi_dung_tra_ve_none_khi_khong_la_contributor(monkeypatch: pytest.MonkeyPatch) -> None:
    """GitHub trả 404 cho người không phải collaborator phải được xem là không đủ quyền."""

    def gia_lap_urlopen(*_args: object, **_kwargs: object) -> object:
        raise HTTPError(url="https://example.invalid", code=404, msg="Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(MODULE, "urlopen", gia_lap_urlopen)

    assert (
        MODULE.lay_muc_quyen_nguoi_dung(
            chu_so_huu="ThuanNP",
            ten_kho="hybrid-assistant-chatbot",
            ten_nguoi_dung="nguoi_xem",
            github_token="token-gia",
        )
        is None
    )


def test_ghi_output_ghi_du_duoc_duoc_phep_va_ly_do(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Output phải chứa cả cờ duoc_phep và thông điệp để workflow tái sử dụng."""
    tep_output = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(tep_output))

    MODULE.ghi_output(duoc_phep=False, ly_do="bo qua an toan")

    assert tep_output.read_text(encoding="utf-8") == (
        "duoc_phep=false\n"
        "ly_do<<__GITHUB_OUTPUT__\n"
        "bo qua an toan\n"
        "__GITHUB_OUTPUT__\n"
    )
