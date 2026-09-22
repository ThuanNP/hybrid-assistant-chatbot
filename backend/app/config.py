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

# Danh sách hồ sơ GPU hợp lệ và chế độ định tuyến hợp lệ
CAC_HO_SO_GPU_HOP_LE = {"gpu6", "gpu8", "gpu12", "gpu16", "gpu24"}
CAC_CHE_DO_DINH_TUYEN_HOP_LE = {"chi_local", "local_truoc", "dam_may_truoc"}


class CauHinhBacLocal(BaseModel):
    """Cấu hình cho một bậc mô hình local (chính hoặc nhỏ)."""

    bac: str
    model: str
    num_ctx: int

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.model == other
        return super().__eq__(other)


class CauHinhTangDamMay(BaseModel):
    """Cấu hình cho một tầng mô hình đám mây trong chuỗi định tuyến."""

    tang: int
    ten: str
    model: str
    api_key_env: str
    gia_vao_usd_moi_trieu: float
    gia_ra_usd_moi_trieu: float
    timeout_giay: int = 90
    cua_so_ngu_canh: int | None = None
    tham_so_them: dict[str, Any] = Field(default_factory=dict)
    ghi_chu: str | None = None
    kha_dung: bool = True

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class CauHinhBoChay(BaseModel):
    """Cấu hình bộ chạy mô hình local (Ollama hoặc LM Studio)."""

    loai: str
    dia_chi: str
    timeout_giay: int = 120

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class CauHinhLocalChung(BaseModel):
    """Cấu hình chung cho các mô hình chạy local."""

    keep_alive: str = "30m"
    nhiet_do: float = 0.3
    nguong_hang_doi_ha_cap: int = 3

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class CauHinhCaiDatChung(BaseModel):
    """Cài đặt chung cho chuỗi định tuyến và gọi mô hình."""

    so_lan_thu_lai_moi_tang: int = 2
    giay_gian_cach_dau: float = 0.5
    gioi_han_token_ra: int = 1024
    ngu_canh_du_phong_token: int = 512

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class CaiDatMoiTruong(BaseSettings):
    """Lớp đọc và kiểm tra các biến môi trường từ .env và hệ thống."""

    moi_truong: str = "dev"
    che_do_dinh_tuyen: str = "local_truoc"
    loai_bo_chay: str = "ollama"
    dia_chi_bo_chay: str = "http://localhost:11434/v1"
    ho_so_gpu: str = "gpu8"

    # Tuyệt đối không đặt giá trị mặc định cho khoá API
    google_api_key: str | None = None
    openrouter_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hybrid_assistant"
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    app_secret: str = "dev_secret_key"
    cors_origins: str = "http://localhost:4200,http://localhost:8080"
    ngan_sach_ngay_usd: float = 10.0
    so_luong_dong_thoi: int = 5
    do_dai_hang_doi_toi_da: int = 50
    timeout_giay: int = 60
    ghi_noi_dung: bool = False
    xac_thuc_gia: bool = True

    model_config = SettingsConfigDict(
        env_file=DUONG_DAN_ENV_MAC_DINH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CauHinhHeThong(BaseModel):
    """Đối tượng cấu hình hoàn chỉnh phơi ra cho toàn bộ ứng dụng."""

    # 5 thuộc tính bắt buộc theo đặc tả
    bac_local: list[CauHinhBacLocal]
    so_model_nap_cung_luc: int
    chuoi_dam_may: list[CauHinhTangDamMay]
    che_do_dinh_tuyen: str
    cai_dat_chung: CauHinhCaiDatChung

    # Các thuộc tính bổ trợ
    bo_chay: CauHinhBoChay
    ho_so_gpu: dict[str, Any]
    ho_so_gpu_dang_chon: str
    local_chung: CauHinhLocalChung
    database_url: str
    moi_truong: str
    ngan_sach_ngay_usd: float
    so_luong_dong_thoi: int
    do_dai_hang_doi_toi_da: int
    timeout_giay: int
    ghi_noi_dung: bool
    xac_thuc_gia: bool
    app_secret: str
    cors_origins: list[str]


def _doc_bien_gop(duong_dan_env: Path | None) -> dict[str, str]:
    """Gộp biến từ .env và os.environ, trong đó os.environ có mức ưu tiên cao hơn."""
    bien_gop: dict[str, str] = {}
    if duong_dan_env and duong_dan_env.exists():
        cac_bien_file = dotenv.dotenv_values(duong_dan_env)
        for khoa, gia_tri in cac_bien_file.items():
            if gia_tri is not None:
                bien_gop[khoa] = gia_tri
    for khoa, gia_tri in os.environ.items():
        bien_gop[khoa] = gia_tri
    return bien_gop


def _kiem_tra_phan_giai_host(host: str) -> bool:
    """Kiểm tra xem tên miền máy chủ có phân giải được qua DNS hay không."""
    try:
        socket.gethostbyname(host)
        return True
    except (socket.gaierror, OSError):
        return False


def _dieu_chinh_dia_chi_ngoai_container(
    dia_chi_bo_chay: str,
    database_url: str,
    dang_trong_container: bool,
) -> tuple[str, str]:
    """Tự động điều chỉnh máy chủ về localhost khi chạy ngoài môi trường container."""
    if dang_trong_container:
        return dia_chi_bo_chay, database_url

    dia_chi_moi = dia_chi_bo_chay
    if "host.docker.internal" in dia_chi_bo_chay:
        if not _kiem_tra_phan_giai_host("host.docker.internal"):
            dia_chi_moi = dia_chi_bo_chay.replace("host.docker.internal", "localhost")
            logger.info(
                "Chạy ngoài container và không phân giải được host.docker.internal, "
                "tự động chuyển dia_chi_bo_chay sang localhost"
            )

    database_url_moi = database_url
    if re.search(r"@db(?=[:/])", database_url):
        database_url_moi = re.sub(r"@db(?=[:/])", "@localhost", database_url)
        logger.info(
            "Chạy ngoài container, tự động chuyển DATABASE_URL từ máy chủ 'db' sang localhost"
        )

    return dia_chi_moi, database_url_moi


def _kiem_tra_the_model_local(the_model: str) -> bool:
    """Kiểm tra thẻ model local có đủ dấu hai chấm và định danh lượng tử hoá."""
    if ":" not in the_model:
        return False
    _, phan_tag = the_model.split(":", 1)
    if "-" not in phan_tag:
        return False
    phan_luong_tu = phan_tag.rsplit("-", 1)[1].lower()
    return bool(re.match(r"^(?:q\d+[_\w]*|fp\d+|bf\d+)$", phan_luong_tu))


def _kiem_tra_tinh_hop_le_ho_so_gpu(
    ho_so_dict: dict[str, Any],
    ho_so_chon: str,
) -> None:
    """Kiểm tra tính hợp lệ của toàn bộ hồ sơ GPU và hồ sơ đang chọn."""
    if ho_so_chon not in ho_so_dict or ho_so_chon not in CAC_HO_SO_GPU_HOP_LE:
        danh_sach = ", ".join(sorted(ho_so_dict.keys(), key=lambda x: int(x.replace("gpu", ""))))
        raise ValueError(
            f"HO_SO_GPU không hợp lệ: '{ho_so_chon}'. Phải là một trong năm khoá đã khai báo: {danh_sach}"
        )

    vi_du = "q" + "wen3.5:9b-q4_K_M"
    for ten_hs, hs in ho_so_dict.items():
        chinh = hs.get("chinh", {})
        nho = hs.get("nho", {})
        the_chinh = chinh.get("model", "")
        the_nho = nho.get("model", "")

        if not _kiem_tra_the_model_local(the_chinh) or not _kiem_tra_the_model_local(the_nho):
            raise ValueError(f"thẻ model phải ghi đầy đủ, ví dụ {vi_du}")

        num_ctx_chinh = chinh.get("num_ctx", 0)
        num_ctx_nho = nho.get("num_ctx", 0)
        if num_ctx_nho > num_ctx_chinh:
            raise ValueError("num_ctx của bậc nho phải nhỏ hơn hoặc bằng bậc chinh")

        so_model = hs.get("so_model_nap_cung_luc", 0)
        if so_model not in (1, 2):
            raise ValueError(f"so_model_nap_cung_luc của hồ sơ '{ten_hs}' phải là 1 hoặc 2")


def _kiem_tra_chuoi_dam_may(chuoi_dam_may: list[dict[str, Any]]) -> None:
    """Kiểm tra chuỗi đám mây có số tầng tăng dần nghiêm ngặt và không trùng."""
    danh_sach_tang = [t.get("tang", 0) for t in chuoi_dam_may]
    if len(danh_sach_tang) != len(set(danh_sach_tang)):
        raise ValueError("chuoi_dam_may có tầng bị trùng lặp")
    for i in range(len(danh_sach_tang) - 1):
        if danh_sach_tang[i] >= danh_sach_tang[i + 1]:
            raise ValueError("chuoi_dam_may phải có số tầng tăng dần")


def _kiem_tra_che_do_dinh_tuyen(che_do: str) -> None:
    """Kiểm tra chế độ định tuyến có nằm trong danh sách cho phép."""
    if che_do not in CAC_CHE_DO_DINH_TUYEN_HOP_LE:
        danh_sach = ", ".join(sorted(CAC_CHE_DO_DINH_TUYEN_HOP_LE))
        raise ValueError(
            f"CHE_DO_DINH_TUYEN không hợp lệ: '{che_do}'. Phải là một trong: {danh_sach}"
        )


def _tao_chuoi_dam_may_da_xac_thuc(
    danh_sach_raw: list[dict[str, Any]],
    bien_gop: dict[str, str],
) -> list[CauHinhTangDamMay]:
    """Chuyển đổi danh sách tầng đám mây và xác định tính khả dụng của từng tầng."""
    ket_qua: list[CauHinhTangDamMay] = []
    for muc in danh_sach_raw:
        tang_obj = CauHinhTangDamMay(**muc)
        ten_bien_khoa = tang_obj.api_key_env
        gia_tri_khoa = bien_gop.get(ten_bien_khoa)

        # Kiểm tra thiếu khoá hoặc còn giữ giá trị mẫu giả
        if not gia_tri_khoa or not gia_tri_khoa.strip() or gia_tri_khoa == "dan-khoa-that-vao-day":
            tang_obj.kha_dung = False
            logger.info(
                "Tầng %s (%s) thiếu khoá API '%s', đánh dấu không khả dụng (kha_dung=False)",
                tang_obj.tang,
                tang_obj.ten,
                ten_bien_khoa,
            )
        else:
            tang_obj.kha_dung = True
        ket_qua.append(tang_obj)
    return ket_qua


def nap_cau_hinh(
    duong_dan_env: Path | None = None,
    duong_dan_yaml: Path | None = None,
) -> CauHinhHeThong:
    """Nạp, thay thế biến, xác thực toàn bộ cấu hình hệ thống và trả về CauHinhHeThong."""
    env_path = duong_dan_env or DUONG_DAN_ENV_MAC_DINH
    yaml_path = duong_dan_yaml or DUONG_DAN_MODELS_YAML_MAC_DINH

    bien_gop = _doc_bien_gop(env_path)

    # Đọc cấu hình YAML và thay thế các biến ${BIEN}
    with open(yaml_path, "r", encoding="utf-8") as f:
        noi_dung_yaml_tho = f.read()

    def _thay_the_bien(khop: re.Match[str]) -> str:
        ten_bien = khop.group(1)
        return bien_gop.get(ten_bien, "")

    noi_dung_yaml_da_thay = re.sub(r"\$\{([A-Za-z0-9_]+)\}", _thay_the_bien, noi_dung_yaml_tho)
    du_lieu_yaml = yaml.safe_load(noi_dung_yaml_da_thay) or {}

    # Đọc cài đặt môi trường
    cai_dat_env = CaiDatMoiTruong()
    che_do_dinh_tuyen = bien_gop.get("CHE_DO_DINH_TUYEN", cai_dat_env.che_do_dinh_tuyen)
    ho_so_gpu_chon = bien_gop.get("HO_SO_GPU", cai_dat_env.ho_so_gpu)
    database_url = bien_gop.get("DATABASE_URL", cai_dat_env.database_url)

    # Xác thực các ràng buộc cấu hình
    _kiem_tra_che_do_dinh_tuyen(che_do_dinh_tuyen)
    ho_so_dict = du_lieu_yaml.get("ho_so_gpu", {})
    _kiem_tra_tinh_hop_le_ho_so_gpu(ho_so_dict, ho_so_gpu_chon)
    chuoi_dam_may_raw = du_lieu_yaml.get("chuoi_dam_may", [])
    _kiem_tra_chuoi_dam_may(chuoi_dam_may_raw)

    # Điều chỉnh ngoài container nếu cần
    dang_trong_container = os.path.exists("/.dockerenv")
    bo_chay_dict = du_lieu_yaml.get("bo_chay", {})
    dia_chi_bo_chay_tho = bo_chay_dict.get("dia_chi", cai_dat_env.dia_chi_bo_chay)
    dia_chi_bo_chay, database_url_dieu_chinh = _dieu_chinh_dia_chi_ngoai_container(
        dia_chi_bo_chay_tho,
        database_url,
        dang_trong_container,
    )
    bo_chay_dict["dia_chi"] = dia_chi_bo_chay

    # Trích xuất 2 bậc local của hồ sơ GPU được chọn
    hs_hien_tai = ho_so_dict[ho_so_gpu_chon]
    bac_local = [
        CauHinhBacLocal(
            bac="chinh",
            model=hs_hien_tai["chinh"]["model"],
            num_ctx=hs_hien_tai["chinh"]["num_ctx"],
        ),
        CauHinhBacLocal(
            bac="nho",
            model=hs_hien_tai["nho"]["model"],
            num_ctx=hs_hien_tai["nho"]["num_ctx"],
        ),
    ]

    chuoi_dam_may = _tao_chuoi_dam_may_da_xac_thuc(chuoi_dam_may_raw, bien_gop)

    cai_dat_chung = CauHinhCaiDatChung(**du_lieu_yaml.get("cai_dat_chung", {}))
    bo_chay = CauHinhBoChay(**bo_chay_dict)
    local_chung = CauHinhLocalChung(**du_lieu_yaml.get("local_chung", {}))

    return CauHinhHeThong(
        bac_local=bac_local,
        so_model_nap_cung_luc=hs_hien_tai["so_model_nap_cung_luc"],
        chuoi_dam_may=chuoi_dam_may,
        che_do_dinh_tuyen=che_do_dinh_tuyen,
        cai_dat_chung=cai_dat_chung,
        bo_chay=bo_chay,
        ho_so_gpu=ho_so_dict,
        ho_so_gpu_dang_chon=ho_so_gpu_chon,
        local_chung=local_chung,
        database_url=database_url_dieu_chinh,
        moi_truong=cai_dat_env.moi_truong,
        ngan_sach_ngay_usd=cai_dat_env.ngan_sach_ngay_usd,
        so_luong_dong_thoi=cai_dat_env.so_luong_dong_thoi,
        do_dai_hang_doi_toi_da=cai_dat_env.do_dai_hang_doi_toi_da,
        timeout_giay=cai_dat_env.timeout_giay,
        ghi_noi_dung=cai_dat_env.ghi_noi_dung,
        xac_thuc_gia=cai_dat_env.xac_thuc_gia,
        app_secret=cai_dat_env.app_secret,
        cors_origins=[s.strip() for s in cai_dat_env.cors_origins.split(",") if s.strip()],
    )


# Khởi tạo đối tượng cấu hình dùng chung toàn hệ thống
cau_hinh = nap_cau_hinh()
