"""Chính sách định tuyến và quy tắc bảo vệ dữ liệu nhạy cảm.

Mô-đun thực hiện Quy tắc tuyệt đối 2 trong AGENTS.md:
Dữ liệu nhãn NHAY_CAM hoặc thuộc phòng ban cấu hình chi_local KHÔNG BAO GIỜ
được gửi ra đám mây, kể cả khi model local hỏng; hết chuỗi local thì trả lời
có kiểm soát, không im lặng.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple

import yaml
from pydantic import BaseModel, Field

from app.config import CauHinhHeThong
from app.config import cau_hinh as cau_hinh_mac_dinh

# Đường dẫn mặc định đến tệp cấu hình chính sách dữ liệu
THU_MUC_GOC = Path(__file__).resolve().parents[3]
DUONG_DAN_CHINH_SACH_YAML_MAC_DINH = THU_MUC_GOC / "config" / "chinh_sach_du_lieu.yaml"


class CheDoDinhTuyen(str, Enum):
    """Chế độ định tuyến cuộc gọi mô hình LLM."""

    CHI_LOCAL = "chi_local"
    LOCAL_TRUOC = "local_truoc"
    DAM_MAY_TRUOC = "dam_may_truoc"

    # Bí danh chữ thường hỗ trợ tra cứu linh hoạt
    chi_local = "chi_local"
    local_truoc = "local_truoc"
    dam_may_truoc = "dam_may_truoc"


class NhanDuLieu(str, Enum):
    """Phân loại mức độ bảo mật của dữ liệu người dùng."""

    THUONG = "THUONG"
    NHAY_CAM = "NHAY_CAM"

    thuong = "THUONG"
    nhay_cam = "NHAY_CAM"


@dataclass(frozen=True)
class Tang:
    """Mô tả một tầng mô hình trong chuỗi định tuyến."""

    so: int
    nguon: Literal["local", "dam_may"]
    ten: str
    cua_so_ngu_canh: int


class KetQuaXacDinhChuoi(NamedTuple):
    """Kết quả xác định chuỗi gồm danh sách tầng và lý do định tuyến."""

    chuoi: list[Tang]
    ly_do_chuoi: str


@dataclass
class ThongTinNguoiDung:
    """Thông tin nhận diện và phân quyền phòng ban của người dùng."""

    ma_nguoi_dung: str = ""
    phong_ban: str = "CNTT"


class CauHinhChinhSachDuLieu(BaseModel):
    """Lược đồ cấu hình chính sách dữ liệu đọc từ YAML."""

    bieu_thuc_nhay_cam: dict[str, str] = Field(default_factory=dict)
    phong_ban_chi_local: list[str] = Field(default_factory=list)
    phong_ban_mac_dinh: str = "CNTT"
    phong_ban_mau: list[str] = Field(default_factory=list)


def nap_cau_hinh_chinh_sach(
    duong_dan_yaml: Path | None = None,
) -> CauHinhChinhSachDuLieu:
    """Nạp cấu hình chính sách dữ liệu từ tệp YAML."""
    duong_dan = duong_dan_yaml or DUONG_DAN_CHINH_SACH_YAML_MAC_DINH
    if not duong_dan.exists():
        return CauHinhChinhSachDuLieu()

    noi_dung = duong_dan.read_text(encoding="utf-8")
    du_lieu = yaml.safe_load(noi_dung)
    if not isinstance(du_lieu, dict):
        return CauHinhChinhSachDuLieu()

    return CauHinhChinhSachDuLieu(**du_lieu)


# Nạp cấu hình chính sách dùng chung cho toàn hệ thống
_cau_hinh_cs = nap_cau_hinh_chinh_sach()


def _bien_dich_bieu_thuc(
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> list[re.Pattern[str]]:
    """Biên dịch danh sách regex từ cấu hình chính sách dữ liệu."""
    cs = cau_hinh_cs or _cau_hinh_cs
    mau_da_bien_dich: list[re.Pattern[str]] = []
    for mau in cs.bieu_thuc_nhay_cam.values():
        if mau:
            mau_da_bien_dich.append(re.compile(mau))
    return mau_da_bien_dich


_MAU_BIEN_DICH_MAC_DINH = _bien_dich_bieu_thuc(_cau_hinh_cs)


def lay_bieu_thuc_theo_loai(
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> list[tuple[str, re.Pattern[str]]]:
    """Trả về cặp (loại, regex đã biên dịch) theo thứ tự khai báo trong bieu_thuc_nhay_cam."""
    cs = cau_hinh_cs or _cau_hinh_cs
    return [(loai, re.compile(mau)) for loai, mau in cs.bieu_thuc_nhay_cam.items() if mau]


# Thẻ thay thế dữ liệu cá nhân do app.core.bao_mat sinh ra, ví dụ <MA_KHACH_HANG_1>
MAU_THE_DA_CHE = re.compile(r"<[A-Z][A-Z_]*_\d+>")


def phat_hien_nhay_cam(
    van_ban: str,
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> bool:
    """Phát hiện dữ liệu nhạy cảm trong văn bản bằng biểu thức chính quy.

    Ghi chú: đây là bộ phát hiện tối giản, thiên về an toàn; việc nhận nhầm
    thành nhạy cảm chỉ khiến câu hỏi được xử lý ở local, không gây rò rỉ.
    """
    if not van_ban:
        return False

    danh_sach_mau = (
        _bien_dich_bieu_thuc(cau_hinh_cs)
        if cau_hinh_cs is not None
        else _MAU_BIEN_DICH_MAC_DINH
    )

    for bieu_thuc in danh_sach_mau:
        if bieu_thuc.search(van_ban):
            return True

    # Thẻ che có đánh số (<SO_DIEN_THOAI_1>...) cho biết lượt cũ đã chứa dữ liệu cá nhân,
    # nên hội thoại vẫn giữ nhãn NHAY_CAM sau khi lịch sử được lưu ở dạng đã che.
    return MAU_THE_DA_CHE.search(van_ban) is not None


def _trich_xuat_van_ban(tin_nhan: Any) -> str:
    """Trích xuất chuỗi văn bản từ đối tượng tin nhắn bất kỳ."""
    if isinstance(tin_nhan, str):
        return tin_nhan
    if isinstance(tin_nhan, dict):
        return str(
            tin_nhan.get("noi_dung")
            or tin_nhan.get("content")
            or tin_nhan.get("text")
            or ""
        )
    if hasattr(tin_nhan, "noi_dung"):
        val = tin_nhan.noi_dung
        return str(val) if val is not None else ""
    if hasattr(tin_nhan, "content"):
        val = tin_nhan.content
        return str(val) if val is not None else ""
    return str(tin_nhan)


def _kiem_tra_tin_nhan_nhay_cam(
    tin_nhan: Any,
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> bool:
    """Kiểm tra một mẩu tin nhắn có nhãn NHAY_CAM hoặc chứa nội dung nhạy cảm."""
    if isinstance(tin_nhan, dict):
        nhan = tin_nhan.get("nhan") or tin_nhan.get("nhan_du_lieu")
        if nhan in (NhanDuLieu.NHAY_CAM, NhanDuLieu.NHAY_CAM.value):
            return True
    elif hasattr(tin_nhan, "nhan_du_lieu"):
        if tin_nhan.nhan_du_lieu in (
            NhanDuLieu.NHAY_CAM,
            NhanDuLieu.NHAY_CAM.value,
        ):
            return True

    van_ban = _trich_xuat_van_ban(tin_nhan)
    return phat_hien_nhay_cam(van_ban, cau_hinh_cs=cau_hinh_cs)


def nhan_cua_hoi_thoai(
    lich_su: list[Any] | None,
    tin_nhan_moi: Any,
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> NhanDuLieu:
    """Xác định nhãn của toàn bộ hội thoại dựa vào tin nhắn mới và lịch sử.

    Chỉ cần một tin nhắn trong phiên chứa thông tin nhạy cảm, mọi lượt tiếp theo
    đều gắn nhãn NHAY_CAM vì ngữ cảnh gửi kèm sẽ chứa thông tin cũ.
    """
    if _kiem_tra_tin_nhan_nhay_cam(tin_nhan_moi, cau_hinh_cs=cau_hinh_cs):
        return NhanDuLieu.NHAY_CAM

    if lich_su:
        for tin_cu in lich_su:
            if _kiem_tra_tin_nhan_nhay_cam(tin_cu, cau_hinh_cs=cau_hinh_cs):
                return NhanDuLieu.NHAY_CAM

    return NhanDuLieu.THUONG


def _lay_phong_ban_nguoi_dung(nguoi: Any, phong_ban_mac_dinh: str) -> str:
    """Trích xuất tên phòng ban của người dùng một cách an toàn."""
    if nguoi is None:
        return phong_ban_mac_dinh
    if isinstance(nguoi, str):
        return nguoi
    if isinstance(nguoi, dict):
        return str(nguoi.get("phong_ban", phong_ban_mac_dinh))
    if hasattr(nguoi, "phong_ban"):
        val = nguoi.phong_ban
        return str(val) if val is not None else phong_ban_mac_dinh
    return phong_ban_mac_dinh


def _tao_tang_local(cau_hinh_he_thong: CauHinhHeThong) -> Tang:
    """Tạo đối tượng Tang cho mô hình cục bộ tầng 0."""
    cua_so = (
        cau_hinh_he_thong.bac_local[0].num_ctx
        if cau_hinh_he_thong.bac_local
        else 8192
    )
    return Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=cua_so)


def _tao_cac_tang_dam_may(cau_hinh_he_thong: CauHinhHeThong) -> list[Tang]:
    """Tạo danh sách Tang đám mây và loại bỏ các tầng không khả dụng."""
    danh_sach: list[Tang] = []
    for t in cau_hinh_he_thong.chuoi_dam_may:
        if t.kha_dung:
            danh_sach.append(
                Tang(
                    so=t.tang,
                    nguon="dam_may",
                    ten=t.ten,
                    cua_so_ngu_canh=t.cua_so_ngu_canh,
                )
            )
    return danh_sach


def xac_dinh_chuoi(
    nguoi: Any,
    nhan_du_lieu: NhanDuLieu | str,
    che_do: CheDoDinhTuyen | str | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    cau_hinh_cs: CauHinhChinhSachDuLieu | None = None,
) -> KetQuaXacDinhChuoi:
    """Xác định chuỗi các tầng mô hình dựa trên nhãn dữ liệu và phòng ban.

    Tuân thủ tuyệt đối Quy tắc 2: Dữ liệu nhạy cảm hoặc thuộc phòng ban chi_local
    chỉ định tuyến qua tầng 0 (local). Trả về danh sách tầng kèm lý do.
    """
    ch_ht = cau_hinh_he_thong or cau_hinh_mac_dinh
    cs_dl = cau_hinh_cs or _cau_hinh_cs

    phong_ban = _lay_phong_ban_nguoi_dung(nguoi, cs_dl.phong_ban_mac_dinh)
    nhan_str = (
        nhan_du_lieu.value
        if isinstance(nhan_du_lieu, NhanDuLieu)
        else str(nhan_du_lieu)
    ).upper()

    che_do_str = (
        che_do.value
        if isinstance(che_do, CheDoDinhTuyen)
        else str(che_do or ch_ht.che_do_dinh_tuyen)
    ).lower()

    tang_0 = _tao_tang_local(ch_ht)

    # Kiểm tra các điều kiện buộc phải dùng duy nhất tầng 0 (local)
    if nhan_str == NhanDuLieu.NHAY_CAM.value:
        return KetQuaXacDinhChuoi(
            chuoi=[tang_0],
            ly_do_chuoi="du_lieu_nhay_cam",
        )

    if phong_ban in cs_dl.phong_ban_chi_local:
        return KetQuaXacDinhChuoi(
            chuoi=[tang_0],
            ly_do_chuoi=f"phong_ban_chi_local ({phong_ban})",
        )

    if che_do_str == CheDoDinhTuyen.CHI_LOCAL.value:
        return KetQuaXacDinhChuoi(
            chuoi=[tang_0],
            ly_do_chuoi="che_do_chi_local",
        )

    # Đám mây được phép tham gia: lọc các tầng có khóa API hợp lệ
    cac_tang_dam_may = _tao_cac_tang_dam_may(ch_ht)

    if che_do_str == CheDoDinhTuyen.DAM_MAY_TRUOC.value:
        return KetQuaXacDinhChuoi(
            chuoi=[*cac_tang_dam_may, tang_0],
            ly_do_chuoi="dam_may_truoc",
        )

    # Mặc định theo chế độ local_truoc
    return KetQuaXacDinhChuoi(
        chuoi=[tang_0, *cac_tang_dam_may],
        ly_do_chuoi="local_truoc",
    )
