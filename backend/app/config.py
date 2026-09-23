"""Mô-đun quản trị và xác thực cấu hình hệ thống từ biến môi trường và tệp YAML."""

import logging
import os
import re
import socket
from pathlib import Path
from typing import Any

import dotenv
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Thư mục gốc repo và các đường dẫn tệp cấu hình mặc định
THU_MUC_GOC = Path(__file__).resolve().parents[2]
DUONG_DAN_ENV_MAC_DINH = THU_MUC_GOC / ".env"
DUONG_DAN_MODELS_YAML_MAC_DINH = THU_MUC_GOC / "config" / "models.yaml"

# Hai tập dưới đây là giá trị mã nguồn hiểu được (mỗi giá trị ứng với một nhánh xử lý),
# không phải cấu hình vận hành; danh sách hồ sơ GPU thì chỉ khai báo trong models.yaml.
CAC_CHE_DO_DINH_TUYEN_HOP_LE = {"chi_local", "local_truoc", "dam_may_truoc"}
CAC_LOAI_BO_CHAY_HOP_LE = {"ollama", "lmstudio"}

# Giá trị mẫu giả trong .env.example, coi như chưa khai báo
GIA_TRI_MAU_GIA = "dan-khoa-that-vao-day"


class CauHinhBacLocal(BaseModel):
    """Cấu hình cho một bậc mô hình local (chính hoặc nhỏ)."""

    bac: str
    model: str
    num_ctx: int


class CauHinhTangDamMay(BaseModel):
    """Cấu hình cho một tầng mô hình đám mây trong chuỗi định tuyến."""

    tang: int
    ten: str
    model: str
    api_key_env: str
    gia_vao_usd_moi_trieu: float
    gia_ra_usd_moi_trieu: float
    timeout_giay: int = 90
    # Bắt buộc: ngân sách token của hội thoại tính theo cửa sổ nhỏ nhất trong chuỗi
    cua_so_ngu_canh: int
    tham_so_them: dict[str, Any] = Field(default_factory=dict)
    ghi_chu: str | None = None
    kha_dung: bool = True


class CauHinhBoChay(BaseModel):
    """Cấu hình bộ chạy mô hình local (Ollama hoặc LM Studio)."""

    loai: str
    dia_chi: str
    timeout_giay: int = 120


class CauHinhLocalChung(BaseModel):
    """Cấu hình chung cho các mô hình chạy local."""

    keep_alive: str = "30m"
    nhiet_do: float = 0.3
    nguong_hang_doi_ha_cap: int = 3
    suy_luan: bool = False


class CauHinhCaiDatChung(BaseModel):
    """Cài đặt chung cho chuỗi định tuyến và gọi mô hình."""

    so_lan_thu_lai_moi_tang: int = 2
    giay_gian_cach_dau: float = 0.5
    gioi_han_token_ra: int = 1024
    ngu_canh_du_phong_token: int = 512
    he_so_an_toan_token: float = 1.15
    nguong_canh_bao_ngan_sach: float = 0.80
    nguong_ty_le_roi_tang: float = 0.20


class CaiDatMoiTruong(BaseSettings):
    """Lớp đọc và kiểm tra các biến môi trường từ .env và hệ thống."""

    moi_truong: str = "dev"
    che_do_dinh_tuyen: str = "local_truoc"
    ho_so_gpu: str = "gpu8"

    # Không đặt giá trị mặc định cho khoá API, chuỗi kết nối hay khoá bí mật:
    # thiếu thì để None, thành phần cần dùng tự từ chối khi khởi tạo.
    google_api_key: str | None = None
    openrouter_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    database_url: str | None = None
    app_secret: str | None = None

    cors_origins: str = "http://localhost:4200,http://localhost:8080"
    ngan_sach_ngay_usd: float = 10.0
    # Để trống thì lấy num_parallel của hồ sơ GPU (phải khớp OLLAMA_NUM_PARALLEL)
    so_luong_dong_thoi: int | None = None
    do_dai_hang_doi_toi_da: int = 20
    timeout_giay: int = 60
    ghi_noi_dung: bool = False
    xac_thuc_gia: bool = True

    # Cấu hình hạn mức (Rate Limiting)
    han_muc_ip_phut: int = 20
    han_muc_moi_nguoi_gio: int = 60
    he_so_bac_pro: float = 2.0
    han_muc_token_ngay: int = 100000
    han_muc_chi_phi_ngay_free_usd: float = 0.5
    han_muc_chi_phi_ngay_pro_usd: float = 2.0

    model_config = SettingsConfigDict(
        env_file=DUONG_DAN_ENV_MAC_DINH,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


class CauHinhHeThong(BaseModel):
    """Đối tượng cấu hình hoàn chỉnh phơi ra cho toàn bộ ứng dụng."""

    bac_local: list[CauHinhBacLocal]
    so_model_nap_cung_luc: int
    chuoi_dam_may: list[CauHinhTangDamMay]
    che_do_dinh_tuyen: str
    cai_dat_chung: CauHinhCaiDatChung

    bo_chay: CauHinhBoChay
    ho_so_gpu: dict[str, Any]
    ho_so_gpu_dang_chon: str
    dung_luong_vram_gb: int = 8
    local_chung: CauHinhLocalChung
    database_url: str | None
    moi_truong: str
    ngan_sach_ngay_usd: float
    so_luong_dong_thoi: int
    do_dai_hang_doi_toi_da: int
    timeout_giay: int
    ghi_noi_dung: bool
    xac_thuc_gia: bool
    app_secret: str | None
    cors_origins: list[str]
    han_muc_ip_phut: int = 20
    han_muc_moi_nguoi_gio: int = 60
    he_so_bac_pro: float = 2.0
    han_muc_token_ngay: int = 100000
    han_muc_chi_phi_ngay_free_usd: float = 0.5
    han_muc_chi_phi_ngay_pro_usd: float = 2.0


def _doc_bien_gop(duong_dan_env: Path | None) -> dict[str, str]:
    """Gộp biến từ .env và os.environ, trong đó os.environ có mức ưu tiên cao hơn."""
    bien_gop: dict[str, str] = {}
    if duong_dan_env and duong_dan_env.exists():
        for khoa, gia_tri in dotenv.dotenv_values(duong_dan_env).items():
            if gia_tri is not None:
                bien_gop[khoa] = gia_tri
    bien_gop.update(os.environ)
    return bien_gop


def _kiem_tra_phan_giai_host(host: str) -> bool:
    """Kiểm tra tên máy có phân giải về địa chỉ dùng được từ ngoài container hay không."""
    try:
        ip = socket.gethostbyname(host)
    except (socket.gaierror, OSError):
        return False
    # Docker Desktop trên Windows cho host.docker.internal trỏ về IP mạng WSL (172.x),
    # trong khi Ollama trên máy Windows chỉ nghe ở 127.0.0.1: coi như không phân giải được.
    if host == "host.docker.internal" and not ip.startswith("127."):
        return False
    return True


def _dieu_chinh_dia_chi_ngoai_container(
    dia_chi_bo_chay: str,
    database_url: str | None,
    dang_trong_container: bool,
) -> tuple[str, str | None]:
    """Đổi host.docker.internal và máy 'db' về localhost khi chạy ngoài container."""
    if dang_trong_container:
        return dia_chi_bo_chay, database_url

    dia_chi_moi = dia_chi_bo_chay
    if "host.docker.internal" in dia_chi_bo_chay and not _kiem_tra_phan_giai_host(
        "host.docker.internal"
    ):
        dia_chi_moi = dia_chi_bo_chay.replace("host.docker.internal", "localhost")
        logger.info("Chạy ngoài container: chuyển dia_chi_bo_chay sang localhost")

    if database_url is None or not re.search(r"@db(?=[:/])", database_url):
        return dia_chi_moi, database_url
    logger.info("Chạy ngoài container: chuyển máy 'db' trong DATABASE_URL sang localhost")
    return dia_chi_moi, re.sub(r"@db(?=[:/])", "@localhost", database_url)


def _kiem_tra_the_model_local(the_model: str) -> bool:
    """Kiểm tra thẻ model local có đủ dấu hai chấm và định danh lượng tử hoá."""
    if ":" not in the_model:
        return False
    _, phan_tag = the_model.split(":", 1)
    if "-" not in phan_tag:
        return False
    phan_luong_tu = phan_tag.rsplit("-", 1)[1].lower()
    return bool(re.match(r"^(?:q\d+[_\w]*|fp\d+|bf\d+)$", phan_luong_tu))


def _kiem_tra_mot_ho_so(ten_hs: str, hs: dict[str, Any]) -> None:
    """Kiểm tra thẻ model, num_ctx và so_model_nap_cung_luc của một hồ sơ GPU."""
    chinh = hs.get("chinh", {})
    nho = hs.get("nho", {})
    for ten_bac, bac in (("chinh", chinh), ("nho", nho)):
        the_model = str(bac.get("model", ""))
        if not _kiem_tra_the_model_local(the_model):
            raise ValueError(
                "thẻ model phải ghi đầy đủ tên, kích thước và mức lượng tử hoá "
                "(dạng <tên>:<kích thước>-<lượng tử hoá>); "
                f"sai ở hồ sơ {ten_hs}, bậc {ten_bac}: '{the_model}'"
            )

    if nho.get("num_ctx", 0) > chinh.get("num_ctx", 0):
        raise ValueError("num_ctx của bậc nho phải nhỏ hơn hoặc bằng bậc chinh")

    if hs.get("so_model_nap_cung_luc", 0) not in (1, 2):
        raise ValueError(f"so_model_nap_cung_luc của hồ sơ '{ten_hs}' phải là 1 hoặc 2")

    if "dung_luong_vram_gb" in hs:
        try:
            vram_gb = int(hs["dung_luong_vram_gb"])
            if vram_gb <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(f"dung_luong_vram_gb của hồ sơ '{ten_hs}' phải là số nguyên dương")


def _kiem_tra_tinh_hop_le_ho_so_gpu(
    ho_so_dict: dict[str, Any],
    ho_so_chon: str,
) -> None:
    """Kiểm tra hồ sơ đang chọn có trong models.yaml và mọi hồ sơ đều hợp lệ."""
    if ho_so_chon not in ho_so_dict:
        danh_sach = ", ".join(ho_so_dict)
        raise ValueError(
            f"HO_SO_GPU không hợp lệ: '{ho_so_chon}'. Phải là một trong các khoá "
            f"khai báo ở ho_so_gpu trong config/models.yaml: {danh_sach}"
        )
    for ten_hs, hs in ho_so_dict.items():
        _kiem_tra_mot_ho_so(ten_hs, hs)


def _kiem_tra_chuoi_dam_may(chuoi_dam_may: list[dict[str, Any]]) -> None:
    """Kiểm tra chuỗi đám mây có số tầng tăng dần nghiêm ngặt và không trùng."""
    danh_sach_tang = [t.get("tang", 0) for t in chuoi_dam_may]
    if len(danh_sach_tang) != len(set(danh_sach_tang)):
        raise ValueError("chuoi_dam_may có tầng bị trùng lặp")
    for truoc, sau in zip(danh_sach_tang, danh_sach_tang[1:]):
        if truoc >= sau:
            raise ValueError("chuoi_dam_may phải có số tầng tăng dần")


def _kiem_tra_che_do_dinh_tuyen(che_do: str) -> None:
    """Kiểm tra chế độ định tuyến có nằm trong danh sách cho phép."""
    if che_do not in CAC_CHE_DO_DINH_TUYEN_HOP_LE:
        danh_sach = ", ".join(sorted(CAC_CHE_DO_DINH_TUYEN_HOP_LE))
        raise ValueError(
            f"CHE_DO_DINH_TUYEN không hợp lệ: '{che_do}'. Phải là một trong: {danh_sach}"
        )


def _kiem_tra_loai_bo_chay(loai: str) -> None:
    """Kiểm tra LOAI_BO_CHAY là một bộ chạy mà mã nguồn có hiện thực."""
    if loai not in CAC_LOAI_BO_CHAY_HOP_LE:
        danh_sach = ", ".join(sorted(CAC_LOAI_BO_CHAY_HOP_LE))
        raise ValueError(f"LOAI_BO_CHAY không hợp lệ: '{loai}'. Phải là một trong: {danh_sach}")


def _tao_chuoi_dam_may_da_xac_thuc(
    danh_sach_raw: list[dict[str, Any]],
    bien_gop: dict[str, str],
) -> list[CauHinhTangDamMay]:
    """Chuyển đổi danh sách tầng đám mây và xác định tính khả dụng của từng tầng."""
    ket_qua: list[CauHinhTangDamMay] = []
    for muc in danh_sach_raw:
        tang = CauHinhTangDamMay(**muc)
        gia_tri_khoa = bien_gop.get(tang.api_key_env, "").strip()
        tang.kha_dung = bool(gia_tri_khoa) and gia_tri_khoa != GIA_TRI_MAU_GIA
        if not tang.kha_dung:
            logger.info(
                "Tầng %s (%s) thiếu cấu hình khoá API, đánh dấu không khả dụng (kha_dung=False)",
                tang.tang,
                tang.ten,
            )
        ket_qua.append(tang)
    return ket_qua


def _doc_yaml_da_thay_bien(duong_dan_yaml: Path, bien_gop: dict[str, str]) -> dict[str, Any]:
    """Đọc models.yaml và thay ${BIEN} bằng giá trị đã gộp từ môi trường và .env."""
    noi_dung_tho = duong_dan_yaml.read_text(encoding="utf-8")
    noi_dung = re.sub(
        r"\$\{([A-Za-z0-9_]+)\}",
        lambda khop: bien_gop.get(khop.group(1), ""),
        noi_dung_tho,
    )
    du_lieu = yaml.safe_load(noi_dung)
    return du_lieu if isinstance(du_lieu, dict) else {}


def _tao_bac_local(ho_so: dict[str, Any]) -> list[CauHinhBacLocal]:
    """Lấy hai bậc local (chinh, nho) của hồ sơ GPU đang chọn."""
    return [
        CauHinhBacLocal(bac=ten, model=ho_so[ten]["model"], num_ctx=ho_so[ten]["num_ctx"])
        for ten in ("chinh", "nho")
    ]


def _doc_cai_dat_moi_truong(duong_dan_env: Path) -> CaiDatMoiTruong:
    """Đọc biến môi trường với đúng tệp .env được chỉ định (biến thật vẫn được ưu tiên)."""

    class CaiDatTheoTep(CaiDatMoiTruong):
        model_config = SettingsConfigDict(
            env_file=duong_dan_env,
            env_file_encoding="utf-8",
            env_ignore_empty=True,
            extra="ignore",
        )

    return CaiDatTheoTep()


def nap_cau_hinh(
    duong_dan_env: Path | None = None,
    duong_dan_yaml: Path | None = None,
) -> CauHinhHeThong:
    """Nạp, thay thế biến, xác thực toàn bộ cấu hình hệ thống và trả về CauHinhHeThong."""
    env_path = duong_dan_env or DUONG_DAN_ENV_MAC_DINH
    bien_gop = _doc_bien_gop(env_path)
    du_lieu_yaml = _doc_yaml_da_thay_bien(duong_dan_yaml or DUONG_DAN_MODELS_YAML_MAC_DINH, bien_gop)
    cai_dat_env = _doc_cai_dat_moi_truong(env_path)

    bo_chay_dict: dict[str, Any] = dict(du_lieu_yaml.get("bo_chay", {}))
    ho_so_dict: dict[str, Any] = du_lieu_yaml.get("ho_so_gpu", {})
    chuoi_dam_may_raw: list[dict[str, Any]] = du_lieu_yaml.get("chuoi_dam_may", [])

    _kiem_tra_che_do_dinh_tuyen(cai_dat_env.che_do_dinh_tuyen)
    _kiem_tra_loai_bo_chay(str(bo_chay_dict.get("loai", "")).strip().lower())
    _kiem_tra_tinh_hop_le_ho_so_gpu(ho_so_dict, cai_dat_env.ho_so_gpu)
    _kiem_tra_chuoi_dam_may(chuoi_dam_may_raw)

    bo_chay_dict["loai"] = str(bo_chay_dict["loai"]).strip().lower()
    bo_chay_dict["dia_chi"], database_url = _dieu_chinh_dia_chi_ngoai_container(
        str(bo_chay_dict.get("dia_chi", "")),
        cai_dat_env.database_url,
        dang_trong_container=os.path.exists("/.dockerenv"),
    )
    if cai_dat_env.ghi_noi_dung and cai_dat_env.moi_truong != "dev":
        raise ValueError(
            "Cờ GHI_NOI_DUNG=true chỉ được phép bật khi MOI_TRUONG=dev; "
            f"bật trong môi trường '{cai_dat_env.moi_truong}' bị từ chối khởi động."
        )

    ho_so_chon = ho_so_dict[cai_dat_env.ho_so_gpu]

    return CauHinhHeThong(
        bac_local=_tao_bac_local(ho_so_chon),
        so_model_nap_cung_luc=ho_so_chon["so_model_nap_cung_luc"],
        chuoi_dam_may=_tao_chuoi_dam_may_da_xac_thuc(chuoi_dam_may_raw, bien_gop),
        che_do_dinh_tuyen=cai_dat_env.che_do_dinh_tuyen,
        cai_dat_chung=CauHinhCaiDatChung(**du_lieu_yaml.get("cai_dat_chung", {})),
        bo_chay=CauHinhBoChay(**bo_chay_dict),
        ho_so_gpu=ho_so_dict,
        ho_so_gpu_dang_chon=cai_dat_env.ho_so_gpu,
        dung_luong_vram_gb=int(ho_so_chon.get("dung_luong_vram_gb", 8)),
        local_chung=CauHinhLocalChung(**du_lieu_yaml.get("local_chung", {})),
        database_url=database_url,
        moi_truong=cai_dat_env.moi_truong,
        ngan_sach_ngay_usd=cai_dat_env.ngan_sach_ngay_usd,
        so_luong_dong_thoi=cai_dat_env.so_luong_dong_thoi or ho_so_chon["num_parallel"],
        do_dai_hang_doi_toi_da=cai_dat_env.do_dai_hang_doi_toi_da,
        timeout_giay=cai_dat_env.timeout_giay,
        ghi_noi_dung=cai_dat_env.ghi_noi_dung,
        xac_thuc_gia=cai_dat_env.xac_thuc_gia,
        app_secret=cai_dat_env.app_secret,
        cors_origins=[s.strip() for s in cai_dat_env.cors_origins.split(",") if s.strip()],
        han_muc_ip_phut=cai_dat_env.han_muc_ip_phut,
        han_muc_moi_nguoi_gio=cai_dat_env.han_muc_moi_nguoi_gio,
        he_so_bac_pro=cai_dat_env.he_so_bac_pro,
        han_muc_token_ngay=cai_dat_env.han_muc_token_ngay,
        han_muc_chi_phi_ngay_free_usd=cai_dat_env.han_muc_chi_phi_ngay_free_usd,
        han_muc_chi_phi_ngay_pro_usd=cai_dat_env.han_muc_chi_phi_ngay_pro_usd,
    )


# Khởi tạo đối tượng cấu hình dùng chung toàn hệ thống
cau_hinh = nap_cau_hinh()
