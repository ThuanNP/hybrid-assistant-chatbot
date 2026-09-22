"""Xử lý và xây dựng ngữ cảnh hội thoại gửi tới mô hình.

Mô-đun chịu trách nhiệm:
1. Đọc và bảo toàn lời nhắc hệ thống từ prompts/he_thong.md.
2. Tính toán ngân sách token an toàn theo cửa sổ nhỏ nhất của chuỗi định tuyến.
3. Cắt tỉa lịch sử hội thoại theo cặp câu hỏi - đáp để vừa ngân sách.
4. Đánh dấu và thông báo khi ngữ cảnh bị cắt tỉa.
5. Ném ngoại lệ có cấu trúc LoiNguCanhQuaDai khi tin nhắn mới vượt ngân sách.
"""

from pathlib import Path
from typing import Any, NamedTuple

from app.config import CauHinhHeThong, cau_hinh as cau_hinh_mac_dinh
from app.core.loi import LoiNguCanhQuaDai, NGU_CANH_QUA_DAI
from app.llm.chinh_sach import Tang
from app.llm.dem_token import dem_token

# Đường dẫn mặc định tới tệp lời nhắc hệ thống
_DUONG_DAN_PROMPT_MAC_DINH = Path(__file__).resolve().parents[3] / "prompts" / "he_thong.md"

# Dòng đánh dấu chèn vào đầu phần hội thoại khi có cắt tỉa
THONG_BAO_CAT_NGU_CANH = "Phần đầu cuộc trò chuyện đã được lược bớt để vừa cửa sổ ngữ cảnh."

# Ước lượng số token trung bình cho một lượt hội thoại (1 câu hỏi + 1 câu đáp)
SO_TOKEN_TRUNG_BINH_MOI_LUOT = 500


class KetQuaNguCanh(NamedTuple):
    """Kết quả xây dựng ngữ cảnh gồm danh sách tin nhắn và chỉ số cắt tỉa."""

    danh_sach: list[dict[str, str]]
    da_cat: bool
    so_luot_bi_cat: int


def doc_loi_nhac_he_thong(duong_dan_prompts: Path | None = None) -> str:
    """Đọc nội dung lời nhắc hệ thống từ tệp Markdown hướng dẫn."""
    duong_dan = duong_dan_prompts or _DUONG_DAN_PROMPT_MAC_DINH
    if not duong_dan.exists():
        return (
            "Bạn là Trợ lý nội bộ của Doanh nghiệp kinh doanh điện năng, "
            "hỗ trợ cán bộ công nhân viên tra cứu và xử lý nghiệp vụ điện."
        )
    return duong_dan.read_text(encoding="utf-8").strip()


def _lay_cua_so_tang(t: Tang, cfg: CauHinhHeThong) -> int:
    """Xác định kích thước cửa sổ ngữ cảnh của một tầng mô hình.

    Tầng 0 (local): bắt buộc lấy num_ctx của bậc NHO (bậc nhỏ nhất có thể phục vụ).
    Tầng đám mây: lấy cua_so_ngu_canh cấu hình trong models.yaml.
    """
    if t.so == 0 or t.nguon == "local":
        for b in cfg.bac_local:
            if b.bac == "nho":
                return b.num_ctx
        return min((b.num_ctx for b in cfg.bac_local), default=4096)

    if t.cua_so_ngu_canh > 0:
        return t.cua_so_ngu_canh

    for dm in cfg.chuoi_dam_may:
        if dm.tang == t.so:
            return dm.cua_so_ngu_canh
    return 128000


def tinh_ngan_sach_token(
    chuoi: list[Tang],
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> int:
    """Tính ngân sách token an toàn cho một chuỗi các tầng mô hình.

    Ngân sách = (min(cửa sổ mọi tầng) - gioi_han_token_ra - ngu_canh_du_phong_token) / he_so_an_toan.
    Chuỗi [0, 1, 2, 3, 4] có ngân sách đúng bằng ngân sách của bậc nho local.
    """
    cfg = cau_hinh_he_thong or cau_hinh_mac_dinh
    if not chuoi:
        cua_so_min = min((b.num_ctx for b in cfg.bac_local), default=4096)
    else:
        cua_so_min = min(_lay_cua_so_tang(t, cfg) for t in chuoi)

    ngan_sach_tho = (
        cua_so_min
        - cfg.cai_dat_chung.gioi_han_token_ra
        - cfg.cai_dat_chung.ngu_canh_du_phong_token
    )
    he_so = cfg.cai_dat_chung.he_so_an_toan_token
    return max(0, int(ngan_sach_tho / max(he_so, 1.0)))


def _chuan_hoa_tin_nhan(tin_nhan: Any, vai_tro_mac_dinh: str = "user") -> dict[str, str]:
    """Chuyển đổi một đối tượng tin nhắn bất kỳ về cấu trúc chuẩn dict[role, content]."""
    if isinstance(tin_nhan, str):
        return {"role": vai_tro_mac_dinh, "content": tin_nhan}
    if isinstance(tin_nhan, dict):
        vai_tro = str(tin_nhan.get("role") or tin_nhan.get("vai_tro") or vai_tro_mac_dinh)
        noi_dung = str(
            tin_nhan.get("content")
            or tin_nhan.get("noi_dung")
            or tin_nhan.get("text")
            or ""
        )
        return {"role": vai_tro, "content": noi_dung}

    vai_tro = str(getattr(tin_nhan, "role", getattr(tin_nhan, "vai_tro", vai_tro_mac_dinh)))
    noi_dung = str(getattr(tin_nhan, "content", getattr(tin_nhan, "noi_dung", "")))
    return {"role": vai_tro, "content": noi_dung}


def _gom_cac_cap_lich_su(
    lich_su: list[Any] | None,
) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Gom danh sách lịch sử thành các cặp hoàn chỉnh (1 lượt hỏi user + 1 lượt đáp assistant)."""
    if not lich_su:
        return []

    danh_sach_chuan: list[dict[str, str]] = []
    for tin in lich_su:
        tin_chuan = _chuan_hoa_tin_nhan(tin)
        if tin_chuan["content"]:
            danh_sach_chuan.append(tin_chuan)

    cac_cap: list[tuple[dict[str, str], dict[str, str]]] = []
    i = 0
    while i < len(danh_sach_chuan) - 1:
        cac_cap.append((danh_sach_chuan[i], danh_sach_chuan[i + 1]))
        i += 2
    return cac_cap


def dung_ngu_canh(
    lich_su: list[Any] | None,
    tin_nhan_moi: Any,
    chuoi: list[Tang],
    *,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    loi_nhac_he_thong: str | None = None,
    ma_yeu_cau: str = "",
) -> KetQuaNguCanh:
    """Xây dựng danh sách tin nhắn gửi tới mô hình, tuân thủ các quy tắc cắt tỉa:

    a) Lời nhắc hệ thống đọc từ prompts/he_thong.md LUÔN giữ.
    b) Tin nhắn mới nhất của người dùng LUÔN giữ.
    c) Lấy các lượt gần nhất đi ngược về quá khứ cho tới khi đạt ngân sách, cắt theo CẶP.
    d) Nếu đã cắt, chèn một dòng đánh dấu vào đầu phần hội thoại giữ lại.
    e) Nếu riêng lời nhắc hệ thống cộng tin nhắn mới vượt ngân sách: ném LoiNguCanhQuaDai.
    """
    cfg = cau_hinh_he_thong or cau_hinh_mac_dinh
    ngan_sach = tinh_ngan_sach_token(chuoi, cfg)

    # Quy tắc a: Lời nhắc hệ thống
    noi_dung_he_thong = (
        loi_nhac_he_thong
        if loi_nhac_he_thong is not None
        else doc_loi_nhac_he_thong()
    )
    tin_he_thong = {"role": "system", "content": noi_dung_he_thong}
    token_he_thong = dem_token(noi_dung_he_thong)

    # Quy tắc b: Tin nhắn mới nhất của người dùng
    tin_moi = _chuan_hoa_tin_nhan(tin_nhan_moi, vai_tro_mac_dinh="user")
    token_moi = dem_token(tin_moi["content"])

    # Quy tắc e: Kiểm tra riêng lời nhắc hệ thống + tin nhắn mới
    token_bat_buoc = token_he_thong + token_moi
    if token_bat_buoc > ngan_sach:
        raise LoiNguCanhQuaDai(
            f"Tin nhắn mới ({token_moi} token) kết hợp lời nhắc hệ thống ({token_he_thong} token) "
            f"đã vượt quá ngân sách ngữ cảnh cho phép ({ngan_sach} token).",
            ma_yeu_cau=ma_yeu_cau,
            so_token=token_bat_buoc,
            ngan_sach=ngan_sach,
        )

    cac_cap = _gom_cac_cap_lich_su(lich_su)
    if not cac_cap:
        return KetQuaNguCanh(danh_sach=[tin_he_thong, tin_moi], da_cat=False, so_luot_bi_cat=0)

    # Tính token của tất cả các cặp lịch sử
    token_cac_cap: list[int] = [
        dem_token(cap[0]["content"]) + dem_token(cap[1]["content"])
        for cap in cac_cap
    ]
    tong_token_lich_su = sum(token_cac_cap)

    # Kiểm tra nếu toàn bộ lịch sử vừa ngân sách
    if token_bat_buoc + tong_token_lich_su <= ngan_sach:
        danh_sach_giu: list[dict[str, str]] = [tin_he_thong]
        for cap in cac_cap:
            danh_sach_giu.extend([cap[0], cap[1]])
        danh_sach_giu.append(tin_moi)
        return KetQuaNguCanh(danh_sach=danh_sach_giu, da_cat=False, so_luot_bi_cat=0)

    # Quy tắc c & d: Cắt tỉa theo cặp đi ngược về quá khứ và chèn thông báo đánh dấu
    tin_thong_bao = {"role": "system", "content": THONG_BAO_CAT_NGU_CANH}
    token_thong_bao = dem_token(THONG_BAO_CAT_NGU_CANH)
    ngan_sach_con_lai = ngan_sach - token_bat_buoc - token_thong_bao

    cac_cap_giu_lai: list[tuple[dict[str, str], dict[str, str]]] = []
    for cap, t_cap in zip(reversed(cac_cap), reversed(token_cac_cap)):
        if t_cap <= ngan_sach_con_lai:
            cac_cap_giu_lai.append(cap)
            ngan_sach_con_lai -= t_cap
        else:
            break

    cac_cap_giu_lai.reverse()
    so_luot_bi_cat = len(cac_cap) - len(cac_cap_giu_lai)

    danh_sach_ket_qua: list[dict[str, str]] = [tin_he_thong, tin_thong_bao]
    for cap in cac_cap_giu_lai:
        danh_sach_ket_qua.extend([cap[0], cap[1]])
    danh_sach_ket_qua.append(tin_moi)

    return KetQuaNguCanh(
        danh_sach=danh_sach_ket_qua,
        da_cat=True,
        so_luot_bi_cat=so_luot_bi_cat,
    )


def uoc_luong_so_luot_giu_duoc(
    chuoi: list[Tang],
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> int:
    """Trả số lượt trung bình giữ được trong ngữ cảnh, phục vụ endpoint /ngu-canh/tinh-trang."""
    cfg = cau_hinh_he_thong or cau_hinh_mac_dinh
    ngan_sach = tinh_ngan_sach_token(chuoi, cfg)
    token_he_thong = dem_token(doc_loi_nhac_he_thong())
    ngan_sach_hoi_thoai = max(0, ngan_sach - token_he_thong)
    return max(0, int(ngan_sach_hoi_thoai / SO_TOKEN_TRUNG_BINH_MOI_LUOT))
