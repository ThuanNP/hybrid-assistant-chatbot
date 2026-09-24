"""Định tuyến các lời gọi mô hình qua chuỗi local và đám mây.

Mọi lời gọi model trong ứng dụng bắt buộc đi qua đúng một cửa tại mô-đun này:
- goi_mo_hinh(): gọi hoàn thành hội thoại một lần (POST /chat, tích hợp M2M).
- goi_mo_hinh_theo_dong(): phát câu trả lời theo dòng (SSE).
- goi_nhung(): gọi tạo vector nhúng từ danh sách văn bản (Giai đoạn 6).

Tuân thủ tuyệt đối Quy tắc 1, 2 và Quy tắc kỹ thuật 7 trong AGENTS.md.

QUY TẮC MỘT MODEL NHÚNG CHO MỖI CHỈ MỤC:
Tài liệu gốc từng đề xuất để lời gọi nhúng rơi từ Gemini sang OpenAI khi tầng 1 lỗi.
KHÔNG làm như vậy: hai model nhúng khác nhau sinh hai không gian vector khác nhau
(thường khác cả số chiều); câu hỏi nhúng bằng model B khi so với đoạn nhúng bằng
model A cho điểm cosine vô nghĩa, truy hồi sai mà không có dấu hiệu nhận biết.
Vì vậy:
- goi_nhung KHÔNG có chuỗi rơi tầng sang nhà cung cấp khác.
- Mỗi tai_lieu lưu model_nhung; truy hồi chỉ so với đoạn có cùng model_nhung với câu hỏi.
- Đổi model nhúng = nạp lại TOÀN BỘ kho bằng scripts/nap_tai_lieu.py --nhung-lai, có thanh tiến độ.
- Model nhúng lỗi -> đặt cờ che_do_truy_hoi = "chi_tu_khoa" và lùi về BM25
  (suy giảm có kiểm soát mức 2 của Module 2).

LỰA CHỌN MẶC ĐỊNH CHẠY LOCAL CHO NHÚNG:
Nhúng mặc định chạy LOCAL (bge-m3 qua Ollama) bất kể CHE_DO_DINH_TUYEN,
vì nội dung tài liệu nội bộ không được rời hạ tầng.
"""

import argparse
import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from app.config import CauHinhHeThong, CauHinhTangDamMay, cau_hinh
from app.core.loi import (
    LoiDauVao,
    LoiHangDoiDay,
    LoiHetBacLocal,
    LoiHetChuoiDuPhong,
    LoiTamThoi,
    LoiVinhVien,
    LoiVuotNganSach,
)
from app.core.xac_thuc import NguoiDung
from app.hang_doi.dieu_phoi import DieuPhoi, dieu_phoi_mac_dinh
from app.llm.bo_chay_local import (
    BoChay,
    KetQuaDongLocal,
    KetQuaGoiLocal,
    KetQuaNhungLocal,
    goi_local,
    lay_bo_chay,
)
from app.llm.chi_phi import (
    KhoLuotGoi,
    LuotGoi,
    chuan_hoa_muc_dich,
    kho_luot_goi_mac_dinh,
    kiem_tra_canh_bao_ty_le_roi_tang,
    kiem_tra_ngan_sach,
    uoc_tinh_chi_phi,
)
from app.llm.chinh_sach import (
    NhanDuLieu,
    Tang,
    xac_dinh_chuoi,
)
from app.llm.nha_cung_cap_dam_may import (
    KetQuaDongDamMay,
    KetQuaGoiDamMay,
    goi_dam_may,
)

logger = logging.getLogger(__name__)

__all__ = [
    "KetQuaGoi",
    "KetQuaNhung",
    "ManhPhatRa",
    "goi_mo_hinh",
    "goi_mo_hinh_theo_dong",
    "goi_nhung",
    "lay_the_nhung_theo_ho_so",
]


class KetQuaNhung(BaseModel):
    """Kết quả hoàn chỉnh của một lượt gọi tạo vector nhúng."""

    vectors: list[list[float]]
    model: str
    so_chieu: int
    do_tre_ms: float
    token_vao: int


class KetQuaGoi(BaseModel):
    """Kết quả hoàn chỉnh của một lượt gọi mô hình LLM."""

    noi_dung: str
    nguon: Literal["local", "dam_may"] | str
    tang: int
    bac_local: str | None = None
    ten_model: str
    token_vao: int = 0
    token_ra: int = 0
    chi_phi_usd: float = 0.0
    do_tre_ms: float = 0.0
    thoi_gian_nap_ms: float = 0.0
    toc_do_tok_s: float = 0.0
    do_dai_hang_doi: int = 0
    so_lan_thu: int = 1
    danh_sach_tang_da_hong: list[int] = Field(default_factory=list)
    da_cat_ngu_canh: bool = False
    so_luot_bi_cat: int = 0
    ly_do_chuoi: str = ""
    # True khi tầng phục vụ khác tầng đầu của chuỗi thực tế hoặc do bậc nho trả lời
    ha_cap: bool = False


# Khoá tuỳ chọn chỉ dùng nội bộ router, không được chuyển sang litellm
_KHOA_NOI_BO = frozenset({
    "bo_chay",
    "cau_hinh_he_thong",
    "cau_hinh_cs",
    "do_dai_hang_doi",
    "dieu_phoi",
    "kho_luot_goi",
    "uu_tien_bac_nho",
    "da_cat_ngu_canh",
    "so_luot_bi_cat",
    "luon_vao_hang",
    "muc_dich",
    "ep_tang",
    "bac_ep",
})


class ManhPhatRa(BaseModel):
    """Mảnh dữ liệu phát theo dòng (SSE) trả về cho người dùng."""

    loai: Literal["bat_dau", "manh", "xong", "loi", "hang_doi"]
    noi_dung: str = ""
    ket_qua: KetQuaGoi | None = None
    vi_tri: int | None = None
    uoc_luong_giay: float | None = None
    nguon: Literal["local", "dam_may"] | str | None = None
    tang: int | None = None
    bac_local: str | None = None
    ten_model: str | None = None
    da_cat_ngu_canh: bool = False
    so_luot_bi_cat: int = 0


def _tinh_toc_do(so_token: int, thoi_gian_giay: float) -> float:
    """Tính tốc độ sinh token (tok/s), tránh chia cho 0."""
    return round(so_token / max(thoi_gian_giay, 0.001), 2) if so_token > 0 else 0.0


def _doc_cau_tra_loi_khi_ban() -> str:
    """Đọc câu trả lời có kiểm soát khi hệ thống bận từ prompts/he_thong.md."""
    cau_mac_dinh = (
        "Hệ thống trợ lý AI nội bộ hiện đang bận hoặc gặp sự cố kết nối. "
        "Anh/Chị vui lòng thử lại sau ít phút."
    )
    duong_dan = Path(__file__).resolve().parents[3] / "prompts" / "he_thong.md"
    if not duong_dan.exists():
        return cau_mac_dinh
    try:
        noi_dung = duong_dan.read_text(encoding="utf-8")
        khop = re.search(r"##\s+tra_loi_khi_ban\s*\n+([^#\n<]+(?:\n+[^#\n<]+)*)", noi_dung)
        if khop:
            cau = " ".join(line.strip() for line in khop.group(1).splitlines() if line.strip())
            if cau:
                return cau
    except Exception as err:
        logger.warning("Không thể đọc mục tra_loi_khi_ban từ %s: %s", duong_dan, err)
    return cau_mac_dinh


def _ghi_nhat_ky(kq: KetQuaGoi, ma_yeu_cau: str) -> None:
    """Ghi nhật ký lượt gọi theo quy tắc kỹ thuật 7, không ghi nội dung tin nhắn."""
    logger.info(
        "[%s] Lượt gọi mô hình hoàn thành: nguồn=%s, tầng=%d, bậc=%s, "
        "model=%s, token_vào=%d, token_ra=%d, chi_phí_usd=%.6f, độ_trễ_ms=%.2f, "
        "thời_gian_nạp_ms=%.2f, tok/s=%.2f",
        ma_yeu_cau,
        kq.nguon,
        kq.tang,
        kq.bac_local or "khong_co",
        kq.ten_model,
        kq.token_vao,
        kq.token_ra,
        kq.chi_phi_usd,
        kq.do_tre_ms,
        kq.thoi_gian_nap_ms,
        kq.toc_do_tok_s,
    )


def _loai_loi(err: Exception) -> str:
    """Tên loại lỗi để lưu vào luot_goi; không dùng thông điệp vì có thể lẫn nội dung."""
    return type(err).__name__[:100]


def _luu_nhat_ky_va_kho(
    kq: KetQuaGoi,
    *,
    ma_yeu_cau: str,
    nguoi_id: str | int,
    kho: KhoLuotGoi,
    cfg: CauHinhHeThong,
    tang_dau: int | None,
    loai_loi_cac_tang: dict[int, str],
    muc_dich: str,
    thanh_cong: bool = True,
) -> None:
    """Đặt cờ ha_cap, ghi nhật ký và lưu bản ghi vào KhoLuotGoi theo Quy tắc kỹ thuật 7.

    Lượt hết chuỗi (thanh_cong=False) luôn tính là rơi tầng.
    """
    roi_tang = not thanh_cong or (tang_dau is not None and kq.tang != tang_dau)
    kq.ha_cap = roi_tang or kq.bac_local == "nho"
    _ghi_nhat_ky(kq, ma_yeu_cau)
    lg = LuotGoi(
        nguoi_id=str(nguoi_id),
        nguon=str(kq.nguon),
        tang=kq.tang,
        bac=kq.bac_local,
        model=kq.ten_model,
        token_vao=kq.token_vao,
        token_ra=kq.token_ra,
        chi_phi_usd=kq.chi_phi_usd,
        do_tre_ms=kq.do_tre_ms,
        thoi_gian_nap_ms=kq.thoi_gian_nap_ms,
        toc_do_tok_s=kq.toc_do_tok_s,
        thanh_cong=thanh_cong,
        ma_yeu_cau=ma_yeu_cau,
        roi_tang=roi_tang,
        ly_do_that_bai_tang_dau=(
            loai_loi_cac_tang.get(tang_dau) if roi_tang and tang_dau is not None else None
        ),
        muc_dich=chuan_hoa_muc_dich(muc_dich),
    )
    kho.ghi(lg)
    kiem_tra_canh_bao_ty_le_roi_tang(kho=kho, cfg=cfg)


def _tao_ket_qua_khi_ban(
    ma_yeu_cau: str,
    ly_do_chuoi: str,
    danh_sach_tang_da_hong: list[int],
) -> KetQuaGoi:
    """Tạo phản hồi có kiểm soát khi toàn bộ chuỗi local gặp sự cố."""
    cau_tra_loi = _doc_cau_tra_loi_khi_ban()
    return KetQuaGoi(
        noi_dung=cau_tra_loi,
        nguon="local",
        tang=0,
        bac_local=None,
        ten_model="khong_co",
        token_vao=0,
        token_ra=0,
        chi_phi_usd=0.0,
        do_tre_ms=0.0,
        thoi_gian_nap_ms=0.0,
        toc_do_tok_s=0.0,
        so_lan_thu=1,
        danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
        da_cat_ngu_canh=False,
        so_luot_bi_cat=0,
        ly_do_chuoi=ly_do_chuoi,
    )


def _tim_cau_hinh_tang_dam_may(cfg: CauHinhHeThong, t: Tang) -> CauHinhTangDamMay:
    """Tìm cấu hình tầng đám mây tương ứng trong cấu hình hệ thống."""
    for cdm in cfg.chuoi_dam_may:
        if cdm.tang == t.so:
            return cdm
    return CauHinhTangDamMay(
        tang=t.so,
        ten=t.ten,
        model=t.ten,
        api_key_env="",
        gia_vao_usd_moi_trieu=0.0,
        gia_ra_usd_moi_trieu=0.0,
        timeout_giay=cfg.timeout_giay,
        cua_so_ngu_canh=t.cua_so_ngu_canh,
    )


async def _thuc_hien_goi_local(
    tin_nhan: list[dict[str, Any]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> KetQuaGoiLocal:
    """Thực hiện gọi bộ chạy cục bộ tầng 0 dạng không phát dòng."""
    bo_chay = tuy_chon.get("bo_chay")
    temperature = tuy_chon.get("temperature")
    max_tokens = tuy_chon.get("max_tokens")
    uu_tien_bac_nho = bool(tuy_chon.get("uu_tien_bac_nho", False))
    bac_ep = tuy_chon.get("bac_ep")
    return await goi_local(
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        do_dai_hang_doi=do_dai_hang_doi,
        phat_theo_dong=False,
        bo_chay=bo_chay,
        cau_hinh_he_thong=cfg,
        temperature=temperature,
        max_tokens=max_tokens,
        uu_tien_bac_nho=uu_tien_bac_nho,
        bac_ep=bac_ep,
    )


async def _thuc_hien_goi_dam_may(
    tang_dm: CauHinhTangDamMay,
    tin_nhan: list[dict[str, Any]],
    *,
    ma_yeu_cau: str,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> KetQuaGoiDamMay:
    """Thực hiện gọi nhà cung cấp đám mây dạng không phát dòng."""
    cac_tham_so = {k: v for k, v in tuy_chon.items() if k not in _KHOA_NOI_BO}
    return await goi_dam_may(
        tang_dm,
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        phat_theo_dong=False,
        cau_hinh_he_thong=cfg,
        **cac_tham_so,
    )


async def goi_mo_hinh(
    tin_nhan: list[dict],
    *,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
    nhan_du_lieu: NhanDuLieu = NhanDuLieu.THUONG,
    uu_tien_bac_nho: bool = False,
    ep_tang: str | int | None = None,
    **tuy_chon: Any,
) -> KetQuaGoi:
    """Gọi mô hình LLM qua chuỗi định tuyến đã được xác thực chính sách.

    Điểm nhập duy nhất trong ứng dụng cho các lời gọi mô hình không phát dòng.
    Khi uu_tien_bac_nho=True: Chuỗi chỉ gồm tầng 0, không rơi sang đám mây.
    Khi ep_tang được truyền (chỉ dùng cho đánh giá/eval runner): ép chạy đúng tầng đó.
    """
    cfg: CauHinhHeThong = tuy_chon.get("cau_hinh_he_thong") or cau_hinh
    dp: DieuPhoi = tuy_chon.get("dieu_phoi") or dieu_phoi_mac_dinh
    kho: KhoLuotGoi = tuy_chon.get("kho_luot_goi") or kho_luot_goi_mac_dinh

    uu_tien_bac_nho_hieu_luc = bool(
        uu_tien_bac_nho or tuy_chon.get("uu_tien_bac_nho", False)
    )
    if uu_tien_bac_nho_hieu_luc:
        tuy_chon["uu_tien_bac_nho"] = True

    che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cfg.che_do_dinh_tuyen
    kq_chuoi = xac_dinh_chuoi(
        nguoi,
        nhan_du_lieu,
        che_do=che_do,
        cau_hinh_he_thong=cfg,
        cau_hinh_cs=tuy_chon.get("cau_hinh_cs"),
    )
    chuoi = kq_chuoi.chuoi
    if uu_tien_bac_nho_hieu_luc:
        # Chuỗi BẮT BUỘC chỉ gồm tầng 0, tuyệt đối không rơi sang đám mây
        chuoi = [t for t in chuoi if t.so == 0]
        if not chuoi:
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=4096, nguon="local")]

    ep_tang_hieu_luc = ep_tang if ep_tang is not None else tuy_chon.get("ep_tang")
    if ep_tang_hieu_luc is not None:
        if ep_tang_hieu_luc == "local1":
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=8192, nguon="local")]
            tuy_chon["bac_ep"] = "chinh"
        elif ep_tang_hieu_luc == "local2":
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=8192, nguon="local")]
            tuy_chon["bac_ep"] = "nho"
        elif str(ep_tang_hieu_luc) in ("1", "2", "3", "4"):
            tang_so = int(ep_tang_hieu_luc)
            if nhan_du_lieu == NhanDuLieu.NHAY_CAM or str(nhan_du_lieu).upper() == "NHAY_CAM":
                raise LoiDauVao(
                    f"Dữ liệu nhãn NHAY_CAM không được phép gửi tới tầng đám mây {tang_so} (Quy tắc 2)",
                    ma_yeu_cau=ma_yeu_cau,
                )
            tang_dm_cfg = next((cdm for cdm in cfg.chuoi_dam_may if cdm.tang == tang_so), None)
            if tang_dm_cfg is None:
                raise LoiDauVao(
                    f"Tầng đám mây {tang_so} không tồn tại trong cấu hình",
                    ma_yeu_cau=ma_yeu_cau,
                )
            chuoi = [Tang(so=tang_so, ten=tang_dm_cfg.ten, cua_so_ngu_canh=tang_dm_cfg.cua_so_ngu_canh, nguon="dam_may")]
        else:
            raise LoiDauVao(f"Giá trị ep_tang không hợp lệ: {ep_tang_hieu_luc}", ma_yeu_cau=ma_yeu_cau)

    tang_dau = chuoi[0].so if chuoi else None
    co_tang_dam_may = any(t.so > 0 for t in chuoi)
    muc_dich = str(tuy_chon.get("muc_dich", "chat"))

    danh_sach_tang_da_hong: list[int] = []
    ly_do_cac_tang: dict[int, str] = {}
    loai_loi_cac_tang: dict[int, str] = {}

    for t in chuoi:
        try:
            if t.so == 0:
                if dp.can_vao_hang() or bool(tuy_chon.get("luon_vao_hang")):
                    if dp.kiem_tra_hang_doi_day():
                        dp.ghi_nhan_tu_choi()
                        if co_tang_dam_may:
                            logger.warning(
                                "[%s] Hàng đợi local đầy (%d/%d), chuỗi có đám mây -> chuyển tầng sau",
                                ma_yeu_cau,
                                dp.dang_cho,
                                dp.do_dai_hang_doi_toi_da,
                            )
                            danh_sach_tang_da_hong.append(0)
                            ly_do_cac_tang[0] = "HANG_DOI_DAY"
                            loai_loi_cac_tang[0] = "HANG_DOI_DAY"
                            continue
                        raise LoiHangDoiDay(
                            f"Hàng đợi xử lý cục bộ đã đầy ({dp.dang_cho}/{dp.do_dai_hang_doi_toi_da})",
                            ma_yeu_cau=ma_yeu_cau,
                        )

                    await dp.vao_hang(ma_yeu_cau)
                    cho_luot = True
                else:
                    cho_luot = False

                da_chay = False
                t0 = 0.0
                try:
                    if cho_luot:
                        await dp.cho_den_luot(ma_yeu_cau)
                    else:
                        await dp.bat_dau_chay_ngay(ma_yeu_cau)
                    da_chay = True
                    t0 = time.perf_counter()
                    kq_local = await _thuc_hien_goi_local(
                        tin_nhan,
                        ma_yeu_cau=ma_yeu_cau,
                        do_dai_hang_doi=dp.dang_cho,
                        cfg=cfg,
                        tuy_chon=tuy_chon,
                    )
                finally:
                    if da_chay:
                        dp.giai_phong(time.perf_counter() - t0)
                    elif cho_luot:
                        dp.huy_cho()

                kq = KetQuaGoi(
                    noi_dung=kq_local.noi_dung,
                    nguon="local",
                    tang=0,
                    bac_local=kq_local.bac,
                    ten_model=kq_local.model,
                    token_vao=kq_local.token_vao,
                    token_ra=kq_local.token_ra,
                    chi_phi_usd=0.0,
                    do_tre_ms=kq_local.do_tre_ms,
                    thoi_gian_nap_ms=kq_local.thoi_gian_nap_ms,
                    toc_do_tok_s=kq_local.toc_do_tok_s,
                    do_dai_hang_doi=dp.dang_cho,
                    so_lan_thu=1,
                    danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                    da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                    so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                    ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                )
                _luu_nhat_ky_va_kho(
                    kq,
                    ma_yeu_cau=ma_yeu_cau,
                    nguoi_id=nguoi.id,
                    kho=kho,
                    cfg=cfg,
                    tang_dau=tang_dau,
                    loai_loi_cac_tang=loai_loi_cac_tang,
                    muc_dich=muc_dich,
                )
                return kq

            # Kiểm tra ngân sách trước MỖI lời gọi tầng đám mây
            vuot_ngan_sach, vuot_canh_bao, tong_chi_phi = kiem_tra_ngan_sach(
                ngan_sach_ngay_usd=cfg.ngan_sach_ngay_usd,
                nguong_canh_bao=cfg.cai_dat_chung.nguong_canh_bao_ngan_sach,
                kho=kho,
                cfg=cfg,
            )
            if vuot_canh_bao:
                logger.warning(
                    "[%s] Cảnh báo ngân sách ngày: tổng chi phí hiện tại %.4f USD "
                    "đạt ngưỡng %.0f%% của ngân sách %.2f USD",
                    ma_yeu_cau,
                    tong_chi_phi,
                    cfg.cai_dat_chung.nguong_canh_bao_ngan_sach * 100,
                    cfg.ngan_sach_ngay_usd,
                )
            if vuot_ngan_sach:
                logger.warning(
                    "[%s] VƯỢT NGÂN SÁCH ngày (%.4f/%.2f USD). Bỏ qua các tầng đám mây.",
                    ma_yeu_cau,
                    tong_chi_phi,
                    cfg.ngan_sach_ngay_usd,
                )
                idx = chuoi.index(t)
                con_local_sau = any(sau.so == 0 for sau in chuoi[idx + 1:])
                if not con_local_sau:
                    raise LoiVuotNganSach(
                        f"Chi phí trong ngày ({tong_chi_phi:.4f} USD) đã vượt ngân sách "
                        f"({cfg.ngan_sach_ngay_usd:.2f} USD) và không còn tầng local",
                        ma_yeu_cau=ma_yeu_cau,
                    )
                continue

            tang_dm = _tim_cau_hinh_tang_dam_may(cfg, t)
            kq_dm = await _thuc_hien_goi_dam_may(
                tang_dm,
                tin_nhan,
                ma_yeu_cau=ma_yeu_cau,
                cfg=cfg,
                tuy_chon=tuy_chon,
            )
            chi_phi = uoc_tinh_chi_phi(t.so, kq_dm.token_vao, kq_dm.token_ra, cfg)
            toc_do = _tinh_toc_do(kq_dm.token_ra, kq_dm.do_tre_ms / 1000.0)
            kq = KetQuaGoi(
                noi_dung=kq_dm.noi_dung,
                nguon="dam_may",
                tang=t.so,
                bac_local=None,
                ten_model=kq_dm.model,
                token_vao=kq_dm.token_vao,
                token_ra=kq_dm.token_ra,
                chi_phi_usd=chi_phi,
                do_tre_ms=kq_dm.do_tre_ms,
                thoi_gian_nap_ms=0.0,
                toc_do_tok_s=toc_do,
                so_lan_thu=kq_dm.so_lan_thu,
                danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                ly_do_chuoi=kq_chuoi.ly_do_chuoi,
            )
            _luu_nhat_ky_va_kho(
                kq,
                ma_yeu_cau=ma_yeu_cau,
                nguoi_id=nguoi.id,
                kho=kho,
                cfg=cfg,
                tang_dau=tang_dau,
                loai_loi_cac_tang=loai_loi_cac_tang,
                muc_dich=muc_dich,
            )
            return kq

        except (LoiDauVao, LoiHangDoiDay, LoiVuotNganSach):
            raise
        except (LoiHetBacLocal, LoiTamThoi, LoiVinhVien) as err:
            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            loai_loi_cac_tang[t.so] = _loai_loi(err)
            logger.warning("[%s] Tầng %s thất bại: %s. Chuyển tầng sau.", ma_yeu_cau, t.so, err)
            continue
        except Exception as err:
            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            loai_loi_cac_tang[t.so] = _loai_loi(err)
            logger.warning("[%s] Tầng %s gặp lỗi: %s. Chuyển tầng sau.", ma_yeu_cau, t.so, err)
            continue

    kq_ban = _tao_ket_qua_khi_ban(ma_yeu_cau, kq_chuoi.ly_do_chuoi, danh_sach_tang_da_hong)
    _luu_nhat_ky_va_kho(
        kq_ban,
        ma_yeu_cau=ma_yeu_cau,
        nguoi_id=nguoi.id,
        kho=kho,
        cfg=cfg,
        tang_dau=tang_dau,
        loai_loi_cac_tang=loai_loi_cac_tang,
        muc_dich=muc_dich,
        thanh_cong=False,
    )
    if all(t.so == 0 for t in chuoi):
        return kq_ban

    raise LoiHetChuoiDuPhong(
        f"Toàn bộ các tầng trong chuỗi định tuyến đều thất bại cho yêu cầu {ma_yeu_cau}",
        danh_sach_ly_do=ly_do_cac_tang,
        ma_yeu_cau=ma_yeu_cau,
    )


async def _dong_local(
    tin_nhan: list[dict[str, Any]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> AsyncIterator[KetQuaDongLocal]:
    """Tạo bộ lặp phát dòng từ bộ chạy cục bộ."""
    bo_chay = tuy_chon.get("bo_chay")
    temperature = tuy_chon.get("temperature")
    max_tokens = tuy_chon.get("max_tokens")
    uu_tien_bac_nho = bool(tuy_chon.get("uu_tien_bac_nho", False))
    bac_ep = tuy_chon.get("bac_ep")
    gen = await goi_local(
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        do_dai_hang_doi=do_dai_hang_doi,
        phat_theo_dong=True,
        bo_chay=bo_chay,
        cau_hinh_he_thong=cfg,
        temperature=temperature,
        max_tokens=max_tokens,
        uu_tien_bac_nho=uu_tien_bac_nho,
        bac_ep=bac_ep,
    )
    async for item in gen:
        yield item


async def _dong_dam_may(
    tang_dm: CauHinhTangDamMay,
    tin_nhan: list[dict[str, Any]],
    *,
    ma_yeu_cau: str,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> AsyncIterator[KetQuaDongDamMay]:
    """Tạo bộ lặp phát dòng từ nhà cung cấp đám mây."""
    cac_tham_so = {k: v for k, v in tuy_chon.items() if k not in _KHOA_NOI_BO}
    gen = await goi_dam_may(
        tang_dm,
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        phat_theo_dong=True,
        cau_hinh_he_thong=cfg,
        **cac_tham_so,
    )
    async for item in gen:
        yield item


async def goi_mo_hinh_theo_dong(
    tin_nhan: list[dict],
    *,
    nguoi: NguoiDung,
    ma_yeu_cau: str,
    nhan_du_lieu: NhanDuLieu = NhanDuLieu.THUONG,
    do_dai_hang_doi: int = 0,
    ep_tang: str | int | None = None,
    **tuy_chon: Any,
) -> AsyncIterator[ManhPhatRa]:
    """Gọi mô hình LLM dạng phát theo dòng (SSE) qua chuỗi định tuyến.

    Xử lý đặc biệt:
    - Phát mảnh "hang_doi" ngay khi yêu cầu vào hàng đợi tầng 0.
    - Lỗi trước mảnh đầu: chuyển sang tầng sau bình thường.
    - Lỗi giữa chừng sau khi đã phát: kết thúc luồng bằng mảnh 'loi', không rơi tầng.
    - Khi ep_tang được truyền: ép chạy đúng tầng đó (dùng cho đánh giá).
    """
    cfg: CauHinhHeThong = tuy_chon.get("cau_hinh_he_thong") or cau_hinh
    dp: DieuPhoi = tuy_chon.get("dieu_phoi") or dieu_phoi_mac_dinh
    kho: KhoLuotGoi = tuy_chon.get("kho_luot_goi") or kho_luot_goi_mac_dinh

    uu_tien_bac_nho_hieu_luc = bool(tuy_chon.get("uu_tien_bac_nho", False))
    che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cfg.che_do_dinh_tuyen
    kq_chuoi = xac_dinh_chuoi(
        nguoi,
        nhan_du_lieu,
        che_do=che_do,
        cau_hinh_he_thong=cfg,
        cau_hinh_cs=tuy_chon.get("cau_hinh_cs"),
    )
    chuoi = kq_chuoi.chuoi
    if uu_tien_bac_nho_hieu_luc:
        chuoi = [t for t in chuoi if t.so == 0]
        if not chuoi:
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=4096, nguon="local")]

    ep_tang_hieu_luc = ep_tang if ep_tang is not None else tuy_chon.get("ep_tang")
    if ep_tang_hieu_luc is not None:
        if ep_tang_hieu_luc == "local1":
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=8192, nguon="local")]
            tuy_chon["bac_ep"] = "chinh"
        elif ep_tang_hieu_luc == "local2":
            chuoi = [Tang(so=0, ten="local", cua_so_ngu_canh=8192, nguon="local")]
            tuy_chon["bac_ep"] = "nho"
        elif str(ep_tang_hieu_luc) in ("1", "2", "3", "4"):
            tang_so = int(ep_tang_hieu_luc)
            if nhan_du_lieu == NhanDuLieu.NHAY_CAM or str(nhan_du_lieu).upper() == "NHAY_CAM":
                raise LoiDauVao(
                    f"Dữ liệu nhãn NHAY_CAM không được phép gửi tới tầng đám mây {tang_so} (Quy tắc 2)",
                    ma_yeu_cau=ma_yeu_cau,
                )
            tang_dm_cfg = next((cdm for cdm in cfg.chuoi_dam_may if cdm.tang == tang_so), None)
            if tang_dm_cfg is None:
                raise LoiDauVao(
                    f"Tầng đám mây {tang_so} không tồn tại trong cấu hình",
                    ma_yeu_cau=ma_yeu_cau,
                )
            chuoi = [Tang(so=tang_so, ten=tang_dm_cfg.ten, cua_so_ngu_canh=tang_dm_cfg.cua_so_ngu_canh, nguon="dam_may")]
        else:
            raise LoiDauVao(f"Giá trị ep_tang không hợp lệ: {ep_tang_hieu_luc}", ma_yeu_cau=ma_yeu_cau)

    tang_dau = chuoi[0].so if chuoi else None
    co_tang_dam_may = any(t.so > 0 for t in chuoi)
    muc_dich = str(tuy_chon.get("muc_dich", "chat"))

    danh_sach_tang_da_hong: list[int] = []
    ly_do_cac_tang: dict[int, str] = {}
    loai_loi_cac_tang: dict[int, str] = {}

    for t in chuoi:
        van_ban_da_nhan = ""
        da_phat_mau = False
        da_phat_bat_dau = False
        try:
            if t.so == 0:
                if dp.can_vao_hang() or bool(tuy_chon.get("luon_vao_hang")):
                    if dp.kiem_tra_hang_doi_day():
                        dp.ghi_nhan_tu_choi()
                        if co_tang_dam_may:
                            logger.warning(
                                "[%s] Hàng đợi local đầy, luồng phát chuyển tầng sau",
                                ma_yeu_cau,
                            )
                            danh_sach_tang_da_hong.append(0)
                            ly_do_cac_tang[0] = "HANG_DOI_DAY"
                            loai_loi_cac_tang[0] = "HANG_DOI_DAY"
                            continue
                        raise LoiHangDoiDay(
                            f"Hàng đợi xử lý cục bộ đã đầy ({dp.dang_cho}/{dp.do_dai_hang_doi_toi_da})",
                            ma_yeu_cau=ma_yeu_cau,
                        )

                    vi_tri = await dp.vao_hang(ma_yeu_cau)
                    yield ManhPhatRa(
                        loai="hang_doi",
                        noi_dung=f"Yêu cầu đang chờ tại vị trí {vi_tri.vi_tri}",
                        vi_tri=vi_tri.vi_tri,
                        uoc_luong_giay=vi_tri.uoc_luong_giay,
                    )
                    cho_luot = True
                else:
                    cho_luot = False

                da_chay = False
                t0 = 0.0
                try:
                    if cho_luot:
                        await dp.cho_den_luot(ma_yeu_cau)
                    else:
                        await dp.bat_dau_chay_ngay(ma_yeu_cau)
                    da_chay = True
                    t0 = time.perf_counter()
                    async for mau_local in _dong_local(
                        tin_nhan,
                        ma_yeu_cau=ma_yeu_cau,
                        do_dai_hang_doi=dp.dang_cho,
                        cfg=cfg,
                        tuy_chon=tuy_chon,
                    ):
                        if not da_phat_bat_dau:
                            da_phat_bat_dau = True
                            yield ManhPhatRa(
                                loai="bat_dau",
                                nguon="local",
                                tang=0,
                                bac_local=mau_local.bac,
                                ten_model=mau_local.model,
                                da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                                so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                            )
                        if not mau_local.da_xong:
                            if mau_local.noi_dung:
                                van_ban_da_nhan += mau_local.noi_dung
                                da_phat_mau = True
                                yield ManhPhatRa(
                                    loai="manh",
                                    noi_dung=mau_local.noi_dung,
                                    ket_qua=None,
                                )
                        else:
                            kq = KetQuaGoi(
                                noi_dung=van_ban_da_nhan,
                                nguon="local",
                                tang=0,
                                bac_local=mau_local.bac,
                                ten_model=mau_local.model,
                                token_vao=mau_local.token_vao,
                                token_ra=mau_local.token_ra,
                                chi_phi_usd=0.0,
                                do_tre_ms=mau_local.do_tre_ms,
                                thoi_gian_nap_ms=mau_local.thoi_gian_nap_ms,
                                toc_do_tok_s=mau_local.toc_do_tok_s,
                                do_dai_hang_doi=dp.dang_cho,
                                so_lan_thu=1,
                                danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                                da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                                so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                                ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                            )
                            _luu_nhat_ky_va_kho(
                                kq,
                                ma_yeu_cau=ma_yeu_cau,
                                nguoi_id=nguoi.id,
                                kho=kho,
                                cfg=cfg,
                                tang_dau=tang_dau,
                                loai_loi_cac_tang=loai_loi_cac_tang,
                                muc_dich=muc_dich,
                            )
                            yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq)
                            return
                finally:
                    if da_chay:
                        dp.giai_phong(time.perf_counter() - t0)
                    elif cho_luot:
                        dp.huy_cho()

            else:
                # Kiểm tra ngân sách trước MỖI lời gọi tầng đám mây
                vuot_ngan_sach, vuot_canh_bao, tong_chi_phi = kiem_tra_ngan_sach(
                    ngan_sach_ngay_usd=cfg.ngan_sach_ngay_usd,
                    nguong_canh_bao=cfg.cai_dat_chung.nguong_canh_bao_ngan_sach,
                    kho=kho,
                    cfg=cfg,
                )
                if vuot_canh_bao:
                    logger.warning(
                        "[%s] Cảnh báo ngân sách ngày: tổng chi phí hiện tại %.4f USD "
                        "đạt ngưỡng %.0f%% của ngân sách %.2f USD",
                        ma_yeu_cau,
                        tong_chi_phi,
                        cfg.cai_dat_chung.nguong_canh_bao_ngan_sach * 100,
                        cfg.ngan_sach_ngay_usd,
                    )
                if vuot_ngan_sach:
                    logger.warning(
                        "[%s] VƯỢT NGÂN SÁCH ngày (%.4f/%.2f USD). Bỏ qua các tầng đám mây.",
                        ma_yeu_cau,
                        tong_chi_phi,
                        cfg.ngan_sach_ngay_usd,
                    )
                    idx = chuoi.index(t)
                    con_local_sau = any(sau.so == 0 for sau in chuoi[idx + 1:])
                    if not con_local_sau:
                        raise LoiVuotNganSach(
                            f"Chi phí trong ngày ({tong_chi_phi:.4f} USD) đã vượt ngân sách "
                            f"({cfg.ngan_sach_ngay_usd:.2f} USD) và không còn tầng local",
                            ma_yeu_cau=ma_yeu_cau,
                        )
                    continue

                tang_dm = _tim_cau_hinh_tang_dam_may(cfg, t)
                async for mau_dm in _dong_dam_may(
                    tang_dm,
                    tin_nhan,
                    ma_yeu_cau=ma_yeu_cau,
                    cfg=cfg,
                    tuy_chon=tuy_chon,
                ):
                    if not da_phat_bat_dau:
                        da_phat_bat_dau = True
                        yield ManhPhatRa(
                            loai="bat_dau",
                            nguon="dam_may",
                            tang=t.so,
                            bac_local=None,
                            ten_model=mau_dm.model or tang_dm.model,
                            da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                            so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                        )
                    if not mau_dm.da_xong:
                        if mau_dm.noi_dung:
                            van_ban_da_nhan += mau_dm.noi_dung
                            da_phat_mau = True
                            yield ManhPhatRa(
                                loai="manh",
                                noi_dung=mau_dm.noi_dung,
                                ket_qua=None,
                            )
                    else:
                        chi_phi = uoc_tinh_chi_phi(t.so, mau_dm.token_vao, mau_dm.token_ra, cfg)
                        toc_do = _tinh_toc_do(mau_dm.token_ra, mau_dm.do_tre_ms / 1000.0)
                        kq = KetQuaGoi(
                            noi_dung=van_ban_da_nhan,
                            nguon="dam_may",
                            tang=t.so,
                            bac_local=None,
                            ten_model=mau_dm.model,
                            token_vao=mau_dm.token_vao,
                            token_ra=mau_dm.token_ra,
                            chi_phi_usd=chi_phi,
                            do_tre_ms=mau_dm.do_tre_ms,
                            thoi_gian_nap_ms=0.0,
                            toc_do_tok_s=toc_do,
                            so_lan_thu=1,
                            danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                            da_cat_ngu_canh=bool(tuy_chon.get("da_cat_ngu_canh", False)),
                            so_luot_bi_cat=int(tuy_chon.get("so_luot_bi_cat", 0)),
                            ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                        )
                        _luu_nhat_ky_va_kho(
                            kq,
                            ma_yeu_cau=ma_yeu_cau,
                            nguoi_id=nguoi.id,
                            kho=kho,
                            cfg=cfg,
                            tang_dau=tang_dau,
                            loai_loi_cac_tang=loai_loi_cac_tang,
                            muc_dich=muc_dich,
                        )
                        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq)
                        return

        except (LoiDauVao, LoiHangDoiDay, LoiVuotNganSach):
            raise
        except Exception as err:  # noqa: BLE001 - Bắt ngoại lệ để chuyển tầng sau hoặc phát mảnh lỗi
            if da_phat_bat_dau or da_phat_mau:
                logger.warning(
                    "[%s] Tầng %s bị ngắt giữa chừng khi đang phát dòng: %s. Trả mảnh lỗi.",
                    ma_yeu_cau,
                    t.so,
                    err,
                )
                yield ManhPhatRa(loai="loi", noi_dung=van_ban_da_nhan, ket_qua=None)
                return

            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            loai_loi_cac_tang[t.so] = _loai_loi(err)
            logger.warning(
                "[%s] Tầng %s lỗi trước mảnh đầu tiên: %s. Chuyển tầng sau.",
                ma_yeu_cau,
                t.so,
                err,
            )
            continue

    kq_ban = _tao_ket_qua_khi_ban(ma_yeu_cau, kq_chuoi.ly_do_chuoi, danh_sach_tang_da_hong)
    _luu_nhat_ky_va_kho(
        kq_ban,
        ma_yeu_cau=ma_yeu_cau,
        nguoi_id=nguoi.id,
        kho=kho,
        cfg=cfg,
        tang_dau=tang_dau,
        loai_loi_cac_tang=loai_loi_cac_tang,
        muc_dich=muc_dich,
        thanh_cong=False,
    )
    if all(t.so == 0 for t in chuoi):
        yield ManhPhatRa(
            loai="bat_dau",
            nguon="local",
            tang=0,
            bac_local=None,
            ten_model="khong_co",
        )
        yield ManhPhatRa(loai="manh", noi_dung=kq_ban.noi_dung, ket_qua=None)
        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq_ban)
        return

    raise LoiHetChuoiDuPhong(
        f"Toàn bộ các tầng trong chuỗi định tuyến đều thất bại cho luồng phát {ma_yeu_cau}",
        danh_sach_ly_do=ly_do_cac_tang,
        ma_yeu_cau=ma_yeu_cau,
    )


def _doc_cau_hinh_rag() -> dict[str, Any]:
    """Đọc cấu hình RAG từ tệp config/rag.yaml."""
    duong_dan = Path(__file__).resolve().parents[3] / "config" / "rag.yaml"
    if not duong_dan.exists():
        duong_dan = Path("/srv/config/rag.yaml")
    if not duong_dan.exists():
        return {
            "model_nhung": "bge-m3",
            "the_nhung_theo_ho_so": {
                "gpu6": "bge-m3-cpu:567m-fp16",
                "gpu8": "bge-m3-cpu:567m-fp16",
                "gpu12": "bge-m3:567m-fp16",
                "gpu16": "bge-m3:567m-fp16",
                "gpu24": "bge-m3:567m-fp16",
            },
            "so_chieu": 1024,
            "kich_thuoc_lo": 32,
        }
    try:
        noi_dung = duong_dan.read_text(encoding="utf-8")
        du_lieu = yaml.safe_load(noi_dung)
        return du_lieu if isinstance(du_lieu, dict) else {}
    except Exception as err:
        logger.warning("Không thể đọc tệp cấu hình RAG %s: %s", duong_dan, err)
        return {}


def lay_the_nhung_theo_ho_so(ho_so_gpu: str, rag_cfg: dict[str, Any] | None = None) -> str:
    """Lấy thẻ model nhúng thực tế theo hồ sơ GPU từ config/rag.yaml."""
    cfg_rag = rag_cfg if rag_cfg is not None else _doc_cau_hinh_rag()
    the_theo_hs = cfg_rag.get("the_nhung_theo_ho_so", {})
    if isinstance(the_theo_hs, dict) and ho_so_gpu in the_theo_hs:
        return str(the_theo_hs[ho_so_gpu])
    if ho_so_gpu in ("gpu6", "gpu8"):
        return "bge-m3-cpu:567m-fp16"
    return "bge-m3:567m-fp16"


async def goi_nhung(
    van_ban: list[str],
    *,
    ma_yeu_cau: str,
    **tuy_chon: Any,
) -> KetQuaNhung:
    """Gọi mô hình tạo vector nhúng qua bộ chạy cục bộ.

    Điểm nhập duy nhất trong ứng dụng cho các lời gọi nhúng mô hình.
    Tuân thủ tuyệt đối Quy tắc 1 (không import httpx, gọi qua bo_chay.nhung)
    và Quy tắc kỹ thuật 7 (ghi nhận LuotGoi với muc_dich='nhung').
    """
    cfg: CauHinhHeThong = tuy_chon.get("cau_hinh_he_thong") or cau_hinh
    kho: KhoLuotGoi = tuy_chon.get("kho_luot_goi") or kho_luot_goi_mac_dinh
    runner: BoChay = tuy_chon.get("bo_chay") or lay_bo_chay(cfg)
    rag_cfg = tuy_chon.get("cau_hinh_rag") or _doc_cau_hinh_rag()

    ho_so = getattr(cfg, "ho_so_gpu_dang_chon", "gpu8")
    model_nhung = str(tuy_chon.get("model") or lay_the_nhung_theo_ho_so(ho_so, rag_cfg))
    kich_thuoc_lo = int(tuy_chon.get("kich_thuoc_lo") or rag_cfg.get("kich_thuoc_lo", 32))
    timeout_giay = float(tuy_chon.get("timeout_giay", cfg.timeout_giay))
    so_lan_thu_lai = int(cfg.cai_dat_chung.so_lan_thu_lai_moi_tang)
    giay_gian_cach = float(cfg.cai_dat_chung.giay_gian_cach_dau)
    tong_so_luot = 1 + so_lan_thu_lai

    if not van_ban:
        return KetQuaNhung(
            vectors=[],
            model=model_nhung,
            so_chieu=0,
            do_tre_ms=0.0,
            token_vao=0,
        )

    # Chia lô 32 đoạn theo cấu hình
    cac_lo = [van_ban[i : i + kich_thuoc_lo] for i in range(0, len(van_ban), kich_thuoc_lo)]

    all_vectors: list[list[float]] = []
    tong_token_vao = 0
    tong_do_tre_ms = 0.0
    so_chieu = 0

    t_bat_dau_tong = time.perf_counter()
    loi_cuoi_cung: Exception | None = None

    for lo in cac_lo:
        thanh_cong_lo = False
        for lan in range(tong_so_luot):
            try:
                kq_lo = await runner.nhung(
                    model_nhung,
                    lo,
                    keep_alive=cfg.local_chung.keep_alive,
                    timeout_giay=timeout_giay,
                    ma_yeu_cau=ma_yeu_cau,
                )
                all_vectors.extend(kq_lo.vectors)
                tong_token_vao += kq_lo.token_vao
                tong_do_tre_ms += kq_lo.do_tre_ms
                if kq_lo.so_chieu > 0:
                    so_chieu = kq_lo.so_chieu
                thanh_cong_lo = True
                break
            except Exception as err:
                loi_cuoi_cung = err
                logger.warning(
                    "[%s] Lỗi khi gọi nhúng lô (%d đoạn), lần %d/%d: %s",
                    ma_yeu_cau,
                    len(lo),
                    lan + 1,
                    tong_so_luot,
                    err,
                )
                if lan < tong_so_luot - 1:
                    await asyncio.sleep(giay_gian_cach * (2 ** lan))

        if not thanh_cong_lo:
            do_tre_that_bai = round((time.perf_counter() - t_bat_dau_tong) * 1000, 2)
            lg_that_bai = LuotGoi(
                nguoi_id=str(tuy_chon.get("nguoi_id", "he_thong")),
                nguon="local",
                tang=0,
                bac=None,
                model=model_nhung,
                token_vao=tong_token_vao,
                token_ra=0,
                chi_phi_usd=0.0,
                do_tre_ms=do_tre_that_bai,
                thoi_gian_nap_ms=0.0,
                toc_do_tok_s=0.0,
                thanh_cong=False,
                ma_yeu_cau=ma_yeu_cau,
                roi_tang=False,
                ly_do_that_bai_tang_dau=_loai_loi(loi_cuoi_cung) if loi_cuoi_cung else "LoiNhung",
                muc_dich=chuan_hoa_muc_dich("nhung"),
            )
            kho.ghi(lg_that_bai)
            raise loi_cuoi_cung or RuntimeError(f"Nhúng văn bản thất bại sau {tong_so_luot} lượt thử")

    do_tre_tong_ms = round((time.perf_counter() - t_bat_dau_tong) * 1000, 2)
    kq_nhung = KetQuaNhung(
        vectors=all_vectors,
        model=model_nhung,
        so_chieu=so_chieu,
        do_tre_ms=do_tre_tong_ms,
        token_vao=tong_token_vao,
    )

    lg_thanh_cong = LuotGoi(
        nguoi_id=str(tuy_chon.get("nguoi_id", "he_thong")),
        nguon="local",
        tang=0,
        bac=None,
        model=model_nhung,
        token_vao=tong_token_vao,
        token_ra=0,
        chi_phi_usd=0.0,
        do_tre_ms=do_tre_tong_ms,
        thoi_gian_nap_ms=0.0,
        toc_do_tok_s=0.0,
        thanh_cong=True,
        ma_yeu_cau=ma_yeu_cau,
        roi_tang=False,
        ly_do_that_bai_tang_dau=None,
        muc_dich=chuan_hoa_muc_dich("nhung"),
    )
    kho.ghi(lg_thanh_cong)

    logger.info(
        "[%s] Lượt gọi nhúng mô hình hoàn thành: nguồn=local, tầng=0, model=%s, "
        "token_vào=%d, số_đoạn=%d, số_chiều=%d, độ_trễ_ms=%.2f",
        ma_yeu_cau,
        model_nhung,
        tong_token_vao,
        len(van_ban),
        so_chieu,
        do_tre_tong_ms,
    )

    return kq_nhung


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Công cụ chạy thử nghiệm router định tuyến.")
    parser.add_argument(
        "--thu",
        type=str,
        default="Cách tính tiền điện bậc thang",
        help="Nội dung câu hỏi thử nghiệm",
    )
    parser.add_argument(
        "--che-do",
        type=str,
        default="local_truoc",
        help="Chế độ định tuyến (local_truoc, chi_local, dam_may_truoc)",
    )
    args = parser.parse_args()

    async def _chay_thu() -> None:
        nguoi_gia = NguoiDung(
            id=1,
            email="can_bo_cntt@vidu.com",
            vai_tro="chuyen_vien",
            bac="free",
            phong_ban="CNTT",
            che_do_dinh_tuyen=args.che_do,
        )
        ma_yc = f"thu_nghiem_{int(time.time())}"
        tin_nhan_mau = [{"role": "user", "content": args.thu}]
        ket_qua = await goi_mo_hinh(tin_nhan_mau, nguoi=nguoi_gia, ma_yeu_cau=ma_yc)
        print(
            f"Nguồn: {ket_qua.nguon} | Tầng: {ket_qua.tang} | "
            f"Model: {ket_qua.ten_model} | Độ trễ: {ket_qua.do_tre_ms}ms"
        )
        print(f"tang = {ket_qua.tang} ({ket_qua.ten_model})")

    asyncio.run(_chay_thu())
