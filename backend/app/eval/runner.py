"""Bộ chạy đánh giá chất lượng các tầng mô hình theo bộ câu hỏi chuẩn.

Chạy tuần tự từng tầng một (local1, local2, 1, 2, 3, 4), mỗi câu hỏi chạy N lần (mặc định 3).
Tuân thủ Quy tắc tuyệt đối 1, 2 trong AGENTS.md:
- Mọi lượt gọi mô hình đều qua goi_mo_hinh() trong app.llm.router.
- Câu hỏi có nhay_cam=True tuyệt đối KHÔNG gửi lên các tầng đám mây (ghi nhận 'BỎ QUA').
- Lỗi giới hạn tần suất (429/quota) ghi nhận 'GIỚI HẠN', không tính là hỏng và không dừng luồng.
- Tầng 2 (openrouter_free) là tầng tham khảo, loại khỏi so sánh bất đồng và so sánh lần chạy trước.
"""

import argparse
import asyncio
import json
import logging
import statistics
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.chat.ngu_canh import dung_ngu_canh
from app.config import cau_hinh
from app.core.bao_mat import che_du_lieu_ca_nhan, kiem_duyet_dau_ra
from app.core.loi import LoiHetChuoiDuPhong
from app.core.thoi_gian import MUI_GIO_VN
from app.core.xac_thuc import NguoiDung
from app.eval.cham_diem import cham_diem
from app.llm.chinh_sach import NhanDuLieu, xac_dinh_chuoi
from app.llm.router import KetQuaGoi, goi_mo_hinh

logger = logging.getLogger(__name__)

THU_MUC_GOC = Path(__file__).resolve().parents[3]
DUONG_DAN_BO_CAU_HOI_MAC_DINH = THU_MUC_GOC / "eval" / "bo_cau_hoi.yaml"
THU_MUC_KET_QUA_MAC_DINH = THU_MUC_GOC / "ket_qua_eval"

# Danh sách tầng mặc định theo thứ tự an toàn: local trước, đám mây sau
DANH_SACH_TANG_CHUAN = ["local1", "local2", "1", "2", "3", "4"]
TANG_THAM_KHAO = "2"  # Tầng 2 (OpenRouter free) chỉ tham khảo, loại khỏi diff
DANH_SACH_LOAI = [
    "co_ban",
    "dinh_dang",
    "tu_choi",
    "an_toan",
    "tieng_viet",
    "ngu_canh_dai",
    "thuong_gap",
]


class BanGhiLanChay(BaseModel):
    """Thông tin chi tiết một lần chạy của một câu hỏi trên một tầng."""

    lan: int
    noi_dung: str = ""
    do_tre_ms: float = 0.0
    toc_do_tok_s: float = 0.0
    token_vao: int = 0
    token_ra: int = 0
    chi_phi_usd: float = 0.0
    dat: bool = False
    lop_cham: str = ""
    ly_do_cham: str = ""
    trang_thai: str = "THANH_CONG"  # THANH_CONG | BO_QUA | GIOI_HAN | LOI


class KetQuaCauHoi(BaseModel):
    """Tổng hợp kết quả của một câu hỏi trên một tầng."""

    ma: str
    loai: str
    cau_hoi: str
    nhay_cam: bool = False
    lan_chay: list[BanGhiLanChay] = Field(default_factory=list)
    dat_trung_vi: bool = False
    do_tre_trung_vi_ms: float = 0.0
    toc_do_trung_vi_tok_s: float = 0.0
    chi_phi_trung_binh_usd: float = 0.0
    trang_thai_chung: str = "THANH_CONG"


class ThongKeTang(BaseModel):
    """Số liệu thống kê 6 cột của một tầng mô hình."""

    tang: str
    tong_so_cau: int = 0
    so_cau_dat: int = 0
    so_cau_bo_qua: int = 0
    so_cau_gioi_han: int = 0
    ty_le_dat_phan_tram: float = 0.0
    do_tre_p50_ms: float = 0.0
    do_tre_p95_ms: float = 0.0
    toc_do_p50_tok_s: float = 0.0
    tong_chi_phi_usd: float = 0.0
    do_dai_tra_loi_tb: float = 0.0
    # Tỷ lệ lượt đạt (0-100) theo loại, trên mọi lượt đã chấm (bỏ BỎ QUA và GIỚI HẠN)
    ty_le_dat_theo_loai: dict[str, float] = Field(default_factory=dict)
    nguong_dat_phan_tram: float = 0.0
    dat_nguong: bool = False
    ty_le_dat_lan_truoc: float | None = None
    ket_qua_chi_tiet: list[KetQuaCauHoi] = Field(default_factory=list)


def nap_bo_cau_hoi(duong_dan: Path) -> list[dict[str, Any]]:
    """Nạp danh sách 40 câu hỏi từ tệp YAML."""
    if not duong_dan.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp bộ câu hỏi tại {duong_dan}")
    noi_dung = duong_dan.read_text(encoding="utf-8")
    du_lieu = yaml.safe_load(noi_dung)
    if not isinstance(du_lieu, list):
        raise TypeError("Định dạng bộ câu hỏi không hợp lệ: mong đợi danh sách")
    return du_lieu


def _la_loi_gioi_han_toc_do(thong_diep_loi: str) -> bool:
    """Nhận diện lỗi giới hạn tốc độ (429, Rate limit, Resource exhausted, Quota)."""
    chuoi = thong_diep_loi.lower()
    tu_khoa = ["429", "rate limit", "ratelimit", "resource_exhausted", "quota", "too many requests"]
    return any(tk in chuoi for tk in tu_khoa)


async def _thuc_hien_mot_lan_goi(
    cau_hoi_item: dict[str, Any],
    tang: str,
    lan: int,
    nguoi_danh_gia: NguoiDung,
) -> BanGhiLanChay:
    """Thực hiện một lần gọi mô hình và chấm điểm, bảo đảm an toàn dữ liệu."""
    ma = str(cau_hoi_item.get("ma", ""))
    cau_hoi = str(cau_hoi_item.get("cau_hoi", ""))
    nhay_cam = bool(cau_hoi_item.get("nhay_cam", False))

    # Tuân thủ Quy tắc tuyệt đối 2: Không gửi câu hỏi nhạy cảm ra đám mây
    if nhay_cam and tang not in ("local1", "local2"):
        return BanGhiLanChay(
            lan=lan,
            trang_thai="BO_QUA",
            ly_do_cham="Bỏ qua do dữ liệu nhãn NHAY_CAM không gửi ra đám mây (Quy tắc 2).",
            dat=True,  # Không tính là trượt
            lop_cham="chinh_sach",
        )

    nhan_du_lieu = NhanDuLieu.NHAY_CAM if nhay_cam else NhanDuLieu.THUONG
    ma_yeu_cau = f"eval-{tang}-{ma}-{lan}-{uuid.uuid4().hex[:6]}"

    try:
        # Dựng ngữ cảnh giống luồng chat thật: che dữ liệu cá nhân, lời nhắc hệ thống,
        # câu hỏi thường gặp liên quan và khối ranh giới; khôi phục trước khi chấm
        kq_che = che_du_lieu_ca_nhan(cau_hoi)
        chuoi = xac_dinh_chuoi(
            nguoi_danh_gia,
            nhan_du_lieu,
            che_do=cau_hinh.che_do_dinh_tuyen,
            cau_hinh_he_thong=cau_hinh,
        ).chuoi
        tin_nhan = dung_ngu_canh([], kq_che.van_ban_da_che, chuoi, ma_yeu_cau=ma_yeu_cau).danh_sach

        kq: KetQuaGoi = await goi_mo_hinh(
            tin_nhan,
            nguoi=nguoi_danh_gia,
            ma_yeu_cau=ma_yeu_cau,
            nhan_du_lieu=nhan_du_lieu,
            ep_tang=tang,
            muc_dich="danh_gia",
        )
        kd_ra = await kiem_duyet_dau_ra(kq.noi_dung, nguoi_danh_gia)
        tra_loi = kq_che.restore(kd_ra.noi_dung_thay_the or kq.noi_dung)
        kq_cham = await cham_diem(cau_hoi_item, tra_loi, ma_yeu_cau=ma_yeu_cau)

        return BanGhiLanChay(
            lan=lan,
            noi_dung=tra_loi,
            do_tre_ms=kq.do_tre_ms,
            toc_do_tok_s=kq.toc_do_tok_s,
            token_vao=kq.token_vao,
            token_ra=kq.token_ra,
            chi_phi_usd=kq.chi_phi_usd,
            dat=kq_cham.dat,
            lop_cham=kq_cham.lop,
            ly_do_cham=kq_cham.ly_do,
            trang_thai="THANH_CONG",
        )
    except Exception as err:  # noqa: BLE001
        err_msg = str(err)
        # Ep mot tang thi tang do het luot thu lai se thanh "het chuoi du phong"; ly do 429
        # nam trong danh_sach_ly_do chu khong nam trong thong diep tong quat
        if isinstance(err, LoiHetChuoiDuPhong):
            err_msg = f"{err_msg} | {' | '.join(err.danh_sach_ly_do.values())}"
        if _la_loi_gioi_han_toc_do(err_msg):
            logger.warning("[%s] Tầng %s bị giới hạn tần suất: %s", ma_yeu_cau, tang, err_msg)
            return BanGhiLanChay(
                lan=lan,
                trang_thai="GIOI_HAN",
                ly_do_cham=f"Giới hạn tần suất gọi: {err_msg[:120]}",
                dat=False,
                lop_cham="he_thong",
            )
        logger.error("[%s] Lỗi khi gọi tầng %s cho câu %s: %s", ma_yeu_cau, tang, ma, err)
        return BanGhiLanChay(
            lan=lan,
            trang_thai="LOI",
            ly_do_cham=f"Lỗi: {err_msg[:120]}",
            dat=False,
            lop_cham="he_thong",
        )


async def danh_gia_tang(
    tang: str,
    danh_sach_cau_hoi: list[dict[str, Any]],
    so_lan: int = 3,
    bo_qua_warmup: bool = True,
) -> ThongKeTang:
    """Đánh giá toàn bộ câu hỏi trên một tầng duy nhất, chạy tuần tự."""
    nguoi_danh_gia = NguoiDung(
        id=999,
        email="eval@vidu.com",
        ho_ten="Chuyên viên Đánh giá",
        vai_tro="quan_tri",
    )

    # Khởi động (Warmup) cho local1 và local2 để nạp model vào GPU
    if bo_qua_warmup and tang in ("local1", "local2") and danh_sach_cau_hoi:
        try:
            logger.info("Chạy khởi động (warmup) cho tầng %s...", tang)
            cau_warmup = danh_sach_cau_hoi[0]
            await _thuc_hien_mot_lan_goi(cau_warmup, tang, 0, nguoi_danh_gia)
        except Exception as err:  # noqa: BLE001
            logger.warning("Lượt warmup tầng %s bỏ qua hoặc lỗi nhẹ: %s", tang, err)

    ket_qua_chi_tiet: list[KetQuaCauHoi] = []
    danh_sach_do_tre: list[float] = []
    danh_sach_toc_do: list[float] = []
    tong_chi_phi = 0.0
    tong_so_ky_tu_tra_loi = 0
    so_cau_tra_loi_duoc = 0

    so_cau_dat = 0
    so_cau_bo_qua = 0
    so_cau_gioi_han = 0

    for idx, item in enumerate(danh_sach_cau_hoi, start=1):
        ma = str(item.get("ma", f"VN-{idx:03d}"))
        loai = str(item.get("loai", "co_ban"))
        cau_hoi = str(item.get("cau_hoi", ""))
        nhay_cam = bool(item.get("nhay_cam", False))

        cac_lan: list[BanGhiLanChay] = []
        for lan in range(1, so_lan + 1):
            ban_ghi = await _thuc_hien_mot_lan_goi(item, tang, lan, nguoi_danh_gia)
            cac_lan.append(ban_ghi)
            # Thêm khoảng nghỉ nhỏ giữa các lượt gọi đám mây để tránh nghẽn quota
            if tang not in ("local1", "local2"):
                await asyncio.sleep(0.5)

        # Tổng hợp kết quả các lần chạy của câu hỏi
        lan_thanh_cong = [b for b in cac_lan if b.trang_thai == "THANH_CONG"]
        la_bo_qua = any(b.trang_thai == "BO_QUA" for b in cac_lan)
        la_gioi_han = all(b.trang_thai == "GIOI_HAN" for b in cac_lan)

        if la_bo_qua:
            so_cau_bo_qua += 1
            dat_trung_vi = True
            trang_thai_chung = "BO_QUA"
            do_tre_tv = 0.0
            toc_do_tv = 0.0
            chi_phi_tb = 0.0
        elif la_gioi_han:
            so_cau_gioi_han += 1
            dat_trung_vi = False
            trang_thai_chung = "GIOI_HAN"
            do_tre_tv = 0.0
            toc_do_tv = 0.0
            chi_phi_tb = 0.0
        elif lan_thanh_cong:
            so_lan_dat = sum(1 for b in lan_thanh_cong if b.dat)
            dat_trung_vi = so_lan_dat >= (len(lan_thanh_cong) / 2.0)
            if dat_trung_vi:
                so_cau_dat += 1
            trang_thai_chung = "THANH_CONG"
            do_tre_tv = statistics.median([b.do_tre_ms for b in lan_thanh_cong])
            toc_do_tv = statistics.median([b.toc_do_tok_s for b in lan_thanh_cong])
            chi_phi_tb = statistics.mean([b.chi_phi_usd for b in lan_thanh_cong])

            danh_sach_do_tre.append(do_tre_tv)
            danh_sach_toc_do.append(toc_do_tv)
            tong_chi_phi += sum(b.chi_phi_usd for b in lan_thanh_cong)
            for b in lan_thanh_cong:
                if b.noi_dung:
                    tong_so_ky_tu_tra_loi += len(b.noi_dung)
                    so_cau_tra_loi_duoc += 1
        else:
            dat_trung_vi = False
            trang_thai_chung = "LOI"
            do_tre_tv = 0.0
            toc_do_tv = 0.0
            chi_phi_tb = 0.0

        kq_cau = KetQuaCauHoi(
            ma=ma,
            loai=loai,
            cau_hoi=cau_hoi,
            nhay_cam=nhay_cam,
            lan_chay=cac_lan,
            dat_trung_vi=dat_trung_vi,
            do_tre_trung_vi_ms=round(do_tre_tv, 2),
            toc_do_trung_vi_tok_s=round(toc_do_tv, 2),
            chi_phi_trung_binh_usd=round(chi_phi_tb, 6),
            trang_thai_chung=trang_thai_chung,
        )
        ket_qua_chi_tiet.append(kq_cau)

    tong_cau = len(danh_sach_cau_hoi)
    # Tỷ lệ đạt tính trên từng lượt chạy (N lần mỗi câu); lượt BỎ QUA và GIỚI HẠN không tính
    dem_loai: dict[str, list[int]] = {}
    for kq_cau in ket_qua_chi_tiet:
        for b in kq_cau.lan_chay:
            if b.trang_thai in ("BO_QUA", "GIOI_HAN"):
                continue
            dem = dem_loai.setdefault(kq_cau.loai, [0, 0])
            dem[0] += 1 if b.dat else 0
            dem[1] += 1
    tong_dat = sum(d[0] for d in dem_loai.values())
    tong_xet = sum(d[1] for d in dem_loai.values())
    ty_le_dat = round(tong_dat / tong_xet * 100, 2) if tong_xet else 0.0
    ty_le_theo_loai = {
        loai: round(d[0] / d[1] * 100, 2) for loai, d in dem_loai.items() if d[1]
    }
    nguong_phan_tram = cau_hinh.cai_dat_chung.nguong_dat_danh_gia * 100

    p50_tre = (
        round(statistics.median(danh_sach_do_tre), 2)
        if danh_sach_do_tre
        else 0.0
    )
    if len(danh_sach_do_tre) >= 2:
        sorted_tre = sorted(danh_sach_do_tre)
        idx_95 = int(len(sorted_tre) * 0.95)
        p95_tre = round(sorted_tre[min(idx_95, len(sorted_tre) - 1)], 2)
    elif danh_sach_do_tre:
        p95_tre = p50_tre
    else:
        p95_tre = 0.0

    p50_toc_do = (
        round(statistics.median(danh_sach_toc_do), 2)
        if danh_sach_toc_do
        else 0.0
    )
    do_dai_tb = (
        round(tong_so_ky_tu_tra_loi / so_cau_tra_loi_duoc, 1)
        if so_cau_tra_loi_duoc > 0
        else 0.0
    )

    return ThongKeTang(
        tang=tang,
        tong_so_cau=tong_cau,
        so_cau_dat=so_cau_dat,
        so_cau_bo_qua=so_cau_bo_qua,
        so_cau_gioi_han=so_cau_gioi_han,
        ty_le_dat_phan_tram=ty_le_dat,
        do_tre_p50_ms=p50_tre,
        do_tre_p95_ms=p95_tre,
        toc_do_p50_tok_s=p50_toc_do,
        tong_chi_phi_usd=round(tong_chi_phi, 6),
        do_dai_tra_loi_tb=do_dai_tb,
        ty_le_dat_theo_loai=ty_le_theo_loai,
        nguong_dat_phan_tram=nguong_phan_tram,
        dat_nguong=tong_xet > 0
        and ty_le_dat >= nguong_phan_tram
        and all(tl >= nguong_phan_tram for tl in ty_le_theo_loai.values()),
        ket_qua_chi_tiet=ket_qua_chi_tiet,
    )


def _o_phan_tram(gia_tri: float | None) -> str:
    """Định dạng ô phần trăm; thiếu số liệu thì in '-'."""
    return "-" if gia_tri is None else f"{gia_tri:.1f}"


def in_bang_thong_ke_6_cot(danh_sach_thong_ke: list[ThongKeTang]) -> None:
    """In bảng so sánh: mỗi cột là một nơi trả lời (local1, local2, 1, 2, 3, 4).

    Hàng: tỷ lệ đạt theo loại, tỷ lệ chung, độ trễ trung vị, p95, tok/s trung vị,
    chi phí cả bộ, độ dài trung bình, chênh lệch so với lần chạy trước và kết luận ngưỡng.
    """
    cot = [
        f"{tk.tang} (TK)" if tk.tang == TANG_THAM_KHAO else tk.tang for tk in danh_sach_thong_ke
    ]
    cac_hang: list[tuple[str, list[str]]] = []
    for loai in DANH_SACH_LOAI:
        cac_hang.append(
            (
                f"Đạt {loai} (%)",
                [_o_phan_tram(tk.ty_le_dat_theo_loai.get(loai)) for tk in danh_sach_thong_ke],
            )
        )
    cac_hang += [
        ("Đạt chung (%)", [_o_phan_tram(tk.ty_le_dat_phan_tram) for tk in danh_sach_thong_ke]),
        ("Độ trễ p50 (ms)", [f"{tk.do_tre_p50_ms:.0f}" for tk in danh_sach_thong_ke]),
        ("Độ trễ p95 (ms)", [f"{tk.do_tre_p95_ms:.0f}" for tk in danh_sach_thong_ke]),
        ("Tok/s p50", [f"{tk.toc_do_p50_tok_s:.1f}" for tk in danh_sach_thong_ke]),
        ("Chi phí cả bộ ($)", [f"{tk.tong_chi_phi_usd:.4f}" for tk in danh_sach_thong_ke]),
        ("Độ dài TB (ký tự)", [f"{tk.do_dai_tra_loi_tb:.0f}" for tk in danh_sach_thong_ke]),
        (
            "Câu BỎ QUA / GIỚI HẠN",
            [f"{tk.so_cau_bo_qua} / {tk.so_cau_gioi_han}" for tk in danh_sach_thong_ke],
        ),
        (
            "So lần trước (điểm %)",
            [
                "-"
                if tk.ty_le_dat_lan_truoc is None
                else f"{tk.ty_le_dat_phan_tram - tk.ty_le_dat_lan_truoc:+.1f}"
                for tk in danh_sach_thong_ke
            ],
        ),
        (
            "Ngưỡng",
            [
                "tham khảo"
                if tk.tang == TANG_THAM_KHAO
                else ("ĐẠT" if tk.dat_nguong else "CHƯA ĐẠT")
                for tk in danh_sach_thong_ke
            ],
        ),
    ]

    rong_nhan = max(len(nhan) for nhan, _ in cac_hang)
    rong_cot = max([12, *(len(c) + 2 for c in cot)])
    tieu_de = f"{'Chỉ số':<{rong_nhan}} | " + " | ".join(f"{c:>{rong_cot}}" for c in cot)
    duong_ke = "-" * len(tieu_de)
    print("\n" + duong_ke)
    print(tieu_de)
    print(duong_ke)
    for nhan, cac_o in cac_hang:
        print(f"{nhan:<{rong_nhan}} | " + " | ".join(f"{o:>{rong_cot}}" for o in cac_o))
    print(duong_ke)
    if danh_sach_thong_ke:
        print(
            f"Ngưỡng đạt: {danh_sach_thong_ke[0].nguong_dat_phan_tram:.0f}% cho tỷ lệ chung "
            "và từng loại (config/models.yaml, cai_dat_chung.nguong_dat_danh_gia)\n"
        )


def tim_bat_dong_giua_cac_tang(
    danh_sach_thong_ke: list[ThongKeTang],
) -> list[tuple[str, str, dict[str, bool]]]:
    """Tìm danh sách các câu hỏi bị bất đồng (disagreement) giữa các tầng mô hình.

    Tầng 2 (OpenRouter free) bị loại khỏi tính năng này theo yêu cầu.
    """
    cac_tang_xet = [tk for tk in danh_sach_thong_ke if tk.tang != TANG_THAM_KHAO]
    if len(cac_tang_xet) < 2:
        return []

    danh_sach_bat_dong: list[tuple[str, str, dict[str, bool]]] = []
    so_cau = cac_tang_xet[0].tong_so_cau

    for idx in range(so_cau):
        ma = cac_tang_xet[0].ket_qua_chi_tiet[idx].ma
        cau_hoi = cac_tang_xet[0].ket_qua_chi_tiet[idx].cau_hoi
        ket_qua_tang: dict[str, bool] = {}

        for tk in cac_tang_xet:
            if idx < len(tk.ket_qua_chi_tiet):
                kq = tk.ket_qua_chi_tiet[idx]
                if kq.trang_thai_chung == "THANH_CONG":
                    ket_qua_tang[tk.tang] = kq.dat_trung_vi

        # Nếu có cả True và False giữa các tầng -> Bất đồng
        gia_tri_dat = set(ket_qua_tang.values())
        if len(gia_tri_dat) > 1:
            danh_sach_bat_dong.append((ma, cau_hoi, ket_qua_tang))

    return danh_sach_bat_dong


def in_danh_sach_bat_dong(danh_sach_bat_dong: list[tuple[str, str, dict[str, bool]]]) -> None:
    """In chi tiết các câu hỏi bị bất đồng kết quả chấm giữa các tầng."""
    if not danh_sach_bat_dong:
        print("Không có bất đồng kết quả chấm giữa các tầng đã đánh giá.")
        return

    print(f"\n--- DANH SÁCH BẤT ĐỒNG GIỮA CÁC TẦNG ({len(danh_sach_bat_dong)} câu) ---")
    for ma, cau_hoi, kq_tang in danh_sach_bat_dong:
        dong_kq = ", ".join(f"{t}: {'ĐẠT' if d else 'TRƯỢT'}" for t, d in kq_tang.items())
        print(f"[{ma}] {cau_hoi[:60]}... -> {dong_kq}")
    print("------------------------------------------------------------------\n")


def doc_ty_le_lan_truoc(tang: str, thu_muc_ra: Path) -> float | None:
    """Tỷ lệ đạt chung của lần chạy gần nhất đã lưu cho tầng (tệp <ngày>_<tầng>.json)."""
    cac_tep = sorted(thu_muc_ra.glob(f"*_{tang}.json"))
    if not cac_tep:
        return None
    try:
        du_lieu = json.loads(cac_tep[-1].read_text(encoding="utf-8"))
        return float(du_lieu["ty_le_dat_phan_tram"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def luu_ket_qua_json(tk: ThongKeTang, thu_muc_ra: Path) -> Path:
    """Lưu kết quả của một tầng vào ket_qua_eval/<ngày>_<tầng>.json."""
    thu_muc_ra.mkdir(parents=True, exist_ok=True)
    bay_gio = datetime.now(MUI_GIO_VN)
    tep_ra = thu_muc_ra / f"{bay_gio:%Y-%m-%d}_{tk.tang}.json"
    du_lieu_xuat = {"thoi_gian": bay_gio.isoformat(), **tk.model_dump()}
    tep_ra.write_text(json.dumps(du_lieu_xuat, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Đã lưu kết quả đánh giá tầng %s tại: %s", tk.tang, tep_ra)
    return tep_ra


async def chay_danh_gia(
    danh_sach_tang: list[str],
    duong_dan_bo_cau_hoi: Path,
    so_lan: int = 3,
    thu_muc_ra: Path | None = None,
) -> list[ThongKeTang]:
    """Hàm điều phối đánh giá chính."""
    cau_hoi = nap_bo_cau_hoi(duong_dan_bo_cau_hoi)
    logger.info("Bắt đầu đánh giá %d câu hỏi trên các tầng: %s (mỗi câu %d lần)", len(cau_hoi), danh_sach_tang, so_lan)

    thu_muc_luu = thu_muc_ra or THU_MUC_KET_QUA_MAC_DINH
    tat_ca_thong_ke: list[ThongKeTang] = []
    for tang in danh_sach_tang:
        logger.info(">>> Đang đánh giá tầng: %s", tang)
        tk = await danh_gia_tang(tang, cau_hoi, so_lan=so_lan)
        # Tầng 2 tự chọn model miễn phí mỗi lượt nên không so với lần trước
        if tang != TANG_THAM_KHAO:
            tk.ty_le_dat_lan_truoc = doc_ty_le_lan_truoc(tang, thu_muc_luu)
        luu_ket_qua_json(tk, thu_muc_luu)
        tat_ca_thong_ke.append(tk)

    in_bang_thong_ke_6_cot(tat_ca_thong_ke)

    bat_dong = tim_bat_dong_giua_cac_tang(tat_ca_thong_ke)
    in_danh_sach_bat_dong(bat_dong)

    return tat_ca_thong_ke


def main() -> None:
    """Điểm nhập dòng lệnh CLI cho runner."""
    parser = argparse.ArgumentParser(description="Bộ chạy đánh giá chất lượng các tầng mô hình.")
    parser.add_argument(
        "--tang",
        type=str,
        default="local1",
        help="Tầng cần đánh giá: local1, local2, 1, 2, 3, 4 hoặc all (mặc định: local1)",
    )
    parser.add_argument(
        "--lan",
        type=int,
        default=3,
        help="Số lần chạy mỗi câu hỏi (mặc định: 3)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=THU_MUC_KET_QUA_MAC_DINH,
        help="Thư mục xuất kết quả JSON (mặc định: ket_qua_eval/)",
    )
    parser.add_argument(
        "--bo-cau-hoi",
        type=Path,
        default=DUONG_DAN_BO_CAU_HOI_MAC_DINH,
        help="Đường dẫn tệp YAML bộ câu hỏi (mặc định: eval/bo_cau_hoi.yaml)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.tang == "all":
        danh_sach_tang = list(DANH_SACH_TANG_CHUAN)
    else:
        danh_sach_tang = [t.strip() for t in args.tang.split(",") if t.strip()]

    asyncio.run(chay_danh_gia(danh_sach_tang, args.bo_cau_hoi, so_lan=args.lan, thu_muc_ra=args.out))


if __name__ == "__main__":
    main()
