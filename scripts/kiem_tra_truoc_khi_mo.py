"""Danh mục kiểm tra trước khi mở hệ thống cho người dùng (Phụ lục 4).

Chạy từ backend/: uv run --frozen python ../scripts/kiem_tra_truoc_khi_mo.py

Đánh số đúng theo Phụ lục 4. Mỗi dòng "Máy" dùng lại kiểm thử hoặc kịch bản chẩn đoán đã có
của prompt tạo ra tính năng; dòng "Người" in CHỜ XÁC NHẬN và không tính vào mã thoát.
Giai đoạn 5 cài các dòng Máy 1-16, 19, 25; dòng 17, 18 (Giai đoạn 6) và 20 (Giai đoạn 7)
do các giai đoạn đó bổ sung.

Kịch bản không gọi thẳng bộ chạy hay litellm (quy tắc tuyệt đối 1): phần cần bộ chạy
đi qua scripts/kiem_tra_bo_chay.py, scripts/kiem_tra_phoi_lo.py hoặc mô-đun của ứng dụng.

Mã thoát: 0 khi mọi dòng Máy đang áp dụng đều ĐẠT, 1 khi có dòng CHƯA ĐẠT.
"""

import asyncio
import io
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# In tiếng Việt đúng trên Windows / Git Bash
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

THU_MUC_GOC = Path(__file__).resolve().parents[1]
THU_MUC_BACKEND = THU_MUC_GOC / "backend"
THU_MUC_SCRIPTS = THU_MUC_GOC / "scripts"
THU_MUC_KET_QUA_EVAL = THU_MUC_GOC / "ket_qua_eval"
if str(THU_MUC_BACKEND) not in sys.path:
    sys.path.insert(0, str(THU_MUC_BACKEND))

from app.config import cau_hinh  # noqa: E402

TIMEOUT_LENH_GIAY = 300

# Tệp duy nhất được import httpx / litellm trong ứng dụng (quy tắc tuyệt đối 1)
TEP_DUOC_GOI_BO_CHAY = {"llm/bo_chay_local.py"}
TEP_DUOC_GOI_LITELLM = {"llm/nha_cung_cap_dam_may.py"}


@dataclass
class KetQuaDong:
    """Kết quả một dòng của Phụ lục 4."""

    so: int
    hang_muc: str
    trang_thai: str  # DAT | CHUA_DAT | CHO_XAC_NHAN | CHUA_AP_DUNG
    chi_tiet: str


def _chay_lenh(lenh: list[str], thu_muc: Path = THU_MUC_BACKEND) -> tuple[bool, str]:
    """Chạy lệnh con, trả (thoát mã 0, dòng cuối có nội dung của đầu ra)."""
    try:
        kq = subprocess.run(
            lenh,
            cwd=thu_muc,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_LENH_GIAY,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return False, f"Không chạy được {' '.join(lenh[:3])}: {err}"
    cac_dong = [d.strip() for d in (kq.stdout + kq.stderr).splitlines() if d.strip()]
    return kq.returncode == 0, cac_dong[-1] if cac_dong else f"mã thoát {kq.returncode}"


def _pytest(*doi_so: str) -> tuple[bool, str]:
    """Chạy pytest trong backend/ bằng chính trình thông dịch của uv run."""
    return _chay_lenh([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *doi_so])


def _kich_ban(ten: str, *doi_so: str) -> tuple[bool, str]:
    """Chạy một kịch bản chẩn đoán đã có trong scripts/."""
    return _chay_lenh([sys.executable, str(THU_MUC_SCRIPTS / ten), *doi_so])


def dong_1() -> tuple[bool, str]:
    """.env không nằm trong Git; không còn bí mật trong mã (dùng lại quet_bi_mat.py)."""
    env_trong_git, _ = _chay_lenh(["git", "ls-files", "--error-unmatch", ".env"], THU_MUC_GOC)
    if env_trong_git:
        return False, ".env đang được Git theo dõi"
    dat, chi_tiet = _kich_ban("quet_bi_mat.py")
    return dat, f".env ngoài Git; quet_bi_mat.py: {chi_tiet}"


def dong_2() -> tuple[bool, str]:
    """Mọi model khai báo đã có trên bộ chạy; thẻ model ghim đủ mức lượng tử hoá."""
    thieu_the = [
        b.model for b in cau_hinh.bac_local if ":" not in b.model or "-q" not in b.model.lower()
    ]
    if thieu_the:
        return False, f"Thẻ model chưa ghim đủ: {', '.join(thieu_the)}"
    dat, chi_tiet = _kich_ban("kiem_tra_bo_chay.py")
    return dat, f"kiem_tra_bo_chay.py: {chi_tiet}"


def dong_3() -> tuple[bool, str]:
    """Chỉ một cửa gọi model: httpx tới bộ chạy và litellm chỉ nằm trong tệp được phép."""
    vi_pham: list[str] = []
    thu_muc_app = THU_MUC_BACKEND / "app"
    for tep in thu_muc_app.rglob("*.py"):
        tuong_doi = tep.relative_to(thu_muc_app).as_posix()
        noi_dung = tep.read_text(encoding="utf-8")
        if re.search(r"^\s*(import|from)\s+httpx\b", noi_dung, re.M) and (
            tuong_doi not in TEP_DUOC_GOI_BO_CHAY
        ):
            vi_pham.append(f"{tuong_doi} (httpx)")
        if re.search(r"^\s*(import|from)\s+litellm\b", noi_dung, re.M) and (
            tuong_doi not in TEP_DUOC_GOI_LITELLM
        ):
            vi_pham.append(f"{tuong_doi} (litellm)")
    if vi_pham:
        return False, "Gọi ngoài cửa: " + ", ".join(vi_pham)
    return True, "httpx chỉ ở bo_chay_local.py, litellm chỉ ở nha_cung_cap_dam_may.py"


def dong_4() -> tuple[bool, str]:
    """Câu hỏi NHAY_CAM không tạo lời gọi nào tới đám mây."""
    return _pytest(
        "tests/test_chinh_sach.py",
        "tests/test_router.py::test_nhay_cam_tang_0_hong_tra_cau_kiem_soat",
        "tests/test_eval.py::test_cau_hoi_nhay_cam_bi_tu_choi_gui_dam_may",
        "tests/test_eval.py::test_runner_bo_qua_cau_nhay_cam_o_tang_dam_may",
    )


def dong_5() -> tuple[bool, str]:
    """keep_alive ở cấp cao nhất; /api/ps cho context_length bằng num_ctx với model đang nạp."""
    dat, chi_tiet = _pytest(
        "tests/test_bo_chay_local.py::test_keep_alive_nam_o_cap_cao_nhat_khong_nam_trong_options"
    )
    if not dat:
        return False, chi_tiet

    from app.giam_sat.suc_khoe import lay_thong_tin_bo_chay

    thong_tin = asyncio.run(lay_thong_tin_bo_chay(cau_hinh))
    if thong_tin.vram.ly_do:
        return False, f"Không đọc được /api/ps: {thong_tin.vram.ly_do}"
    lech = [f"{n.model} ({n.num_ctx_thuc_te}/{n.num_ctx_cau_hinh})" for n in thong_tin.ngu_canh if n.co_lech]
    if lech:
        return False, "context_length khác num_ctx: " + ", ".join(lech)
    da_so = [n.model for n in thong_tin.ngu_canh if n.num_ctx_thuc_te is not None]
    return True, f"keep_alive cấp cao nhất; đã đối chiếu ngữ cảnh: {', '.join(da_so) or 'chưa model nào nạp'}"


def dong_6() -> tuple[bool, str]:
    """Trần ngân sách chặn TRƯỚC khi gọi model."""
    return _pytest("tests/test_chi_phi.py::test_vuot_ngan_sach_0_loi_goi_dam_may_local_van_phuc_vu")


def dong_7() -> tuple[bool, str]:
    """/health không truy cập CSDL; /ready trả san_sang hoặc 503 đúng điều kiện."""
    return _pytest("tests/test_api.py", "-k", "health or ready")


def dong_8() -> tuple[bool, str]:
    """Phát theo dòng qua nginx: header chống đệm và cấu hình proxy_buffering off."""
    cau_hinh_nginx = (THU_MUC_GOC / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    if "proxy_buffering off" not in cau_hinh_nginx:
        return False, "frontend/nginx.conf thiếu proxy_buffering off"
    return _pytest("tests/test_stream.py::test_stream_headers_va_x_accel_buffering")


def dong_9() -> tuple[bool, str]:
    """Giao diện không gọi ra Internet: CSP chỉ 'self', không nạp tài nguyên ngoài."""
    cau_hinh_nginx = (THU_MUC_GOC / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    csp = re.search(r"Content-Security-Policy\s+\"([^\"]+)\"", cau_hinh_nginx)
    if not csp or "default-src 'self'" not in csp.group(1) or "http" in csp.group(1):
        return False, "CSP trong frontend/nginx.conf không giới hạn ở 'self'"
    tai_nguyen_ngoai: list[str] = []
    for tep in (THU_MUC_GOC / "frontend" / "src").rglob("*"):
        if tep.suffix in {".html", ".scss", ".css"}:
            if re.search(r"(src|href|url\()\s*=?\s*[\"']?https?://", tep.read_text(encoding="utf-8")):
                tai_nguyen_ngoai.append(tep.name)
    if tai_nguyen_ngoai:
        return False, "Nạp tài nguyên ngoài: " + ", ".join(sorted(set(tai_nguyen_ngoai)))
    return True, "CSP default-src 'self'; không có liên kết tài nguyên ra Internet"


def dong_10() -> tuple[bool, str]:
    """Mật khẩu băm bcrypt; JWT hết hạn ngắn."""
    return _pytest("tests/test_xac_thuc.py")


def dong_11() -> tuple[bool, str]:
    """Hạn mức 4 lớp hoạt động; 429 có Retry-After."""
    return _pytest("tests/test_han_muc.py")


def dong_12() -> tuple[bool, str]:
    """Nhật ký không chứa nội dung tin nhắn; mọi dòng có ma_yeu_cau."""
    return _pytest("tests/test_nhat_ky.py")


def dong_13() -> tuple[bool, str]:
    """Cổng Ollama không gọi được từ máy khác (thử qua IP LAN của chính máy)."""
    dat, chi_tiet = _kich_ban("kiem_tra_phoi_lo.py", "--tu-dong-ip")
    return dat, f"kiem_tra_phoi_lo.py --tu-dong-ip: {chi_tiet}"


def dong_14() -> tuple[bool, str]:
    """Dữ liệu cá nhân bị che trước khi vào CSDL, nhật ký và trước khi gửi model."""
    return _pytest("tests/test_bao_mat.py", "-k", "not phoi_lo")


def dong_15() -> tuple[bool, str]:
    """Khi MOI_TRUONG=prod: /docs 404; thiếu APP_SECRET, XAC_THUC_GIA=true, CORS '*' bị từ chối."""
    return _pytest(
        "tests/test_main.py::test_prod_tat_tai_lieu_api",
        "tests/test_xac_thuc.py::test_xac_thuc_gia_trong_prod_tu_choi_khoi_dong",
        "tests/test_nhat_ky.py::test_ghi_noi_dung_prod_tu_choi_khoi_dong",
        "tests/test_api.py::test_cors_prod_chan_dau_sao",
        "tests/test_bao_mat.py",
        "-k",
        "prod",
    )


def _tang_can_danh_gia() -> list[str]:
    """Tầng 0 (local1) và mọi tầng đám mây đang bật, trừ tầng 2 chỉ để tham khảo."""
    cac_tang = ["local1"]
    if cau_hinh.che_do_dinh_tuyen != "chi_local":
        cac_tang += [str(t.tang) for t in cau_hinh.chuoi_dam_may if t.kha_dung and t.tang != 2]
    return cac_tang


def dong_16() -> tuple[bool, str]:
    """Bộ câu hỏi vàng lần gần nhất đạt ngưỡng trên tầng 0 và mọi tầng đám mây đang bật."""
    chi_tiet: list[str] = []
    dat_tat_ca = True
    for tang in _tang_can_danh_gia():
        cac_tep = sorted(THU_MUC_KET_QUA_EVAL.glob(f"*_{tang}.json"))
        if not cac_tep:
            dat_tat_ca = False
            chi_tiet.append(f"{tang}: chưa chạy")
            continue
        try:
            du_lieu = json.loads(cac_tep[-1].read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            dat_tat_ca = False
            chi_tiet.append(f"{tang}: không đọc được {cac_tep[-1].name} ({err})")
            continue
        dat = bool(du_lieu.get("dat_nguong"))
        dat_tat_ca = dat_tat_ca and dat
        chi_tiet.append(
            f"{tang}: {du_lieu.get('ty_le_dat_phan_tram', 0):.1f}% "
            f"({'đạt' if dat else 'chưa đạt'} ngưỡng, {cac_tep[-1].stem[:10]})"
        )
    return dat_tat_ca, "; ".join(chi_tiet)


def dong_19() -> tuple[bool, str]:
    """Mọi câu trả lời có nhãn "Nội dung do AI tạo"."""
    return _pytest("tests", "-k", "nhan_ai or hai_moc_kiem_duyet or xong_co_ma_yeu_cau")


def dong_25() -> tuple[bool, str]:
    """Chỉ chủ hội thoại được xem, gửi tiếp và xoá; hội thoại người khác trả KHONG_TIM_THAY."""
    return _pytest(
        "tests/test_api.py::test_get_hoi_thoai_nguoi_khac_tra_404",
        "tests/test_api.py::test_xoa_mem_cuoc_hoi_thoai",
        "tests/test_api_giao_dien.py::test_stream_hoi_thoai_nguoi_khac_bi_tu_choi",
        "tests/test_xac_thuc.py::test_chi_doc_gui_tin_bi_chan_403",
    )


DONG_MAY: list[tuple[int, str, Callable[[], tuple[bool, str]]]] = [
    (1, ".env không nằm trong Git; không còn bí mật trong mã", dong_1),
    (2, "Mọi model khai báo đã có trên bộ chạy; thẻ model đầy đủ", dong_2),
    (3, "Chỉ một cửa gọi model trong router.py", dong_3),
    (4, "Câu hỏi NHAY_CAM không tạo lời gọi nào tới đám mây", dong_4),
    (5, "keep_alive ở cấp cao nhất; /api/ps cho context_length bằng num_ctx", dong_5),
    (6, "Trần ngân sách chặn TRƯỚC khi gọi model", dong_6),
    (7, "/health trả ngay, không truy cập CSDL; /ready đúng trạng thái", dong_7),
    (8, "Phát theo dòng hoạt động qua nginx", dong_8),
    (9, "Giao diện không gọi ra Internet (CSP chỉ 'self')", dong_9),
    (10, "Mật khẩu băm bcrypt; JWT hết hạn ngắn", dong_10),
    (11, "Hạn mức 4 lớp hoạt động; 429 có Retry-After", dong_11),
    (12, "Nhật ký không chứa nội dung tin nhắn; mọi dòng có ma_yeu_cau", dong_12),
    (13, "Cổng Ollama không gọi được từ máy khác", dong_13),
    (14, "Dữ liệu cá nhân bị che trước khi vào CSDL và nhật ký", dong_14),
    (15, "Các kiểm tra khi MOI_TRUONG=prod", dong_15),
    (16, "Bộ câu hỏi vàng đạt ngưỡng trên tầng 0 và mọi tầng đám mây đang bật", dong_16),
    (19, "Mọi câu trả lời có nhãn \"Nội dung do AI tạo\"", dong_19),
    (25, "Chỉ chủ hội thoại xem, gửi tiếp, xoá; người khác nhận KHONG_TIM_THAY", dong_25),
]

DONG_CHUA_AP_DUNG = [
    (17, "Tài liệu thiếu siêu dữ liệu hiệu lực bị từ chối nạp", "Giai đoạn 6 bổ sung"),
    (18, "Ngưỡng từ chối đã hiệu chuẩn, biên an toàn dương", "Giai đoạn 6 bổ sung"),
    (20, "Không phản hồi nào có trường hop_le hoặc duoc_duyet", "Giai đoạn 7 bổ sung"),
]

DONG_NGUOI = [
    (21, "Chủ sở hữu nghiệp vụ và người có quyền ra lệnh dừng đã được chỉ định bằng văn bản"),
    (22, "Một người chưa từng thấy hệ thống đã dùng thử mười phút; đã ghi lại điểm khó khăn"),
    (23, "Điều kiện dừng (mục A.5) đã được phổ biến cho người vận hành"),
    (24, "Bộ câu hỏi vàng do phòng ban nghiệp vụ soạn và ký xác nhận"),
]

NHAN_TRANG_THAI = {
    "DAT": "ĐẠT",
    "CHUA_DAT": "CHƯA ĐẠT",
    "CHO_XAC_NHAN": "CHỜ XÁC NHẬN",
    "CHUA_AP_DUNG": "CHƯA ÁP DỤNG",
}


def chay_kiem_tra() -> list[KetQuaDong]:
    """Chạy mọi dòng Máy đang áp dụng và gom thêm dòng Người, dòng chưa áp dụng."""
    ket_qua: list[KetQuaDong] = []
    for so, hang_muc, ham in DONG_MAY:
        print(f"  ... dòng {so:>2}: {hang_muc}", flush=True)
        try:
            dat, chi_tiet = ham()
        except Exception as err:  # noqa: BLE001 - một dòng lỗi không được làm dừng cả bảng
            dat, chi_tiet = False, f"Lỗi khi kiểm tra: {err}"
        ket_qua.append(KetQuaDong(so, hang_muc, "DAT" if dat else "CHUA_DAT", chi_tiet))
    ket_qua += [KetQuaDong(so, hm, "CHUA_AP_DUNG", ghi_chu) for so, hm, ghi_chu in DONG_CHUA_AP_DUNG]
    ket_qua += [KetQuaDong(so, hm, "CHO_XAC_NHAN", "Người vận hành xác nhận") for so, hm in DONG_NGUOI]
    return sorted(ket_qua, key=lambda k: k.so)


def in_bang(ket_qua: list[KetQuaDong]) -> None:
    """In bảng theo đúng số dòng của Phụ lục 4."""
    print("\n" + "=" * 100)
    print(" DANH MỤC KIỂM TRA TRƯỚC KHI MỞ (PHỤ LỤC 4)")
    print("=" * 100)
    print(f"{'#':>3} | {'Trạng thái':<13} | Hạng mục")
    print("-" * 100)
    for dong in ket_qua:
        print(f"{dong.so:>3} | {NHAN_TRANG_THAI[dong.trang_thai]:<13} | {dong.hang_muc}")
        print(f"{'':>3} | {'':<13} |   -> {dong.chi_tiet}")
    print("=" * 100)


def main() -> None:
    """Chạy danh mục, in bảng và thoát mã 1 nếu còn dòng Máy chưa đạt."""
    print("Đang kiểm tra các dòng Máy của Phụ lục 4 (Giai đoạn 1-5)...")
    ket_qua = chay_kiem_tra()
    in_bang(ket_qua)
    chua_dat = [d.so for d in ket_qua if d.trang_thai == "CHUA_DAT"]
    so_dong_may = sum(1 for d in ket_qua if d.trang_thai in ("DAT", "CHUA_DAT"))
    if chua_dat:
        print(f"KẾT LUẬN: {len(chua_dat)}/{so_dong_may} dòng Máy CHƯA ĐẠT: {chua_dat}")
        sys.exit(1)
    print(f"KẾT LUẬN: {so_dong_may}/{so_dong_may} dòng Máy ĐẠT; dòng Người chờ xác nhận.")
    sys.exit(0)


if __name__ == "__main__":
    main()
