"""Bảo vệ dữ liệu nhạy cảm và các móc kiểm duyệt nội dung.

Thứ tự trong luồng chat: kiem_duyet_dau_vao -> phat_hien_nhay_cam (qua nhan_cua_hoi_thoai)
-> che_du_lieu_ca_nhan -> goi_mo_hinh (bản đã che, mọi tầng) -> kiem_duyet_dau_ra
-> restore khi phát ra cho chính người hỏi. CSDL và nhật ký chỉ nhận bản đã che.

Lớp này mỏng có chủ đích (Presidio, llm-guard hoãn tới Giai đoạn 9): chỉ chặn khi chắc chắn,
còn lại ghi nhật ký và gắn cờ để rà soát dần theo dữ liệu thực tế.
"""

import logging
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app.core.nhat_ky import ghi_nhat_ky_chang
from app.llm.chinh_sach import (
    MAU_THE_DA_CHE,
    CauHinhChinhSachDuLieu,
    lay_bieu_thuc_theo_loai,
)

logger = logging.getLogger(__name__)

# Thẻ dài nhất có thể giữ lại khi phát theo dòng, ví dụ <CHI_SO_CONG_TO_123>
DO_DAI_THE_TOI_DA = 32

# Ranh giới bọc nội dung người dùng trong lời nhắc gửi model
MO_RANH_GIOI = "<<<DU_LIEU_NGUOI_DUNG"
DONG_RANH_GIOI = "DU_LIEU_NGUOI_DUNG>>>"

THONG_DIEP_TU_CHOI_LO_LOI_NHAC = (
    "Trợ lý nội bộ không thể cung cấp nội dung cấu hình hay chỉ dẫn hệ thống. "
    "Anh/Chị vui lòng đặt câu hỏi về nghiệp vụ cần hỗ trợ."
)

# Số dòng lời nhắc hệ thống xuất hiện nguyên văn trong câu trả lời thì coi là lộ lời nhắc
SO_DONG_LO_TOI_THIEU = 2
DO_DAI_DONG_LOI_NHAC_TOI_THIEU = 40

# Mẫu tiêm lời nhắc cơ bản, so khớp trên văn bản đã bỏ dấu và viết thường
_MAU_TIEM_LOI_NHAC: tuple[re.Pattern[str], ...] = tuple(
    re.compile(mau)
    for mau in (
        (
            r"(bo qua|phot lo|quen)\s+(het\s+|moi\s+|tat ca\s+|cac\s+|nhung\s+)*"
            r"(chi dan|huong dan|lenh|yeu cau|quy tac)\s+(truoc|o tren|phia tren|ban dau|cu)"
        ),
        (
            r"(tiet lo|in ra|hien thi|nhac lai|cho\s+\w+\s+xem|doc lai)\s+(\w+\s+){0,3}"
            r"(loi nhac|prompt|chi dan|huong dan)\s+(he thong|goc|ban dau|an)"
        ),
        r"dong vai\b.{0,60}(khong\s+(co\s+)?gioi han|khong bi rang buoc|khong kiem duyet)",
        (
            r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+"
            r"(instructions?|prompts?|rules?)"
        ),
        (
            r"(reveal|show|print|repeat|output)\s+(me\s+)?(your|the)\s+"
            r"(system prompt|initial instructions|hidden instructions|system message)"
        ),
        (
            r"(act as|pretend to be|you are now)\b.{0,60}"
            r"(unrestricted|no restrictions|without (any )?(limits|restrictions|filters))"
        ),
        r"\bjailbreak\b|\bdan mode\b",
    )
)


class KetQuaKiemDuyet(BaseModel):
    """Kết quả kiểm tra kiểm duyệt nội dung đầu vào hoặc phản hồi đầu ra."""

    cho_qua: bool = Field(
        default=True, description="Cờ cho phép tiếp tục luồng xử lý hoặc lưu trữ"
    )
    ly_do: str | None = Field(
        default=None, description="Lý do từ chối nếu nội dung vi phạm chính sách"
    )
    noi_dung_thay_the: str | None = Field(
        default=None, description="Nội dung đã được khử nhạy cảm hoặc thay thế an toàn"
    )
    nghi_tiem_loi_nhac: bool = Field(
        default=False, description="Đầu vào khớp mẫu tiêm lời nhắc; chỉ gắn cờ, không chặn"
    )


@dataclass
class KetQuaChe:
    """Kết quả che dữ liệu cá nhân của một yêu cầu.

    Bảng ánh xạ thẻ -> giá trị thật chỉ nằm trong bộ nhớ của yêu cầu hiện tại:
    không lưu CSDL, không ghi nhật ký (repr=False để không lọt vào chuỗi mô tả đối tượng).
    """

    van_ban_da_che: str
    so_the_theo_loai: dict[str, int] = field(default_factory=dict)
    _anh_xa: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def co_du_lieu_ca_nhan(self) -> bool:
        """Có ít nhất một giá trị đã bị thay bằng thẻ."""
        return bool(self._anh_xa)

    def restore(self, van_ban: str) -> str:
        """Khôi phục giá trị thật cho các thẻ có trong van_ban; thẻ lạ giữ nguyên."""
        if not self._anh_xa:
            return van_ban
        return MAU_THE_DA_CHE.sub(lambda m: self._anh_xa.get(m.group(0), m.group(0)), van_ban)


class BoKhoiPhucDong:
    """Khôi phục thẻ trên luồng phát theo dòng, giữ lại phần thẻ bị cắt giữa hai mảnh."""

    def __init__(self, ket_qua_che: KetQuaChe) -> None:
        self._ket_qua_che = ket_qua_che
        self._phan_giu = ""

    def them(self, manh: str) -> str:
        """Nhận một mảnh mới, trả phần đã khôi phục có thể phát ngay."""
        van_ban = self._phan_giu + manh
        vi_tri_mo = van_ban.rfind("<")
        con_mo = vi_tri_mo != -1 and ">" not in van_ban[vi_tri_mo:]
        if con_mo and len(van_ban) - vi_tri_mo <= DO_DAI_THE_TOI_DA:
            self._phan_giu = van_ban[vi_tri_mo:]
            van_ban = van_ban[:vi_tri_mo]
        else:
            self._phan_giu = ""
        return self._ket_qua_che.restore(van_ban)

    def xa_het(self) -> str:
        """Trả phần còn giữ lại khi luồng kết thúc."""
        con_lai, self._phan_giu = self._phan_giu, ""
        return self._ket_qua_che.restore(con_lai)


def _bo_dau(van_ban: str) -> str:
    """Bỏ dấu tiếng Việt và viết thường để so khớp mẫu tất định."""
    chuoi = unicodedata.normalize("NFD", van_ban)
    chuoi = "".join(k for k in chuoi if unicodedata.category(k) != "Mn")
    return chuoi.replace("đ", "d").replace("Đ", "d").lower()


def dem_the_da_dung(cac_van_ban: Iterable[str]) -> dict[str, int]:
    """Số thứ tự lớn nhất đã dùng theo loại thẻ trong các lượt cũ (đã che) của hội thoại.

    Lượt mới đánh số tiếp theo để một thẻ không mang hai giá trị khác nhau trong cùng ngữ cảnh.
    """
    lon_nhat: dict[str, int] = {}
    for van_ban in cac_van_ban:
        for the in MAU_THE_DA_CHE.findall(van_ban):
            loai, _, so = the[1:-1].rpartition("_")
            lon_nhat[loai] = max(lon_nhat.get(loai, 0), int(so))
    return lon_nhat


def che_du_lieu_ca_nhan(
    van_ban: str,
    *,
    so_bat_dau: dict[str, int] | None = None,
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> KetQuaChe:
    """Thay dữ liệu cá nhân bằng thẻ có đánh số, ví dụ <SO_DIEN_THOAI_1>.

    Dùng lại bieu_thuc_nhay_cam trong config/chinh_sach_du_lieu.yaml. Cùng một giá trị xuất
    hiện nhiều lần chỉ sinh một thẻ. Nhãn cố định kiểu [SO_DIEN_THOAI] làm model mất ngữ cảnh
    vì hai số khác nhau trở thành hai chuỗi giống hệt nhau, nên thẻ luôn có số thứ tự.
    """
    # Gom mọi đoạn khớp trên văn bản gốc, giải quyết chồng lấn: vị trí sớm hơn thắng,
    # cùng vị trí thì biểu thức khai báo trước thắng
    doan_khop: list[tuple[int, int, int, str]] = []
    for thu_tu, (loai, bieu_thuc) in enumerate(lay_bieu_thuc_theo_loai(cau_hinh_cs)):
        for khop in bieu_thuc.finditer(van_ban):
            nhom = next((i for i in range(1, (khop.re.groups or 0) + 1) if khop.group(i)), 0)
            dau, cuoi = khop.span(nhom)
            if cuoi > dau:
                doan_khop.append((dau, thu_tu, cuoi, loai.upper()))
    doan_khop.sort()

    dem = dict(so_bat_dau or {})
    the_theo_gia_tri: dict[tuple[str, str], str] = {}
    anh_xa: dict[str, str] = {}
    so_the_theo_loai: dict[str, int] = {}
    cac_phan: list[str] = []
    vi_tri = 0
    for dau, _, cuoi, loai in doan_khop:
        if dau < vi_tri:
            continue
        gia_tri = van_ban[dau:cuoi]
        the = the_theo_gia_tri.get((loai, gia_tri))
        if the is None:
            dem[loai] = dem.get(loai, 0) + 1
            the = f"<{loai}_{dem[loai]}>"
            the_theo_gia_tri[(loai, gia_tri)] = the
            anh_xa[the] = gia_tri
            so_the_theo_loai[loai] = so_the_theo_loai.get(loai, 0) + 1
        cac_phan.append(van_ban[vi_tri:dau])
        cac_phan.append(the)
        vi_tri = cuoi
    cac_phan.append(van_ban[vi_tri:])

    return KetQuaChe(
        van_ban_da_che="".join(cac_phan),
        so_the_theo_loai=so_the_theo_loai,
        _anh_xa=anh_xa,
    )


def boc_ranh_gioi(noi_dung: str) -> str:
    """Bọc nội dung người dùng trong khối ranh giới; lời nhắc hệ thống coi khối này là dữ liệu."""
    return f"{MO_RANH_GIOI}\n{noi_dung}\n{DONG_RANH_GIOI}"


def phat_hien_tiem_loi_nhac(noi_dung: str) -> bool:
    """Nhận diện vài mẫu tiêm lời nhắc tiếng Việt và tiếng Anh thường gặp."""
    van_ban = _bo_dau(noi_dung)
    return any(mau.search(van_ban) for mau in _MAU_TIEM_LOI_NHAC)


@lru_cache(maxsize=1)
def _cac_dong_loi_nhac_he_thong() -> tuple[str, ...]:
    """Các dòng đủ dài của lời nhắc hệ thống (bỏ phần tra_loi_khi_ban vốn được phép phát ra)."""
    from app.chat.ngu_canh import doc_loi_nhac_he_thong

    noi_dung = doc_loi_nhac_he_thong().split("## tra_loi_khi_ban", 1)[0]
    cac_dong: list[str] = []
    for dong in noi_dung.splitlines():
        dong_chuan = " ".join(dong.strip(" -#*`").split()).lower()
        if len(dong_chuan) >= DO_DAI_DONG_LOI_NHAC_TOI_THIEU:
            cac_dong.append(dong_chuan)
    return tuple(cac_dong)


def phat_hien_lo_loi_nhac(noi_dung: str) -> bool:
    """Câu trả lời chứa nguyên văn từ SO_DONG_LO_TOI_THIEU dòng lời nhắc hệ thống trở lên."""
    van_ban = " ".join(noi_dung.split()).lower()
    if "phien_ban:" in van_ban:
        return True
    so_dong_lo = sum(1 for dong in _cac_dong_loi_nhac_he_thong() if dong in van_ban)
    return so_dong_lo >= SO_DONG_LO_TOI_THIEU


async def kiem_duyet_dau_vao(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt nội dung người dùng nhập vào trước khi dựng ngữ cảnh hội thoại.

    Giới hạn độ dài do lược đồ yêu cầu (GIOI_HAN_DO_DAI_TIN_NHAN) chặn trước ở tầng FastAPI.
    Mẫu tiêm lời nhắc chỉ được ghi nhật ký và gắn cờ, không chặn: lời nhắc hệ thống và khối
    ranh giới đã hướng model coi nội dung người dùng là dữ liệu.
    """
    if not phat_hien_tiem_loi_nhac(noi_dung):
        return KetQuaKiemDuyet(cho_qua=True)

    ghi_nhat_ky_chang(
        chang="nghi_tiem_loi_nhac",
        thong_diep=f"Đầu vào khớp mẫu tiêm lời nhắc (độ dài {len(noi_dung)} ký tự)",
        muc=logging.WARNING,
        nguoi_id=getattr(nguoi, "id", None),
        phong_ban=getattr(nguoi, "phong_ban", None),
    )
    return KetQuaKiemDuyet(cho_qua=True, nghi_tiem_loi_nhac=True)


async def kiem_duyet_dau_ra(
    noi_dung: str,
    nguoi: Any,
) -> KetQuaKiemDuyet:
    """Móc kiểm duyệt phản hồi mô hình trên toàn văn trước khi lưu CSDL và trả về.

    Câu trả lời chứa đoạn lời nhắc hệ thống được thay bằng thông điệp từ chối có kiểm soát.
    """
    if not phat_hien_lo_loi_nhac(noi_dung):
        return KetQuaKiemDuyet(cho_qua=True)

    ghi_nhat_ky_chang(
        chang="lo_loi_nhac_he_thong",
        thong_diep="Câu trả lời chứa đoạn lời nhắc hệ thống, đã thay bằng thông điệp từ chối",
        muc=logging.WARNING,
        nguoi_id=getattr(nguoi, "id", None),
        phong_ban=getattr(nguoi, "phong_ban", None),
    )
    return KetQuaKiemDuyet(cho_qua=True, noi_dung_thay_the=THONG_DIEP_TU_CHOI_LO_LOI_NHAC)


# ---------------------------------------------------------------------------
# BỐI CẢNH BẢO MẬT BỘ CHẠY CỤC BỘ (OLLAMA / LM STUDIO):
# Máy chủ Ollama KHÔNG CÓ CƠ CHẾ XÁC THỰC. API của nó không chỉ phục vụ sinh văn
# bản mà còn cho phép: tải model (/api/pull), tạo model (/api/create), sao chép
# (/api/copy), đẩy (/api/push) và xoá model (/api/delete). Mặc định Ollama chỉ
# nghe ở 127.0.0.1 nên an toàn; rủi ro phát sinh khi mở rộng để container hoặc
# máy khác gọi được (lộ GPU miễn phí, bị tải tràn ổ cứng hoặc xoá model).
# LM Studio có rủi ro tương tự khi bật "Serve on Local Network".
# ---------------------------------------------------------------------------

THONG_DIEP_BA_CACH_NOI_AN_TOAN = """
LỖI CẤU HÌNH BẢO MẬT: Phát hiện cổng bộ chạy cục bộ bị phơi lộ ({dia_chi_phoi_lo}).
Máy chủ Ollama KHÔNG có xác thực. API cho phép tải, tạo, sao chép, đẩy và xoá model.
Trong môi trường MOI_TRUONG=prod, ứng dụng TỪ CHỐI khởi động để bảo vệ an toàn hệ thống.

Vui lòng áp dụng một trong ba cách nối an toàn sau (xếp theo thứ tự ưu tiên):
  Cách A - GIỮ 127.0.0.1 (mặc định của Ollama, ưu tiên số 1):
    - Windows/macOS với Docker Desktop: Giữ nguyên OLLAMA_HOST=127.0.0.1:11434. Container
      gọi qua http://host.docker.internal:11434, Docker Desktop tự chuyển tới loopback máy.
    - Linux (Docker Engine): Backend dùng network_mode: host hoặc chạy backend ngoài container.
  Cách B - Chỉ dùng trên máy chủ Linux:
    - Bind vào địa chỉ cầu nối Docker (thường 172.17.0.1, xem bằng 'ip addr show docker0'),
      KHÔNG bind 0.0.0.0, kèm luật ufw chỉ cho dải mạng Docker vào cổng 11434.
    - Trên Windows: Dùng PowerShell quản trị tạo New-NetFirewallRule hạn chế dải RemoteAddress.
  Cách C - Buộc phải mở rộng hơn:
    - Đặt Nginx phía trước, bật Basic Auth hoặc mTLS, CHẶN các đường quản trị:
      /api/pull, /api/create, /api/delete, /api/push, /api/copy.
    - Chỉ cho qua các endpoint suy luận: /api/chat, /v1/chat/completions, /v1/embeddings,
      /api/embed, /api/tags, /api/ps, /api/show. Tham khảo mẫu tại deploy/nginx-ollama.conf.
"""


def _trich_xuat_host(dia_chi: str) -> str:
    """Trích xuất hostname hoặc IP từ URL hoặc chuỗi địa chỉ host:port."""
    dia_chi_chuan = dia_chi.strip()
    if not dia_chi_chuan:
        return ""
    if dia_chi_chuan.startswith(":"):
        return "0.0.0.0"
    if "://" not in dia_chi_chuan:
        dia_chi_chuan = f"http://{dia_chi_chuan}"
    try:
        from urllib.parse import urlparse

        parsed = urlparse(dia_chi_chuan)
        return parsed.hostname or ""
    except Exception:  # noqa: BLE001
        return dia_chi.split(":")[0].strip()


def _la_dia_chi_phoi_lo(host: str) -> bool:
    """Xác định hostname/IP có phải là địa chỉ phơi lộ nguy hiểm hay không.

    Địa chỉ an toàn: loopback (127.0.0.1, localhost, ::1), host.docker.internal,
    và dải cầu nối nội bộ Docker (172.17.0.1 hoặc mạng docker0 172.17.0.0/16).
    Mọi địa chỉ 0.0.0.0, IP công cộng, hoặc dải LAN khác đều coi là phơi lộ.
    """
    import ipaddress

    host_chuan = host.strip().lower()
    if not host_chuan:
        return False
    if host_chuan in {"localhost", "host.docker.internal"}:
        return False
    if host_chuan in {"0.0.0.0", "::"}:
        return True

    try:
        ip = ipaddress.ip_address(host_chuan)
        if ip.is_loopback:
            return False
        # Dải cầu nối Docker mặc định (172.17.0.0/16) được chấp nhận cho Cách B
        if ip == ipaddress.ip_address("172.17.0.1") or ip in ipaddress.ip_network("172.17.0.0/16"):
            return False
        if ip.is_global or ip.is_unspecified or ip.is_private:
            return True
    except ValueError:
        # Tên miền không phải IP chuẩn và không nằm trong danh sách an toàn
        return True
    return False


def kiem_tra_phoi_lo(
    dia_chi: str | None = None,
    ollama_host: str | None = None,
    moi_truong: str | None = None,
) -> bool:
    """Kiểm tra nguy cơ phơi lộ cổng bộ chạy mô hình local (Ollama / LM Studio).

    Chạy trong lifespan lúc khởi động. Phát hiện 0.0.0.0, địa chỉ công cộng, hoặc
    địa chỉ LAN không được phép. Môi trường prod phát hiện phơi lộ sẽ từ chối khởi động.
    """
    import logging
    import os
    import sys

    from app.config import cau_hinh

    logger = logging.getLogger(__name__)

    dia_chi_chinh = dia_chi if dia_chi is not None else cau_hinh.bo_chay.dia_chi
    bien_ollama_host = (
        ollama_host if ollama_host is not None else os.environ.get("OLLAMA_HOST")
    )
    env_moi_truong = moi_truong if moi_truong is not None else cau_hinh.moi_truong

    cac_dia_chi_can_kiem_tra: list[tuple[str, str]] = []
    if dia_chi_chinh:
        cac_dia_chi_can_kiem_tra.append(("DIA_CHI_BO_CHAY", dia_chi_chinh))
    if bien_ollama_host:
        cac_dia_chi_can_kiem_tra.append(("OLLAMA_HOST", bien_ollama_host))

    for nguon, gia_tri in cac_dia_chi_can_kiem_tra:
        host = _trich_xuat_host(gia_tri)
        if _la_dia_chi_phoi_lo(host):
            thong_diep = THONG_DIEP_BA_CACH_NOI_AN_TOAN.format(
                dia_chi_phoi_lo=f"{nguon}={gia_tri}"
            )
            logger.warning(
                "CẢNH BÁO BẢO MẬT: Phát hiện cổng bộ chạy local có nguy cơ bị phơi lộ: "
                "%s=%s (host: %s)",
                nguon,
                gia_tri,
                host,
            )
            if env_moi_truong == "prod":
                logger.critical(thong_diep)
                sys.exit(thong_diep)
            return False

    return True
