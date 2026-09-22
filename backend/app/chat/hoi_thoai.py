"""Quản lý các phiên hội thoại, tin nhắn và lịch sử trao đổi của người dùng.

Chịu trách nhiệm:
1. Tạo mới, truy vấn (bỏ hội thoại đã xoá mềm) và xoá hội thoại (cascade delete lượt).
2. Đọc các lượt theo thứ tự thời gian tăng dần phục vụ ghép ngữ cảnh.
3. Lưu cặp lượt người dùng và lượt trợ lý trong MỘT giao dịch duy nhất.
4. Trích xuất phiên bản lời nhắc từ dòng đầu prompts/he_thong.md.
5. Tự động sinh tiêu đề hội thoại chạy nền ưu tiên bậc nhỏ local sau lượt đầu tiên.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csdl import HoiThoaiModel, LuotModel, lay_sessionmaker_async
from app.core.xac_thuc import NguoiDung
from app.llm.router import KetQuaGoi, goi_mo_hinh

logger = logging.getLogger(__name__)

# Thư mục chứa các tệp lời nhắc Markdown của hệ thống
_THU_MUC_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
_TEP_PROMPT_HE_THONG = _THU_MUC_PROMPTS / "he_thong.md"
_TEP_PROMPT_TIEU_DE = _THU_MUC_PROMPTS / "tieu_de.md"


def doc_phien_ban_loi_nhac(duong_dan: Path | None = None) -> str:
    """Đọc phiên bản lời nhắc hệ thống từ dòng đầu tiên của prompts/he_thong.md."""
    tep = duong_dan or _TEP_PROMPT_HE_THONG
    if not tep.exists():
        return "2026-09-22.1"

    try:
        dong_dau = tep.read_text(encoding="utf-8").splitlines()[0].strip()
        if ":" in dong_dau:
            return dong_dau.split(":", 1)[1].strip()
        return dong_dau
    except Exception as err:  # noqa: BLE001
        logger.warning("Không thể đọc phiên bản lời nhắc từ %s: %s", tep, err)
        return "2026-09-22.1"


def doc_loi_nhac_tieu_de(duong_dan: Path | None = None) -> str:
    """Đọc nội dung lời nhắc hướng dẫn đặt tiêu đề từ prompts/tieu_de.md."""
    tep = duong_dan or _TEP_PROMPT_TIEU_DE
    if not tep.exists():
        return (
            "Bạn là trợ lý AI. Hãy tóm tắt nội dung hội thoại thành một tiêu đề "
            "ngắn gọn tối đa 8 từ tiếng Việt, không dùng dấu ngoặc kép."
        )
    return tep.read_text(encoding="utf-8").strip()


async def tao_hoi_thoai(
    phien: AsyncSession,
    nguoi_id: int,
    tieu_de: str = "Cuộc trò chuyện mới",
) -> HoiThoaiModel:
    """Tạo mới một cuộc hội thoại trong cơ sở dữ liệu."""
    hoi_thoai = HoiThoaiModel(
        nguoi_id=nguoi_id,
        tieu_de=tieu_de,
        da_xoa=False,
    )
    phien.add(hoi_thoai)
    await phien.flush()
    return hoi_thoai


async def lay_hoi_thoai(
    phien: AsyncSession,
    hoi_thoai_id: int,
    nguoi_id: int | None = None,
) -> HoiThoaiModel | None:
    """Truy vấn cuộc hội thoại theo định danh, tự động bỏ qua các hội thoại đã xoá mềm."""
    cau_lenh = select(HoiThoaiModel).where(
        HoiThoaiModel.id == hoi_thoai_id,
        HoiThoaiModel.da_xoa.is_(False),
    )
    if nguoi_id is not None:
        cau_lenh = cau_lenh.where(HoiThoaiModel.nguoi_id == nguoi_id)

    return (await phien.scalars(cau_lenh)).first()


async def lay_danh_sach_luot(
    phien: AsyncSession,
    hoi_thoai_id: int,
) -> list[LuotModel]:
    """Lấy toàn bộ các lượt trao đổi trong hội thoại sắp xếp theo thứ tự thời gian tăng dần."""
    cau_lenh = (
        select(LuotModel)
        .where(LuotModel.hoi_thoai_id == hoi_thoai_id)
        .order_by(LuotModel.tao_luc.asc(), LuotModel.id.asc())
    )
    ket_qua = await phien.scalars(cau_lenh)
    return list(ket_qua.all())


async def luu_cap_luot_hoi_thoai(
    phien: AsyncSession,
    hoi_thoai_id: int,
    noi_dung_nguoi: str,
    noi_dung_tro_ly: str,
    *,
    kq_goi: KetQuaGoi | None = None,
    ma_yeu_cau: str,
    nhan_du_lieu: str | None = None,
    phien_ban_prompt: str | None = None,
) -> tuple[LuotModel, LuotModel]:
    """Lưu cả lượt người dùng và lượt phản hồi của trợ lý trong MỘT giao dịch duy nhất."""
    pb_prompt = phien_ban_prompt or doc_phien_ban_loi_nhac()
    moc_tao = datetime.now(timezone.utc)

    # 1. Lượt của người dùng
    luot_nguoi = LuotModel(
        hoi_thoai_id=hoi_thoai_id,
        vai_tro="nguoi_dung",
        noi_dung=noi_dung_nguoi,
        nhan_du_lieu=nhan_du_lieu,
        phien_ban_loi_nhac=pb_prompt,
        ma_yeu_cau=ma_yeu_cau,
        tao_luc=moc_tao,
    )
    phien.add(luot_nguoi)

    # 2. Lượt trả lời của trợ lý
    luot_tro_ly = LuotModel(
        hoi_thoai_id=hoi_thoai_id,
        vai_tro="tro_ly",
        noi_dung=noi_dung_tro_ly,
        nguon=str(kq_goi.nguon) if kq_goi else "local",
        tang=kq_goi.tang if kq_goi else 0,
        bac_local=kq_goi.bac_local if kq_goi else None,
        model_da_dung=kq_goi.ten_model if kq_goi else "khong_ro",
        token_vao=kq_goi.token_vao if kq_goi else 0,
        token_ra=kq_goi.token_ra if kq_goi else 0,
        chi_phi_usd=kq_goi.chi_phi_usd if kq_goi else 0.0,
        toc_do_tok_s=kq_goi.toc_do_tok_s if kq_goi else 0.0,
        thoi_gian_nap_ms=kq_goi.thoi_gian_nap_ms if kq_goi else 0.0,
        do_tre_ms=kq_goi.do_tre_ms if kq_goi else 0.0,
        da_cat_ngu_canh=kq_goi.da_cat_ngu_canh if kq_goi else False,
        so_luot_bi_cat=kq_goi.so_luot_bi_cat if kq_goi else 0,
        nhan_du_lieu=nhan_du_lieu,
        nguon_tham_chieu=None,
        phien_ban_loi_nhac=pb_prompt,
        ma_yeu_cau=ma_yeu_cau,
        tao_luc=moc_tao,
    )
    phien.add(luot_tro_ly)

    # Cập nhật thời điểm sửa đổi của cuộc hội thoại
    hoi_thoai = await lay_hoi_thoai(phien, hoi_thoai_id)
    if hoi_thoai:
        hoi_thoai.cap_nhat_luc = moc_tao

    await phien.flush()
    return luot_nguoi, luot_tro_ly


async def xoa_hoi_thoai(
    phien: AsyncSession,
    hoi_thoai_id: int,
    nguoi_id: int | None = None,
) -> bool:
    """Xóa cuộc hội thoại khỏi cơ sở dữ liệu.

    Ràng buộc khoá ngoại ON DELETE CASCADE đảm bảo toàn bộ các bản ghi lượt
    liên quan sẽ tự động bị xoá theo.
    """
    hoi_thoai = await lay_hoi_thoai(phien, hoi_thoai_id, nguoi_id=nguoi_id)
    if hoi_thoai is None:
        return False

    await phien.delete(hoi_thoai)
    await phien.flush()
    return True


def _chuan_hoa_tieu_de(van_ban: str) -> str:
    """Làm sạch và giới hạn độ dài chuỗi tiêu đề tối đa 8 từ."""
    chuoi = van_ban.strip().strip('"').strip("'").strip("`")
    # Lấy dòng đầu tiên nếu mô hình sinh nhiều dòng
    dong_dau = chuoi.splitlines()[0].strip() if chuoi else "Cuộc trò chuyện"
    cac_tu = dong_dau.split()
    return " ".join(cac_tu[:8]) if len(cac_tu) > 8 else dong_dau


async def tu_dat_tieu_de(
    hoi_thoai_id: int,
    noi_dung_nguoi: str,
    noi_dung_tro_ly: str,
    nguoi: NguoiDung,
) -> None:
    """Tác vụ nền tự động đặt tiêu đề cho cuộc hội thoại sau lượt đầu tiên.

    BUỘC dùng tầng 0 bậc nho qua uu_tien_bac_nho=True để không chiếm khe của model chính
    và không gửi nội dung hội thoại ra đám mây chỉ để đặt tiêu đề.
    """
    ma_yc = f"tieu_de_{hoi_thoai_id}"
    prompt_he_thong = doc_loi_nhac_tieu_de()
    tin_nhan = [
        {"role": "system", "content": prompt_he_thong},
        {
            "role": "user",
            "content": f"Câu hỏi: {noi_dung_nguoi}\nTrả lời: {noi_dung_tro_ly}",
        },
    ]

    try:
        kq = await goi_mo_hinh(
            tin_nhan,
            nguoi=nguoi,
            ma_yeu_cau=ma_yc,
            uu_tien_bac_nho=True,
        )
        tieu_de_moi = _chuan_hoa_tieu_de(kq.noi_dung)
        if not tieu_de_moi:
            return

        maker = lay_sessionmaker_async()
        async with maker() as phien:
            hoi_thoai = await lay_hoi_thoai(phien, hoi_thoai_id)
            if hoi_thoai:
                hoi_thoai.tieu_de = tieu_de_moi
                await phien.commit()
                logger.info(
                    "[%s] Tự đặt tiêu đề thành công cho hội thoại %d: '%s'",
                    ma_yc,
                    hoi_thoai_id,
                    tieu_de_moi,
                )
    except Exception as err:  # noqa: BLE001
        logger.warning("[%s] Tự đặt tiêu đề thất bại cho hội thoại %d: %s", ma_yc, hoi_thoai_id, err)
