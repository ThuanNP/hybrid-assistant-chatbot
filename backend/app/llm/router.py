"""Định tuyến các lời gọi mô hình qua chuỗi local và đám mây.

Mọi lời gọi model trong ứng dụng bắt buộc đi qua đúng một cửa tại mô-đun này:
- goi_mo_hinh(): gọi hoàn thành hội thoại một lần (POST /chat, tích hợp M2M).
- goi_mo_hinh_theo_dong(): phát câu trả lời theo dòng (SSE).

Tuân thủ tuyệt đối Quy tắc 1, 2 và Quy tắc kỹ thuật 7 trong AGENTS.md.
"""

import argparse
import asyncio
import logging
from pathlib import Path
import re
import time
from typing import Any, AsyncIterator, Literal

from pydantic import BaseModel, Field

from app.config import CauHinhHeThong, CauHinhTangDamMay, cau_hinh
from app.core.loi import (
    LoiDauVao,
    LoiHetBacLocal,
    LoiHetChuoiDuPhong,
    LoiTamThoi,
    LoiVinhVien,
)
from app.core.xac_thuc import NguoiDung
from app.llm.bo_chay_local import (
    KetQuaDongLocal,
    KetQuaGoiLocal,
    goi_local,
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

__all__ = ["KetQuaGoi", "ManhPhatRa", "goi_mo_hinh", "goi_mo_hinh_theo_dong"]


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
    so_lan_thu: int = 1
    danh_sach_tang_da_hong: list[int] = Field(default_factory=list)
    da_cat_ngu_canh: bool = False
    so_luot_bi_cat: int = 0
    ly_do_chuoi: str = ""


class ManhPhatRa(BaseModel):
    """Mảnh dữ liệu phát theo dòng (SSE) trả về cho người dùng."""

    loai: Literal["manh", "xong", "loi"]
    noi_dung: str = ""
    ket_qua: KetQuaGoi | None = None


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
    return await goi_local(
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        do_dai_hang_doi=do_dai_hang_doi,
        phat_theo_dong=False,
        bo_chay=bo_chay,
        cau_hinh_he_thong=cfg,
        temperature=temperature,
        max_tokens=max_tokens,
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
    cac_tham_so = {
        k: v
        for k, v in tuy_chon.items()
        if k not in ("bo_chay", "cau_hinh_he_thong", "cau_hinh_cs", "do_dai_hang_doi")
    }
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
    **tuy_chon: Any,
) -> KetQuaGoi:
    """Gọi mô hình LLM qua chuỗi định tuyến đã được xác thực chính sách.

    Điểm nhập duy nhất trong ứng dụng cho các lời gọi mô hình không phát dòng.
    """
    cfg: CauHinhHeThong = tuy_chon.get("cau_hinh_he_thong") or cau_hinh
    che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cfg.che_do_dinh_tuyen
    kq_chuoi = xac_dinh_chuoi(
        nguoi,
        nhan_du_lieu,
        che_do=che_do,
        cau_hinh_he_thong=cfg,
        cau_hinh_cs=tuy_chon.get("cau_hinh_cs"),
    )
    chuoi = kq_chuoi.chuoi
    danh_sach_tang_da_hong: list[int] = []
    ly_do_cac_tang: dict[int, str] = {}
    do_dai_hang_doi = int(tuy_chon.get("do_dai_hang_doi", 0))

    for t in chuoi:
        try:
            if t.so == 0:
                kq_local = await _thuc_hien_goi_local(
                    tin_nhan,
                    ma_yeu_cau=ma_yeu_cau,
                    do_dai_hang_doi=do_dai_hang_doi,
                    cfg=cfg,
                    tuy_chon=tuy_chon,
                )
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
                    so_lan_thu=1,
                    danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                    da_cat_ngu_canh=False,
                    so_luot_bi_cat=0,
                    ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                )
                _ghi_nhat_ky(kq, ma_yeu_cau)
                return kq

            tang_dm = _tim_cau_hinh_tang_dam_may(cfg, t)
            kq_dm = await _thuc_hien_goi_dam_may(
                tang_dm,
                tin_nhan,
                ma_yeu_cau=ma_yeu_cau,
                cfg=cfg,
                tuy_chon=tuy_chon,
            )
            toc_do = _tinh_toc_do(kq_dm.token_ra, kq_dm.do_tre_ms / 1000.0)
            kq = KetQuaGoi(
                noi_dung=kq_dm.noi_dung,
                nguon="dam_may",
                tang=t.so,
                bac_local=None,
                ten_model=kq_dm.model,
                token_vao=kq_dm.token_vao,
                token_ra=kq_dm.token_ra,
                chi_phi_usd=0.0,
                do_tre_ms=kq_dm.do_tre_ms,
                thoi_gian_nap_ms=0.0,
                toc_do_tok_s=toc_do,
                so_lan_thu=kq_dm.so_lan_thu,
                danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                da_cat_ngu_canh=False,
                so_luot_bi_cat=0,
                ly_do_chuoi=kq_chuoi.ly_do_chuoi,
            )
            _ghi_nhat_ky(kq, ma_yeu_cau)
            return kq

        except LoiDauVao:
            raise
        except (LoiHetBacLocal, LoiTamThoi, LoiVinhVien) as err:
            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            logger.warning("[%s] Tầng %s thất bại: %s. Chuyển tầng sau.", ma_yeu_cau, t.so, err)
            continue
        except Exception as err:
            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            logger.warning("[%s] Tầng %s gặp lỗi: %s. Chuyển tầng sau.", ma_yeu_cau, t.so, err)
            continue

    if all(t.so == 0 for t in chuoi):
        kq_ban = _tao_ket_qua_khi_ban(ma_yeu_cau, kq_chuoi.ly_do_chuoi, danh_sach_tang_da_hong)
        _ghi_nhat_ky(kq_ban, ma_yeu_cau)
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
    gen = await goi_local(
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        do_dai_hang_doi=do_dai_hang_doi,
        phat_theo_dong=True,
        bo_chay=bo_chay,
        cau_hinh_he_thong=cfg,
        temperature=temperature,
        max_tokens=max_tokens,
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
    cac_tham_so = {
        k: v
        for k, v in tuy_chon.items()
        if k not in ("bo_chay", "cau_hinh_he_thong", "cau_hinh_cs", "do_dai_hang_doi")
    }
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
    **tuy_chon: Any,
) -> AsyncIterator[ManhPhatRa]:
    """Gọi mô hình LLM dạng phát theo dòng (SSE) qua chuỗi định tuyến.

    Xử lý đặc biệt:
    - Lỗi trước mảnh đầu: chuyển sang tầng sau bình thường.
    - Lỗi giữa chừng sau khi đã phát: kết thúc luồng bằng mảnh 'loi', không rơi tầng.
    """
    cfg: CauHinhHeThong = tuy_chon.get("cau_hinh_he_thong") or cau_hinh
    che_do = getattr(nguoi, "che_do_dinh_tuyen", None) or cfg.che_do_dinh_tuyen
    kq_chuoi = xac_dinh_chuoi(
        nguoi,
        nhan_du_lieu,
        che_do=che_do,
        cau_hinh_he_thong=cfg,
        cau_hinh_cs=tuy_chon.get("cau_hinh_cs"),
    )
    chuoi = kq_chuoi.chuoi
    danh_sach_tang_da_hong: list[int] = []
    ly_do_cac_tang: dict[int, str] = {}

    for t in chuoi:
        van_ban_da_nhan = ""
        da_phat_mau = False
        try:
            if t.so == 0:
                async for mau_local in _dong_local(
                    tin_nhan,
                    ma_yeu_cau=ma_yeu_cau,
                    do_dai_hang_doi=do_dai_hang_doi,
                    cfg=cfg,
                    tuy_chon=tuy_chon,
                ):
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
                            so_lan_thu=1,
                            danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                            da_cat_ngu_canh=False,
                            so_luot_bi_cat=0,
                            ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                        )
                        _ghi_nhat_ky(kq, ma_yeu_cau)
                        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq)
                        return
            else:
                tang_dm = _tim_cau_hinh_tang_dam_may(cfg, t)
                async for mau_dm in _dong_dam_may(
                    tang_dm,
                    tin_nhan,
                    ma_yeu_cau=ma_yeu_cau,
                    cfg=cfg,
                    tuy_chon=tuy_chon,
                ):
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
                        toc_do = _tinh_toc_do(mau_dm.token_ra, mau_dm.do_tre_ms / 1000.0)
                        kq = KetQuaGoi(
                            noi_dung=van_ban_da_nhan,
                            nguon="dam_may",
                            tang=t.so,
                            bac_local=None,
                            ten_model=mau_dm.model,
                            token_vao=mau_dm.token_vao,
                            token_ra=mau_dm.token_ra,
                            chi_phi_usd=0.0,
                            do_tre_ms=mau_dm.do_tre_ms,
                            thoi_gian_nap_ms=0.0,
                            toc_do_tok_s=toc_do,
                            so_lan_thu=1,
                            danh_sach_tang_da_hong=list(danh_sach_tang_da_hong),
                            da_cat_ngu_canh=False,
                            so_luot_bi_cat=0,
                            ly_do_chuoi=kq_chuoi.ly_do_chuoi,
                        )
                        _ghi_nhat_ky(kq, ma_yeu_cau)
                        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq)
                        return

        except Exception as err:
            if da_phat_mau:
                logger.warning(
                    "[%s] Tầng %s bị ngắt giữa chừng khi đang phát dòng: %s. Trả mảnh lỗi.",
                    ma_yeu_cau,
                    t.so,
                    err,
                )
                yield ManhPhatRa(loai="loi", noi_dung=van_ban_da_nhan, ket_qua=None)
                return

            if isinstance(err, LoiDauVao):
                raise

            danh_sach_tang_da_hong.append(t.so)
            ly_do_cac_tang[t.so] = str(err)
            logger.warning(
                "[%s] Tầng %s lỗi trước mảnh đầu tiên: %s. Chuyển tầng sau.",
                ma_yeu_cau,
                t.so,
                err,
            )
            continue

    if all(t.so == 0 for t in chuoi):
        kq_ban = _tao_ket_qua_khi_ban(ma_yeu_cau, kq_chuoi.ly_do_chuoi, danh_sach_tang_da_hong)
        _ghi_nhat_ky(kq_ban, ma_yeu_cau)
        yield ManhPhatRa(loai="manh", noi_dung=kq_ban.noi_dung, ket_qua=None)
        yield ManhPhatRa(loai="xong", noi_dung="", ket_qua=kq_ban)
        return

    raise LoiHetChuoiDuPhong(
        f"Toàn bộ các tầng trong chuỗi định tuyến đều thất bại cho luồng phát {ma_yeu_cau}",
        danh_sach_ly_do=ly_do_cac_tang,
        ma_yeu_cau=ma_yeu_cau,
    )


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
            id="nd_kiem_thu",
            ten_dang_nhap="can_bo_cntt",
            vai_tro="chuyen_vien",
            bac="chinh",
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
