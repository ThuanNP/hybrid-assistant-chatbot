"""Tính toán và theo dõi chi phí gọi mô hình ngôn ngữ cùng kiểm soát ngân sách."""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import CauHinhHeThong, cau_hinh
from app.core.csdl import LuotGoiModel, lay_engine_dong_bo
from app.core.thoi_gian import hom_nay_vn, khoang_ngay_vn

logger = logging.getLogger(__name__)

__all__ = [
    "KhoLuotGoi",
    "KhoLuotGoiBoNho",
    "KhoLuotGoiPostgres",
    "LuotGoi",
    "bao_cao_chi_phi",
    "chuan_hoa_muc_dich",
    "kho_luot_goi_mac_dinh",
    "kiem_tra_canh_bao_ty_le_roi_tang",
    "kiem_tra_ngan_sach",
    "tinh_ty_le_roi_tang",
    "uoc_tinh_chi_phi",
]


MucDichGoi = Literal["chat", "tieu_de", "danh_gia", "nhung"]


def chuan_hoa_muc_dich(muc_dich: str | None) -> MucDichGoi:
    """Ánh xạ mục đích gọi về giá trị hợp lệ; giá trị lạ tính là lượt hỏi (chat)."""
    if muc_dich == "tieu_de":
        return "tieu_de"
    if muc_dich == "danh_gia":
        return "danh_gia"
    if muc_dich == "nhung":
        return "nhung"
    return "chat"


class LuotGoi(BaseModel):
    """Thông tin chi tiết một lượt gọi mô hình LLM theo Quy tắc kỹ thuật 7."""

    thoi_diem: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Thời điểm thực hiện lượt gọi",
    )
    nguoi_id: str = Field(description="Định danh người dùng thực hiện yêu cầu")
    nguon: str = Field(description="Nguồn phục vụ: local hoặc dam_may")
    tang: int = Field(ge=0, description="Tầng mô hình đã phục vụ")
    bac: str | None = Field(default=None, description="Bậc mô hình local: chinh hoặc nho")
    model: str = Field(description="Tên model đã thực thi")
    token_vao: int = Field(ge=0, description="Số lượng token đầu vào (prompt)")
    token_ra: int = Field(ge=0, description="Số lượng token đầu ra (completion)")
    chi_phi_usd: float = Field(ge=0.0, description="Chi phí tính bằng USD (tầng 0 là 0.0)")
    do_tre_ms: float = Field(ge=0.0, description="Độ trễ tổng cộng tính bằng mili-giây")
    thoi_gian_nap_ms: float = Field(ge=0.0, description="Thời gian nạp model tính bằng ms")
    toc_do_tok_s: float = Field(ge=0.0, description="Tốc độ sinh token (tok/s)")
    thanh_cong: bool = Field(default=True, description="Trạng thái thực thi có thành công không")
    ma_yeu_cau: str = Field(description="Mã định danh yêu cầu xuyên suốt")
    roi_tang: bool = Field(
        default=False,
        description="Đánh dấu lượt gọi không được tầng đầu tiên của chuỗi phục vụ",
    )
    ly_do_that_bai_tang_dau: str | None = Field(
        default=None,
        max_length=100,
        description="Loại lỗi khiến tầng đầu tiên thất bại, không chứa nội dung tin nhắn",
    )
    muc_dich: MucDichGoi = Field(
        default="chat",
        description=(
            "chat: lượt hỏi của người dùng; tieu_de: lời gọi nền đặt tiêu đề; "
            "danh_gia: lời gọi của bộ đánh giá; nhung: lời gọi nhúng vector"
        ),
    )


class KhoLuotGoi(ABC):
    """Giao diện trừu tượng cho kho lưu trữ lịch sử các lượt gọi mô hình."""

    @abstractmethod
    def ghi(self, luot_goi: LuotGoi) -> None:
        """Ghi nhận một bản ghi lượt gọi vào kho lưu trữ."""

    @abstractmethod
    def lay_tat_ca(self) -> list[LuotGoi]:
        """Lấy toàn bộ danh sách lượt gọi đã lưu trữ."""

    @abstractmethod
    def lay_trong_ngay(self, ngay: date | None = None) -> list[LuotGoi]:
        """Lấy danh sách các lượt gọi phát sinh trong một ngày cụ thể (mặc định hôm nay)."""

    @abstractmethod
    def lay_trong_khoang(self, tu_thoi_diem: datetime, den_thoi_diem: datetime) -> list[LuotGoi]:
        """Lấy danh sách các lượt gọi trong một khoảng thời gian nhất định."""

    @abstractmethod
    def tinh_tong_chi_phi_ngay(self, ngay: date | None = None) -> float:
        """Tính tổng chi phí gọi mô hình đám mây trong một ngày cụ thể."""


class KhoLuotGoiBoNho(KhoLuotGoi):
    """Hiện thực lưu trữ lượt gọi trong bộ nhớ ram cho Giai đoạn 2."""

    def __init__(self) -> None:
        self._danh_sach: list[LuotGoi] = []

    def xoa_toan_bo(self) -> None:
        """Xoá sạch dữ liệu lượt gọi trong bộ nhớ, phục vụ kiểm thử."""
        self._danh_sach.clear()

    def ghi(self, luot_goi: LuotGoi) -> None:
        """Ghi nhận bản ghi lượt gọi."""
        self._danh_sach.append(luot_goi)

    def lay_tat_ca(self) -> list[LuotGoi]:
        """Trả về toàn bộ danh sách lượt gọi."""
        return list(self._danh_sach)

    def lay_trong_ngay(self, ngay: date | None = None) -> list[LuotGoi]:
        """Lấy các lượt gọi trong ngày chỉ định theo giờ Việt Nam."""
        tu, den = khoang_ngay_vn(ngay or hom_nay_vn())
        return [lg for lg in self._danh_sach if tu <= lg.thoi_diem < den]

    def lay_trong_khoang(self, tu_thoi_diem: datetime, den_thoi_diem: datetime) -> list[LuotGoi]:
        """Lấy các lượt gọi nằm trong khoảng thời gian [tu_thoi_diem, den_thoi_diem]."""
        return [
            lg
            for lg in self._danh_sach
            if tu_thoi_diem <= lg.thoi_diem <= den_thoi_diem
        ]

    def tinh_tong_chi_phi_ngay(self, ngay: date | None = None) -> float:
        """Tính tổng chi phí USD các lượt gọi trong ngày."""
        cac_luot = self.lay_trong_ngay(ngay)
        tong = sum(lg.chi_phi_usd for lg in cac_luot)
        return round(tong, 6)


class KhoLuotGoiPostgres(KhoLuotGoi):
    """Hiện thực lưu trữ và truy vấn lượt gọi mô hình trên cơ sở dữ liệu PostgreSQL."""

    def __init__(self) -> None:
        self._engine = lay_engine_dong_bo()

    def ghi(self, luot_goi: LuotGoi) -> None:
        """Ghi nhận một bản ghi lượt gọi vào bảng luot_goi của PostgreSQL."""
        ban_ghi = LuotGoiModel(
            thoi_diem=luot_goi.thoi_diem,
            nguoi_id=str(luot_goi.nguoi_id),
            nguon=str(luot_goi.nguon),
            tang=luot_goi.tang,
            bac=luot_goi.bac,
            model=luot_goi.model,
            token_vao=luot_goi.token_vao,
            token_ra=luot_goi.token_ra,
            chi_phi_usd=luot_goi.chi_phi_usd,
            do_tre_ms=luot_goi.do_tre_ms,
            thoi_gian_nap_ms=luot_goi.thoi_gian_nap_ms,
            toc_do_tok_s=luot_goi.toc_do_tok_s,
            thanh_cong=luot_goi.thanh_cong,
            ma_yeu_cau=luot_goi.ma_yeu_cau,
            roi_tang=luot_goi.roi_tang,
            ly_do_that_bai_tang_dau=luot_goi.ly_do_that_bai_tang_dau,
            muc_dich=luot_goi.muc_dich,
        )
        try:
            with Session(self._engine) as phien:
                phien.add(ban_ghi)
                phien.commit()
        except Exception as err:  # noqa: BLE001
            logger.warning("Ghi nhận lượt gọi vào cơ sở dữ liệu thất bại: %s", err)

    def _chuyen_doi_model_sang_schema(self, row: LuotGoiModel) -> LuotGoi:
        """Chuyển đổi thực thể ORM LuotGoiModel sang mô hình dữ liệu LuotGoi."""
        return LuotGoi(
            thoi_diem=row.thoi_diem,
            nguoi_id=row.nguoi_id,
            nguon=row.nguon,
            tang=row.tang,
            bac=row.bac,
            model=row.model,
            token_vao=row.token_vao,
            token_ra=row.token_ra,
            chi_phi_usd=row.chi_phi_usd,
            do_tre_ms=row.do_tre_ms,
            thoi_gian_nap_ms=row.thoi_gian_nap_ms,
            toc_do_tok_s=row.toc_do_tok_s,
            thanh_cong=row.thanh_cong,
            ma_yeu_cau=row.ma_yeu_cau,
            roi_tang=row.roi_tang,
            ly_do_that_bai_tang_dau=row.ly_do_that_bai_tang_dau,
            muc_dich=chuan_hoa_muc_dich(row.muc_dich),
        )

    def lay_tat_ca(self) -> list[LuotGoi]:
        """Truy vấn toàn bộ danh sách lượt gọi từ PostgreSQL."""
        with Session(self._engine) as phien:
            cau_lenh = select(LuotGoiModel).order_by(LuotGoiModel.thoi_diem.asc())
            ket_qua = phien.scalars(cau_lenh).all()
            return [self._chuyen_doi_model_sang_schema(r) for r in ket_qua]

    def lay_trong_khoang(
        self, tu_thoi_diem: datetime, den_thoi_diem: datetime
    ) -> list[LuotGoi]:
        """Truy vấn danh sách lượt gọi trong khoảng thời gian [tu_thoi_diem, den_thoi_diem]."""
        with Session(self._engine) as phien:
            cau_lenh = (
                select(LuotGoiModel)
                .where(
                    LuotGoiModel.thoi_diem >= tu_thoi_diem,
                    LuotGoiModel.thoi_diem <= den_thoi_diem,
                )
                .order_by(LuotGoiModel.thoi_diem.asc())
            )
            ket_qua = phien.scalars(cau_lenh).all()
            return [self._chuyen_doi_model_sang_schema(r) for r in ket_qua]

    def lay_trong_ngay(self, ngay: date | None = None) -> list[LuotGoi]:
        """Lấy danh sách các lượt gọi trong ngày theo giờ Việt Nam."""
        tu, den = khoang_ngay_vn(ngay or hom_nay_vn())
        with Session(self._engine) as phien:
            cau_lenh = (
                select(LuotGoiModel)
                .where(LuotGoiModel.thoi_diem >= tu, LuotGoiModel.thoi_diem < den)
                .order_by(LuotGoiModel.thoi_diem.asc())
            )
            ket_qua = phien.scalars(cau_lenh).all()
            return [self._chuyen_doi_model_sang_schema(r) for r in ket_qua]

    def tinh_tong_chi_phi_ngay(self, ngay: date | None = None) -> float:
        """Tính tổng chi phí gọi mô hình trong ngày (giờ Việt Nam) từ bảng luot_goi."""
        tu, den = khoang_ngay_vn(ngay or hom_nay_vn())
        with Session(self._engine) as phien:
            cau_lenh = select(
                func.coalesce(func.sum(LuotGoiModel.chi_phi_usd), 0.0)
            ).where(LuotGoiModel.thoi_diem >= tu, LuotGoiModel.thoi_diem < den)
            tong = phien.scalar(cau_lenh)
            return round(float(tong or 0.0), 6)


kho_luot_goi_mac_dinh = KhoLuotGoiPostgres()


def uoc_tinh_chi_phi(
    tang: int,
    token_vao: int,
    token_ra: int,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> float:
    """Ước tính chi phí gọi mô hình (USD) dựa trên số lượng token và bảng giá YAML.

    Tầng 0 luôn trả về 0.0 USD. Các tầng đám mây tính theo đơn giá trên 1 triệu token.
    """
    if tang == 0:
        return 0.0

    cfg = cau_hinh_he_thong or cau_hinh
    for tang_dm in cfg.chuoi_dam_may:
        if tang_dm.tang == tang:
            chi_phi = (
                token_vao * tang_dm.gia_vao_usd_moi_trieu
                + token_ra * tang_dm.gia_ra_usd_moi_trieu
            ) / 1_000_000.0
            return round(chi_phi, 6)

    return 0.0


def kiem_tra_ngan_sach(
    ngan_sach_ngay_usd: float | None = None,
    nguong_canh_bao: float | None = None,
    kho: KhoLuotGoi | None = None,
    cfg: CauHinhHeThong | None = None,
) -> tuple[bool, bool, float]:
    """Kiểm tra tổng chi phí trong ngày so với ngân sách và ngưỡng cảnh báo.

    Trả (vuot_ngan_sach, vuot_canh_bao, tong_chi_phi).
    """
    ch = cfg or cau_hinh
    ns = (
        ngan_sach_ngay_usd
        if ngan_sach_ngay_usd is not None
        else ch.ngan_sach_ngay_usd
    )
    nguong = (
        nguong_canh_bao
        if nguong_canh_bao is not None
        else ch.cai_dat_chung.nguong_canh_bao_ngan_sach
    )
    k = kho or kho_luot_goi_mac_dinh
    tong_chi_phi = k.tinh_tong_chi_phi_ngay()

    vuot_ngan_sach = tong_chi_phi >= ns
    vuot_canh_bao = tong_chi_phi >= (ns * nguong)
    return vuot_ngan_sach, vuot_canh_bao, tong_chi_phi


def tinh_ty_le_roi_tang(
    kho: KhoLuotGoi | None = None,
    gio_gan_nhat: int = 1,
) -> tuple[float, str | None]:
    """Tính tỷ lệ (0-1) lượt hỏi không được tầng đầu của chuỗi phục vụ trong khoảng vừa qua.

    Chỉ xét lượt hỏi của người dùng (muc_dich=chat), gồm cả lượt hết chuỗi (thanh_cong=False).
    Trả (ty_le, loai_loi_tang_dau_gan_nhat).
    """
    k = kho or kho_luot_goi_mac_dinh
    den_thoi_diem = datetime.now(timezone.utc)
    tu_thoi_diem = den_thoi_diem - timedelta(hours=gio_gan_nhat)

    danh_sach = [
        lg for lg in k.lay_trong_khoang(tu_thoi_diem, den_thoi_diem) if lg.muc_dich == "chat"
    ]
    if not danh_sach:
        return 0.0, None

    danh_sach_roi = [lg for lg in danh_sach if lg.roi_tang]
    ty_le = round(len(danh_sach_roi) / len(danh_sach), 4)

    ly_do_gan_nhat: str | None = None
    for lg in reversed(danh_sach_roi):
        if lg.ly_do_that_bai_tang_dau:
            ly_do_gan_nhat = lg.ly_do_that_bai_tang_dau
            break

    return ty_le, ly_do_gan_nhat


def kiem_tra_canh_bao_ty_le_roi_tang(
    kho: KhoLuotGoi | None = None,
    cfg: CauHinhHeThong | None = None,
) -> None:
    """Kiểm tra và ghi cảnh báo nếu tỷ lệ rơi tầng 1 giờ qua vượt ngưỡng cho phép."""
    ch = cfg or cau_hinh
    nguong = ch.cai_dat_chung.nguong_ty_le_roi_tang
    ty_le, ly_do = tinh_ty_le_roi_tang(kho=kho, gio_gan_nhat=1)

    if ty_le > nguong:
        logger.warning(
            "CẢNH BÁO TỶ LỆ RƠI TẦNG: Tỷ lệ rơi tầng 1 giờ qua là %.1f%% "
            "(vượt ngưỡng %.1f%%). Lý do hỏng tầng đầu gần nhất: %s",
            ty_le * 100.0,
            nguong * 100.0,
            ly_do or "Không có thông tin",
        )


def bao_cao_chi_phi(
    kho: KhoLuotGoi | None = None,
    cfg: CauHinhHeThong | None = None,
    ngay: date | None = None,
) -> dict[str, Any]:
    """Tổng hợp báo cáo chi phí và tỷ lệ định tuyến trong ngày (giờ Việt Nam).

    Mọi trường ty_le_* là phân số 0-1; riêng phan_tram_da_dung theo thang 0-100.
    Phân rã theo tầng và ty_le_local chỉ tính lượt hỏi (muc_dich=chat) đã được phục vụ;
    chi phí tính trên mọi lượt gọi.
    """
    ch = cfg or cau_hinh
    k = kho or kho_luot_goi_mac_dinh
    tat_ca = k.lay_trong_ngay(ngay)
    cac_luot = [lg for lg in tat_ca if lg.muc_dich == "chat" and lg.thanh_cong]

    chi_phi_hom_nay = round(sum(lg.chi_phi_usd for lg in tat_ca), 6)
    ngan_sach_ngay = ch.ngan_sach_ngay_usd
    phan_tram_dung = (
        round((chi_phi_hom_nay / max(ngan_sach_ngay, 0.0001)) * 100.0, 2)
        if ngan_sach_ngay > 0
        else 0.0
    )

    phan_ra: dict[int, dict[str, Any]] = {}
    so_luot_tang_0 = 0
    tong_luot = len(cac_luot)

    for lg in cac_luot:
        if lg.tang == 0:
            so_luot_tang_0 += 1
        if lg.tang not in phan_ra:
            phan_ra[lg.tang] = {"so_luot": 0, "token": 0, "chi_phi": 0.0}
        phan_ra[lg.tang]["so_luot"] += 1
        phan_ra[lg.tang]["token"] += lg.token_vao + lg.token_ra
        phan_ra[lg.tang]["chi_phi"] = round(
            phan_ra[lg.tang]["chi_phi"] + lg.chi_phi_usd, 6
        )

    ty_le_local = round(so_luot_tang_0 / tong_luot, 4) if tong_luot > 0 else 0.0

    ty_le_roi, _ = tinh_ty_le_roi_tang(kho=k, gio_gan_nhat=1)

    return {
        "chi_phi_hom_nay_usd": chi_phi_hom_nay,
        "ngan_sach_ngay_usd": ngan_sach_ngay,
        "phan_tram_da_dung": phan_tram_dung,
        "phan_ra_theo_tang": phan_ra,
        "ty_le_local": ty_le_local,
        "ty_le_roi_tang": ty_le_roi,
        "nguong_canh_bao_ngan_sach": ch.cai_dat_chung.nguong_canh_bao_ngan_sach,
        "nguong_ty_le_roi_tang": ch.cai_dat_chung.nguong_ty_le_roi_tang,
    }
