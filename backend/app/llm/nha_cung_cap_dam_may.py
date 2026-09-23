"""Kết nối và điều phối các nhà cung cấp đám mây qua LiteLLM.

Mọi lời gọi mô hình đám mây trong ứng dụng đi qua mô-đun này; litellm chỉ nằm tại đây.
Tuyệt đối không ghi khoá API hoặc nội dung tin nhắn vào nhật ký.
"""

import asyncio
import logging
import os
import random
import time
from collections.abc import AsyncIterator
from typing import Any, Literal, overload

import litellm
import litellm.exceptions
from pydantic import BaseModel

from app.config import (
    DUONG_DAN_ENV_MAC_DINH,
    GIA_TRI_MAU_GIA,
    CauHinhHeThong,
    CauHinhTangDamMay,
    _doc_bien_gop,
    cau_hinh,
)
from app.core.loi import LoiDauVao, LoiHeThong, LoiTamThoi, LoiVinhVien
from app.llm.dem_token import dem_token

logger = logging.getLogger(__name__)

# Tắt thông tin gỡ lỗi mặc định của litellm để tránh rò rỉ khoá hoặc làm rối nhật ký
litellm.suppress_debug_info = True
litellm.drop_params = True


class KetQuaGoiDamMay(BaseModel):
    """Kết quả gọi hoàn thành hội thoại từ nhà cung cấp đám mây không phát dòng."""

    noi_dung: str
    model: str
    token_vao: int
    token_ra: int
    do_tre_ms: float
    ma_yeu_cau: str
    tang: int
    so_lan_thu: int
    chi_phi_la_uoc_tinh_tho: bool = False


class KetQuaDongDamMay(BaseModel):
    """Mẩu dữ liệu phát theo dòng (SSE) từ nhà cung cấp đám mây."""

    noi_dung: str
    da_xong: bool = False
    model: str
    tang: int
    ma_yeu_cau: str
    do_tre_ms: float = 0.0
    token_vao: int = 0
    token_ra: int = 0
    chi_phi_la_uoc_tinh_tho: bool = False


def lay_khoa_api(ten_bien_khoa: str) -> str | None:
    """Lấy khoá API từ biến môi trường hoặc tệp .env, trả về None nếu chưa cấu hình."""
    khoa = os.environ.get(ten_bien_khoa)
    if not khoa:
        bien_gop = _doc_bien_gop(DUONG_DAN_ENV_MAC_DINH)
        khoa = bien_gop.get(ten_bien_khoa)
    if not khoa or not khoa.strip() or khoa.strip() == GIA_TRI_MAU_GIA:
        return None
    return khoa.strip()


def _trich_xuat_ma_trang_thai(err: Exception) -> int | None:
    """Trích xuất mã trạng thái HTTP từ đối tượng ngoại lệ nếu có."""
    ma = getattr(err, "status_code", None)
    if isinstance(ma, int):
        return ma
    ma_code = getattr(err, "code", None)
    return ma_code if isinstance(ma_code, int) else None


def _phan_loai_theo_lop_litellm(err: Exception) -> tuple[type[LoiHeThong], int] | None:
    """Phân loại ngoại lệ dựa trên cây kế thừa của LiteLLM."""
    if isinstance(
        err,
        (
            litellm.exceptions.BadRequestError,
            litellm.exceptions.ContextWindowExceededError,
            litellm.exceptions.ContentPolicyViolationError,
        ),
    ):
        return LoiDauVao, 400

    if isinstance(err, litellm.exceptions.AuthenticationError):
        return LoiVinhVien, 401
    if isinstance(err, litellm.exceptions.PermissionDeniedError):
        return LoiVinhVien, 403
    if isinstance(err, litellm.exceptions.NotFoundError):
        return LoiVinhVien, 404

    if isinstance(
        err,
        (
            litellm.exceptions.RateLimitError,
            litellm.exceptions.InternalServerError,
            litellm.exceptions.ServiceUnavailableError,
            litellm.exceptions.BadGatewayError,
            litellm.exceptions.Timeout,
            litellm.exceptions.APIConnectionError,
        ),
    ):
        ma = 429 if isinstance(err, litellm.exceptions.RateLimitError) else 500
        return LoiTamThoi, ma

    return None


def _phan_loai_ngoai_le(err: Exception) -> tuple[type[LoiHeThong], int]:
    """Phân loại ngoại lệ thành ba nhóm: LoiDauVao, LoiVinhVien hoặc LoiTamThoi."""
    theo_lop = _phan_loai_theo_lop_litellm(err)
    ma_trang_thai = _trich_xuat_ma_trang_thai(err)
    if theo_lop is not None:
        loai_lop, ma_lop = theo_lop
        return loai_lop, ma_trang_thai or ma_lop

    if ma_trang_thai is not None:
        if ma_trang_thai == 400:
            return LoiDauVao, 400
        if ma_trang_thai in (401, 403, 404):
            return LoiVinhVien, ma_trang_thai
        if ma_trang_thai in (429, 500, 502, 503, 504):
            return LoiTamThoi, ma_trang_thai
        if 400 <= ma_trang_thai < 500:
            return LoiDauVao, ma_trang_thai
        if 500 <= ma_trang_thai < 600:
            return LoiTamThoi, ma_trang_thai

    if isinstance(err, (TimeoutError, asyncio.TimeoutError)):
        return LoiTamThoi, 504
    if isinstance(err, (ConnectionError, OSError)):
        return LoiTamThoi, 503

    thong_diep = str(err).lower()
    if "401" in thong_diep or "authentication" in thong_diep:
        return LoiVinhVien, 401
    if "403" in thong_diep or "permission" in thong_diep:
        return LoiVinhVien, 403
    if "404" in thong_diep or "not found" in thong_diep:
        return LoiVinhVien, 404
    if "429" in thong_diep or "rate limit" in thong_diep:
        return LoiTamThoi, 429
    if "400" in thong_diep:
        return LoiDauVao, 400

    return LoiTamThoi, 500


def _lam_sach_loi(thong_diep: str, khoa_api: str | None) -> str:
    """Xóa khoá API khỏi chuỗi lỗi nhằm bảo đảm không rò rỉ vào nhật ký."""
    if khoa_api and len(khoa_api) > 4 and khoa_api in thong_diep:
        return thong_diep.replace(khoa_api, "[DA_CHE_KHOA]")
    return thong_diep


def _tinh_thoi_gian_cho(giay_gian_cach: float, lan_thu: int) -> float:
    """Tính thời gian chờ giãn cách lũy thừa kèm nhiễu ngẫu nhiên (jitter)."""
    do_tre = giay_gian_cach * (2**lan_thu)
    nhieu = random.uniform(0.0, 0.25 * do_tre)
    return round(do_tre + nhieu, 4)


def _la_openrouter_auto(tang: CauHinhTangDamMay) -> bool:
    """Kiểm tra xem tầng có phải là openrouter/auto hay không."""
    return tang.ten == "openrouter_auto" or "openrouter/auto" in tang.model


def _chuan_bi_tham_so_litellm(
    tang: CauHinhTangDamMay,
    khoa_api: str,
    tuy_chon: dict[str, Any],
) -> dict[str, Any]:
    """Tạo từ điển tham số hoàn chỉnh gửi sang litellm.acompletion."""
    tham_so: dict[str, Any] = {
        "model": tang.model,
        "api_key": khoa_api,
        "timeout": float(tang.timeout_giay),
    }
    if tang.tham_so_them:
        tham_so["extra_body"] = dict(tang.tham_so_them)

    bo_qua = {"so_lan_thu_lai_moi_tang", "giay_gian_cach_dau", "cau_hinh_he_thong"}
    for k, v in tuy_chon.items():
        if k not in bo_qua and v is not None:
            tham_so[k] = v
    return tham_so


def _trich_xuat_noi_dung_va_usage(phan_hoi: Any) -> tuple[str, int, int, str | None]:
    """Trích xuất văn bản phản hồi, số token vào/ra và tên model từ đối tượng litellm."""
    noi_dung = ""
    choices = getattr(phan_hoi, "choices", [])
    if choices:
        message = getattr(choices[0], "message", None)
        if message:
            noi_dung = str(getattr(message, "content", "") or "")

    usage = getattr(phan_hoi, "usage", None)
    token_vao = int(getattr(usage, "prompt_tokens", 0) or 0)
    token_ra = int(getattr(usage, "completion_tokens", 0) or 0)
    model_thuc = getattr(phan_hoi, "model", None)
    return noi_dung, token_vao, token_ra, model_thuc


def _lay_model_thuc_cua_chunk(chunk: Any) -> str | None:
    """Lấy tên model thực của một mẩu phát dòng.

    LiteLLM ghi đè chunk.model bằng tên model trong yêu cầu; tên model mà router
    (như openrouter/free) thực sự chọn nằm trong _hidden_params.
    """
    an = getattr(chunk, "_hidden_params", None)
    if isinstance(an, dict) and an.get("provider_response_model"):
        return str(an["provider_response_model"])
    return getattr(chunk, "model", None)


async def _xu_ly_that_bai(
    err: Exception,
    *,
    tang: CauHinhTangDamMay,
    ma_yeu_cau: str,
    lan_thu: int,
    tong_so_luot: int,
    giay_gian_cach: float,
    khoa_api: str,
    so_lan_goi: int,
) -> None:
    """Xử lý ngoại lệ, ghi nhật ký và quyết định ngủ để thử lại hay ném lỗi."""
    loai_loi, ma_trang_thai = _phan_loai_ngoai_le(err)
    thong_diep_sach = _lam_sach_loi(str(err), khoa_api)

    if loai_loi is LoiDauVao:
        logger.warning(
            "[%s] Tầng %s (%s) gặp LoiDauVao (%s): %s",
            ma_yeu_cau,
            tang.tang,
            tang.ten,
            ma_trang_thai,
            thong_diep_sach,
        )
        raise LoiDauVao(
            f"Lỗi đầu vào từ tầng {tang.tang} ({tang.ten}): {thong_diep_sach}",
            ma_trang_thai=ma_trang_thai,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet=thong_diep_sach,
        )

    if loai_loi is LoiVinhVien:
        logger.warning(
            "[%s] Tầng %s (%s) gặp LoiVinhVien (%s): %s",
            ma_yeu_cau,
            tang.tang,
            tang.ten,
            ma_trang_thai,
            thong_diep_sach,
        )
        raise LoiVinhVien(
            f"Lỗi vĩnh viễn từ tầng {tang.tang} ({tang.ten}): {thong_diep_sach}",
            ma_trang_thai=ma_trang_thai,
            ma_yeu_cau=ma_yeu_cau,
            chi_tiet=thong_diep_sach,
        )

    # LoiTamThoi: kiểm tra còn lượt thử lại không
    if lan_thu < tong_so_luot - 1:
        thoi_gian_cho = _tinh_thoi_gian_cho(giay_gian_cach, lan_thu)
        logger.warning(
            "[%s] Tầng %s (%s) lỗi tạm thời (%s), thử lại lần %d/%d sau %.2fs: %s",
            ma_yeu_cau,
            tang.tang,
            tang.ten,
            ma_trang_thai,
            lan_thu + 1,
            tong_so_luot - 1,
            thoi_gian_cho,
            thong_diep_sach,
        )
        await asyncio.sleep(thoi_gian_cho)
        return

    logger.warning(
        "[%s] Tầng %s (%s) hết %d lượt thử do lỗi tạm thời (%s): %s",
        ma_yeu_cau,
        tang.tang,
        tang.ten,
        tong_so_luot,
        ma_trang_thai,
        thong_diep_sach,
    )
    raise LoiTamThoi(
        f"Lỗi tạm thời từ tầng {tang.tang} ({tang.ten}) sau {tong_so_luot} lượt: {thong_diep_sach}",
        ma_trang_thai=ma_trang_thai,
        ma_yeu_cau=ma_yeu_cau,
        chi_tiet=thong_diep_sach,
        so_lan_thu=so_lan_goi,
    )


async def _goi_dam_may_mot_lan(
    tang: CauHinhTangDamMay,
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    khoa_api: str,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> KetQuaGoiDamMay:
    """Gọi một tầng đám mây dạng không phát theo dòng, có thử lại nếu lỗi tạm thời."""
    so_lan_thu_lai = int(
        tuy_chon.get("so_lan_thu_lai_moi_tang", cfg.cai_dat_chung.so_lan_thu_lai_moi_tang)
    )
    giay_gian_cach = float(
        tuy_chon.get("giay_gian_cach_dau", cfg.cai_dat_chung.giay_gian_cach_dau)
    )
    tong_so_luot = 1 + so_lan_thu_lai
    tham_so = _chuan_bi_tham_so_litellm(tang, khoa_api, tuy_chon)

    so_lan_goi = 0
    for lan_thu in range(tong_so_luot):
        so_lan_goi += 1
        t0 = time.perf_counter()
        try:
            phan_hoi = await litellm.acompletion(messages=tin_nhan, stream=False, **tham_so)
            do_tre_ms = round((time.perf_counter() - t0) * 1000, 2)
            noi_dung, token_vao, token_ra, model_thuc = _trich_xuat_noi_dung_va_usage(phan_hoi)
            la_openrouter = _la_openrouter_auto(tang)
            if token_vao == 0 and tin_nhan:
                token_vao = sum(
                    dem_token(m.get("content", "")) for m in tin_nhan if isinstance(m, dict)
                )
            if token_ra == 0 and noi_dung:
                token_ra = dem_token(noi_dung)
            return KetQuaGoiDamMay(
                noi_dung=noi_dung,
                model=model_thuc or tang.model,
                token_vao=token_vao,
                token_ra=token_ra,
                do_tre_ms=do_tre_ms,
                ma_yeu_cau=ma_yeu_cau,
                tang=tang.tang,
                so_lan_thu=so_lan_goi,
                chi_phi_la_uoc_tinh_tho=la_openrouter,
            )
        except Exception as err:
            await _xu_ly_that_bai(
                err,
                tang=tang,
                ma_yeu_cau=ma_yeu_cau,
                lan_thu=lan_thu,
                tong_so_luot=tong_so_luot,
                giay_gian_cach=giay_gian_cach,
                khoa_api=khoa_api,
                so_lan_goi=so_lan_goi,
            )

    raise RuntimeError("Luồng gọi không thể đạt tới đây")


async def _goi_dam_may_theo_dong(
    tang: CauHinhTangDamMay,
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    khoa_api: str,
    cfg: CauHinhHeThong,
    tuy_chon: dict[str, Any],
) -> AsyncIterator[KetQuaDongDamMay]:
    """Gọi một tầng đám mây dạng phát theo dòng SSE, chỉ thử lại trước mẩu đầu tiên."""
    so_lan_thu_lai = int(
        tuy_chon.get("so_lan_thu_lai_moi_tang", cfg.cai_dat_chung.so_lan_thu_lai_moi_tang)
    )
    giay_gian_cach = float(
        tuy_chon.get("giay_gian_cach_dau", cfg.cai_dat_chung.giay_gian_cach_dau)
    )
    tong_so_luot = 1 + so_lan_thu_lai
    tham_so = _chuan_bi_tham_so_litellm(tang, khoa_api, tuy_chon)
    la_openrouter = _la_openrouter_auto(tang)

    so_lan_goi = 0
    for lan_thu in range(tong_so_luot):
        so_lan_goi += 1
        t0 = time.perf_counter()
        da_phat_mau = False
        try:
            phan_hoi_stream: Any = await litellm.acompletion(
                messages=tin_nhan, stream=True, **tham_so
            )
            model_thuc = tang.model
            token_vao = 0
            token_ra = 0

            van_ban_da_nhan = ""
            async for chunk in phan_hoi_stream:
                # LiteLLM ghi đè chunk.model bằng tên model trong yêu cầu; tên model thực
                # (router như openrouter/free tự chọn) nằm trong _hidden_params
                chunk_model = _lay_model_thuc_cua_chunk(chunk)
                if chunk_model:
                    model_thuc = chunk_model

                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage:
                    token_vao = int(getattr(chunk_usage, "prompt_tokens", token_vao) or token_vao)
                    token_ra = int(
                        getattr(chunk_usage, "completion_tokens", token_ra) or token_ra
                    )

                chunk_choices = getattr(chunk, "choices", [])
                noi_dung_chunk = ""
                if chunk_choices:
                    delta = getattr(chunk_choices[0], "delta", None)
                    if delta:
                        noi_dung_chunk = str(getattr(delta, "content", "") or "")

                if noi_dung_chunk:
                    da_phat_mau = True
                    van_ban_da_nhan += noi_dung_chunk
                    token_ra += 1
                    yield KetQuaDongDamMay(
                        noi_dung=noi_dung_chunk,
                        da_xong=False,
                        model=model_thuc,
                        tang=tang.tang,
                        ma_yeu_cau=ma_yeu_cau,
                    )

            do_tre_ms = round((time.perf_counter() - t0) * 1000, 2)
            if token_vao == 0 and tin_nhan:
                token_vao = sum(
                    dem_token(m.get("content", "")) for m in tin_nhan if isinstance(m, dict)
                )
            if token_ra == 0 and van_ban_da_nhan:
                token_ra = dem_token(van_ban_da_nhan)
            yield KetQuaDongDamMay(
                noi_dung="",
                da_xong=True,
                model=model_thuc,
                tang=tang.tang,
                ma_yeu_cau=ma_yeu_cau,
                do_tre_ms=do_tre_ms,
                token_vao=token_vao,
                token_ra=token_ra,
                chi_phi_la_uoc_tinh_tho=la_openrouter,
            )
            return
        except Exception as err:
            # Đã phát mẩu ra ngoài thì không được phép thử lại, ném lên cho router xử lý
            if da_phat_mau:
                logger.warning(
                    "[%s] Tầng %s (%s) bị ngắt giữa chừng khi đang phát dòng: %s",
                    ma_yeu_cau,
                    tang.tang,
                    tang.ten,
                    _lam_sach_loi(str(err), khoa_api),
                )
                raise
            await _xu_ly_that_bai(
                err,
                tang=tang,
                ma_yeu_cau=ma_yeu_cau,
                lan_thu=lan_thu,
                tong_so_luot=tong_so_luot,
                giay_gian_cach=giay_gian_cach,
                khoa_api=khoa_api,
                so_lan_goi=so_lan_goi,
            )


@overload
async def goi_dam_may(
    tang: CauHinhTangDamMay,
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    phat_theo_dong: Literal[False] = False,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    **tuy_chon: Any,
) -> KetQuaGoiDamMay: ...


@overload
async def goi_dam_may(
    tang: CauHinhTangDamMay,
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    phat_theo_dong: Literal[True],
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    **tuy_chon: Any,
) -> AsyncIterator[KetQuaDongDamMay]: ...


async def goi_dam_may(
    tang: CauHinhTangDamMay,
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    phat_theo_dong: bool = False,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    **tuy_chon: Any,
) -> KetQuaGoiDamMay | AsyncIterator[KetQuaDongDamMay]:
    """Gọi MỘT tầng mô hình đám mây qua litellm.acompletion.

    Hỗ trợ cả hai chế độ phát dòng và không phát dòng. Tự động đọc cấu hình model,
    api_key_env, timeout_giay, tham_so_them từ tầng. Phân loại và xử lý thử lại lỗi
    theo chính sách giãn cách lũy thừa.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    khoa_api = lay_khoa_api(tang.api_key_env)
    if not khoa_api:
        logger.warning(
            "[%s] Tầng %s (%s): Thiếu khoá API đã cấu hình",
            ma_yeu_cau,
            tang.tang,
            tang.ten,
        )
        raise LoiVinhVien(
            f"Thiếu khoá API đã cấu hình cho tầng {tang.tang} ({tang.ten})",
            ma_trang_thai=401,
            ma_yeu_cau=ma_yeu_cau,
        )

    if phat_theo_dong:
        return _goi_dam_may_theo_dong(
            tang,
            tin_nhan,
            ma_yeu_cau=ma_yeu_cau,
            khoa_api=khoa_api,
            cfg=cfg,
            tuy_chon=tuy_chon,
        )

    return await _goi_dam_may_mot_lan(
        tang,
        tin_nhan,
        ma_yeu_cau=ma_yeu_cau,
        khoa_api=khoa_api,
        cfg=cfg,
        tuy_chon=tuy_chon,
    )
