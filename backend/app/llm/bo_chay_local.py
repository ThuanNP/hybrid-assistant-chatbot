"""Kết nối và điều phối bộ chạy mô hình cục bộ (Ollama, LM Studio)."""

from abc import ABC, abstractmethod
import json
import logging
import time
from typing import Any, AsyncIterator

import httpx
from pydantic import BaseModel

from app.config import CauHinhHeThong, cau_hinh
from app.core.loi import LoiDauVao, LoiHetBacLocal

logger = logging.getLogger(__name__)


class KetQuaGoiLocal(BaseModel):
    """Kết quả gọi hoàn thành hội thoại từ bộ chạy cục bộ dạng không phát dòng."""

    noi_dung: str
    model: str
    bac: str
    thoi_gian_nap_ms: float
    do_tre_ms: float
    toc_do_tok_s: float
    token_vao: int
    token_ra: int
    ma_yeu_cau: str
    do_dai_hang_doi: int = 0


class KetQuaDongLocal(BaseModel):
    """Mẩu dữ liệu phát theo dòng (SSE) từ bộ chạy cục bộ."""

    noi_dung: str
    da_xong: bool = False
    model: str
    bac: str
    ma_yeu_cau: str
    thoi_gian_nap_ms: float = 0.0
    do_tre_ms: float = 0.0
    toc_do_tok_s: float = 0.0
    token_vao: int = 0
    token_ra: int = 0


class LuongKetQuaDong:
    """Bộ bọc luồng phát dòng bất đồng bộ hỗ trợ cả 'await' lẫn 'async for'."""

    def __init__(self, bo_sinh: AsyncIterator[KetQuaDongLocal]) -> None:
        self._bo_sinh = bo_sinh

    def __aiter__(self) -> AsyncIterator[KetQuaDongLocal]:
        return self._bo_sinh

    def __await__(self) -> Any:
        async def _tra_ve_chinh_minh() -> "LuongKetQuaDong":
            return self

        return _tra_ve_chinh_minh().__await__()


def _chuan_hoa_url_chat(dia_chi: str) -> str:
    """Chuẩn hóa đường dẫn endpoint chat completions tương thích chuẩn OpenAI."""
    duong_dan = dia_chi.rstrip("/")
    if duong_dan.endswith("/chat/completions"):
        return duong_dan
    if duong_dan.endswith("/v1"):
        return f"{duong_dan}/chat/completions"
    return f"{duong_dan}/v1/chat/completions"


def _chuan_hoa_url_goc(dia_chi: str) -> str:
    """Lấy địa chỉ gốc của dịch vụ để gọi các API quản lý như /api/ps, /api/show."""
    duong_dan = dia_chi.rstrip("/")
    if duong_dan.endswith("/v1"):
        return duong_dan[:-3]
    return duong_dan


async def _boc_dong_sse(
    phan_hoi: httpx.Response,
    *,
    model: str,
    bac: str,
    ma_yeu_cau: str,
    t0: float,
) -> AsyncIterator[KetQuaDongLocal]:
    """Bóc từng dòng dữ liệu SSE tương thích OpenAI, dừng khi gặp [DONE]."""
    t_dau_tien: float | None = None
    so_token_ra = 0
    token_vao = 0

    async for dong_tho in phan_hoi.aiter_lines():
        dong = dong_tho.strip()
        # Bỏ qua dòng rỗng và dòng chú thích SSE (bắt đầu bằng dấu hai chấm)
        if not dong or dong.startswith(":"):
            continue
        if not dong.startswith("data:"):
            continue

        du_lieu = dong[5:].strip()
        if du_lieu == "[DONE]":
            break

        try:
            vat_the_json = json.loads(du_lieu)
        except json.JSONDecodeError:
            continue

        usage = vat_the_json.get("usage")
        if usage:
            token_vao = usage.get("prompt_tokens", token_vao)
            token_ra_usage = usage.get("completion_tokens")
            if token_ra_usage is not None:
                so_token_ra = token_ra_usage

        lua_chon = vat_the_json.get("choices", [])
        if not lua_chon:
            continue

        delta = lua_chon[0].get("delta", {})
        noi_dung_chunk = delta.get("content", "")
        if noi_dung_chunk:
            if t_dau_tien is None:
                t_dau_tien = time.perf_counter()
            so_token_ra += 1
            yield KetQuaDongLocal(
                noi_dung=noi_dung_chunk,
                da_xong=False,
                model=model,
                bac=bac,
                ma_yeu_cau=ma_yeu_cau,
            )

    t_ket_thuc = time.perf_counter()
    do_tre_ms = round((t_ket_thuc - t0) * 1000, 2)
    if t_dau_tien is not None:
        thoi_gian_nap_ms = round((t_dau_tien - t0) * 1000, 2)
        thoi_gian_sinh_giay = max(t_ket_thuc - t_dau_tien, 0.001)
        toc_do_tok_s = round(so_token_ra / thoi_gian_sinh_giay, 2)
    else:
        thoi_gian_nap_ms = do_tre_ms
        toc_do_tok_s = 0.0

    # TODO: nếu bộ chạy không trả usage thì ước lượng bằng dem_token ở PROMPT 9
    yield KetQuaDongLocal(
        noi_dung="",
        da_xong=True,
        model=model,
        bac=bac,
        ma_yeu_cau=ma_yeu_cau,
        thoi_gian_nap_ms=thoi_gian_nap_ms,
        do_tre_ms=do_tre_ms,
        toc_do_tok_s=toc_do_tok_s,
        token_vao=token_vao,
        token_ra=so_token_ra,
    )


class BoChay(ABC):
    """Giao diện trừu tượng cho bộ chạy mô hình cục bộ."""

    def __init__(
        self,
        dia_chi: str,
        timeout_giay: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.dia_chi = dia_chi
        self.timeout_giay = timeout_giay
        self._client = client

    @abstractmethod
    def _tao_than_yeu_cau(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        num_ctx: int,
        keep_alive: str,
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Tạo thân JSON yêu cầu phù hợp với từng loại bộ chạy."""
        ...

    @abstractmethod
    async def liet_ke_model(self) -> list[str]:
        """Liệt kê danh sách các mô hình có sẵn trong bộ chạy."""
        ...

    @abstractmethod
    async def model_dang_nap(self) -> list[str]:
        """Liệt kê danh sách các mô hình đang được nạp vào VRAM/RAM."""
        ...

    @abstractmethod
    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc kích thước cửa sổ ngữ cảnh thực tế mà bộ chạy đang dùng cho model."""
        ...

    async def _gui_post(
        self,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, Any],
        timeout: float,
    ) -> httpx.Response:
        """Gửi yêu cầu POST qua httpx.AsyncClient tái sử dụng hoặc tạo mới."""
        if self._client is not None:
            return await self._client.post(url, headers=headers, json=json_body, timeout=timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, headers=headers, json=json_body)

    async def goi(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        num_ctx: int,
        keep_alive: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        ma_yeu_cau: str = "",
        timeout_giay: float | None = None,
    ) -> KetQuaGoiLocal:
        """Gửi yêu cầu hoàn thành hội thoại dạng không phát theo dòng."""
        t0 = time.perf_counter()
        url = _chuan_hoa_url_chat(self.dia_chi)
        than_yeu_cau = self._tao_than_yeu_cau(
            model=model,
            messages=messages,
            stream=False,
            num_ctx=num_ctx,
            keep_alive=keep_alive,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        headers = {"Authorization": "Bearer local", "Content-Type": "application/json"}
        timeout = timeout_giay if timeout_giay is not None else self.timeout_giay

        phan_hoi = await self._gui_post(url, headers, than_yeu_cau, timeout)

        # Lỗi 4xx là do tham số hoặc mã gọi sai, ném LoiDauVao không hạ cấp
        if 400 <= phan_hoi.status_code < 500:
            raise LoiDauVao(
                f"Lỗi client từ bộ chạy ({phan_hoi.status_code}): {phan_hoi.text}",
                ma_trang_thai=phan_hoi.status_code,
                ma_yeu_cau=ma_yeu_cau,
                chi_tiet=phan_hoi.text,
            )
        phan_hoi.raise_for_status()

        t1 = time.perf_counter()
        du_lieu_json = phan_hoi.json()
        lua_chon = du_lieu_json.get("choices", [])
        noi_dung = lua_chon[0]["message"]["content"] if lua_chon else ""

        usage = du_lieu_json.get("usage") or {}
        token_vao = usage.get("prompt_tokens", 0)
        token_ra = usage.get("completion_tokens", 0)
        # TODO: Nếu bộ chạy không trả usage thì ước lượng bằng dem_token ở PROMPT 9

        do_tre_ms = round((t1 - t0) * 1000, 2)
        prompt_eval_ns = du_lieu_json.get("prompt_eval_duration")
        if prompt_eval_ns is not None:
            thoi_gian_nap_ms = round(prompt_eval_ns / 1_000_000, 2)
        else:
            thoi_gian_nap_ms = do_tre_ms

        eval_duration_ns = du_lieu_json.get("eval_duration")
        if eval_duration_ns is not None and token_ra > 0:
            toc_do_tok_s = round(token_ra / (eval_duration_ns / 1e9), 2)
        else:
            thoi_gian_giay = max(do_tre_ms / 1000.0, 0.001)
            toc_do_tok_s = round(token_ra / thoi_gian_giay, 2) if token_ra > 0 else 0.0

        return KetQuaGoiLocal(
            noi_dung=noi_dung,
            model=model,
            bac="",
            thoi_gian_nap_ms=thoi_gian_nap_ms,
            do_tre_ms=do_tre_ms,
            toc_do_tok_s=toc_do_tok_s,
            token_vao=token_vao,
            token_ra=token_ra,
            ma_yeu_cau=ma_yeu_cau,
        )

    async def goi_theo_dong(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        num_ctx: int,
        keep_alive: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        ma_yeu_cau: str = "",
        timeout_giay: float | None = None,
    ) -> AsyncIterator[KetQuaDongLocal]:
        """Gửi yêu cầu hoàn thành hội thoại dạng phát theo dòng (SSE)."""
        t0 = time.perf_counter()
        url = _chuan_hoa_url_chat(self.dia_chi)
        than_yeu_cau = self._tao_than_yeu_cau(
            model=model,
            messages=messages,
            stream=True,
            num_ctx=num_ctx,
            keep_alive=keep_alive,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        headers = {"Authorization": "Bearer local", "Content-Type": "application/json"}
        timeout = timeout_giay if timeout_giay is not None else self.timeout_giay

        client = self._client or httpx.AsyncClient(timeout=timeout)
        can_dong_client = self._client is None
        try:
            async with client.stream("POST", url, headers=headers, json=than_yeu_cau) as phan_hoi:
                if 400 <= phan_hoi.status_code < 500:
                    noi_dung_loi = await phan_hoi.aread()
                    raise LoiDauVao(
                        f"Lỗi client từ bộ chạy ({phan_hoi.status_code}): {noi_dung_loi.decode('utf-8', errors='replace')}",
                        ma_trang_thai=phan_hoi.status_code,
                        ma_yeu_cau=ma_yeu_cau,
                    )
                phan_hoi.raise_for_status()

                async for chunk in _boc_dong_sse(
                    phan_hoi,
                    model=model,
                    bac="",
                    ma_yeu_cau=ma_yeu_cau,
                    t0=t0,
                ):
                    yield chunk
        finally:
            if can_dong_client:
                await client.aclose()


class BoChayOllama(BoChay):
    """Hiện thực bộ chạy cho Ollama qua API chuẩn OpenAI và API quản lý nội bộ."""

    def _tao_than_yeu_cau(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        num_ctx: int,
        keep_alive: str,
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        # keep_alive nằm ở CẤP CAO NHẤT, là anh em với options, KHÔNG nằm trong options
        than_yeu_cau: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "keep_alive": keep_alive,
            "options": {
                "num_ctx": num_ctx,
            },
        }
        if max_tokens is not None:
            than_yeu_cau["max_tokens"] = max_tokens
        return than_yeu_cau

    async def liet_ke_model(self) -> list[str]:
        """Lấy danh sách các mô hình đã tải về thông qua GET /api/tags."""
        url = f"{_chuan_hoa_url_goc(self.dia_chi)}/api/tags"
        if self._client is not None:
            phan_hoi = await self._client.get(url, timeout=self.timeout_giay)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                phan_hoi = await client.get(url)
        phan_hoi.raise_for_status()
        du_lieu = phan_hoi.json()
        return [m.get("name", "") for m in du_lieu.get("models", []) if m.get("name")]

    async def model_dang_nap(self) -> list[str]:
        """Lấy danh sách mô hình đang nạp trong VRAM thông qua GET /api/ps."""
        url = f"{_chuan_hoa_url_goc(self.dia_chi)}/api/ps"
        if self._client is not None:
            phan_hoi = await self._client.get(url, timeout=self.timeout_giay)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                phan_hoi = await client.get(url)
        phan_hoi.raise_for_status()
        du_lieu = phan_hoi.json()
        return [m.get("name", "") for m in du_lieu.get("models", []) if m.get("name")]

    async def thiet_lap_keep_alive(self, model: str, keep_alive: str) -> None:
        """Thiết lập thời gian duy trì mô hình trong VRAM của Ollama qua /api/generate."""
        try:
            url = f"{_chuan_hoa_url_goc(self.dia_chi)}/api/generate"
            body = {"model": model, "keep_alive": keep_alive}
            if self._client is not None:
                await self._client.post(url, json=body, timeout=self.timeout_giay)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                    await client.post(url, json=body)
        except Exception as err:
            logger.debug("Không cập nhật được keep_alive qua /api/generate: %s", err)

    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc cửa sổ ngữ cảnh thực tế từ GET /api/ps (nếu đang nạp) hoặc POST /api/show."""
        goc = _chuan_hoa_url_goc(self.dia_chi)
        # 1. Kiểm tra mô hình đang nạp qua /api/ps
        try:
            url_ps = f"{goc}/api/ps"
            if self._client is not None:
                ps_res = await self._client.get(url_ps, timeout=self.timeout_giay)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                    ps_res = await client.get(url_ps)
            if ps_res.status_code == 200:
                models_nap = ps_res.json().get("models", [])
                for m in models_nap:
                    if (m.get("name") == model or m.get("model") == model) and m.get("context_length"):
                        return int(m["context_length"])
        except Exception as err:
            logger.debug("Không đọc được ngữ cảnh từ /api/ps cho %s: %s", model, err)

        # 2. Đọc thông tin mô hình qua POST /api/show
        try:
            url_show = f"{goc}/api/show"
            body = {"model": model}
            if self._client is not None:
                show_res = await self._client.post(url_show, json=body, timeout=self.timeout_giay)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                    show_res = await client.post(url_show, json=body)
            if show_res.status_code == 200:
                info = show_res.json().get("model_info", {})
                for k, v in info.items():
                    if k.endswith(".context_length"):
                        return int(v)
                details = show_res.json().get("details", {})
                if details.get("context_length"):
                    return int(details["context_length"])
        except Exception as err:
            logger.debug("Không đọc được ngữ cảnh từ /api/show cho %s: %s", model, err)

        return None


class BoChayLMStudio(BoChay):
    """Hiện thực bộ chạy cho LM Studio (lược bỏ options và keep_alive)."""

    def _tao_than_yeu_cau(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        num_ctx: int,
        keep_alive: str,
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        # LM Studio quản lý ngữ cảnh và thời gian nạp khi nạp model nên bỏ options và keep_alive
        than_yeu_cau: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens is not None:
            than_yeu_cau["max_tokens"] = max_tokens
        return than_yeu_cau

    async def liet_ke_model(self) -> list[str]:
        """Lấy danh sách các mô hình qua endpoint /models chuẩn OpenAI."""
        url = f"{self.dia_chi.rstrip('/')}/models"
        if self._client is not None:
            phan_hoi = await self._client.get(url, timeout=self.timeout_giay)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                phan_hoi = await client.get(url)
        phan_hoi.raise_for_status()
        du_lieu = phan_hoi.json()
        return [m.get("id", "") for m in du_lieu.get("data", []) if m.get("id")]

    async def model_dang_nap(self) -> list[str]:
        """Trong LM Studio các model trả về qua /models là các model khả dụng/đang nạp."""
        return await self.liet_ke_model()

    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc ngữ cảnh từ trường context_length trong danh sách /models nếu có."""
        try:
            url = f"{self.dia_chi.rstrip('/')}/models"
            if self._client is not None:
                phan_hoi = await self._client.get(url, timeout=self.timeout_giay)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_giay) as client:
                    phan_hoi = await client.get(url)
            if phan_hoi.status_code == 200:
                du_lieu = phan_hoi.json()
                for m in du_lieu.get("data", []):
                    if m.get("id") == model:
                        val = m.get("context_length") or m.get("max_context_length")
                        if val:
                            return int(val)
        except Exception as err:
            logger.debug("Không đọc được ngữ cảnh từ LM Studio cho %s: %s", model, err)
        return None


def lay_bo_chay(
    loai: str | None = None,
    dia_chi: str | None = None,
    timeout_giay: float | None = None,
    client: httpx.AsyncClient | None = None,
) -> BoChay:
    """Factory khởi tạo bộ chạy BoChay phù hợp theo LOAI_BO_CHAY."""
    loai_duoc_chon = (loai or cau_hinh.bo_chay.loai).lower().strip()
    dia_chi_duoc_chon = dia_chi or cau_hinh.bo_chay.dia_chi
    timeout = timeout_giay if timeout_giay is not None else float(cau_hinh.bo_chay.timeout_giay)

    if loai_duoc_chon == "ollama":
        return BoChayOllama(dia_chi=dia_chi_duoc_chon, timeout_giay=timeout, client=client)
    if loai_duoc_chon in ("lmstudio", "lm_studio"):
        return BoChayLMStudio(dia_chi=dia_chi_duoc_chon, timeout_giay=timeout, client=client)

    raise ValueError(
        f"LOAI_BO_CHAY không hợp lệ: '{loai_duoc_chon}'. Chỉ hỗ trợ 'ollama' hoặc 'lmstudio'."
    )


async def _goi_local_theo_dong(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int,
    bo_chay: BoChay,
    cfg: CauHinhHeThong,
    temperature: float | None,
    max_tokens: int | None,
) -> AsyncIterator[KetQuaDongLocal]:
    """Luồng phát theo dòng qua chuỗi bậc 1 (chính) và bậc 2 (nhỏ)."""
    so_model = cfg.so_model_nap_cung_luc
    nguong_hang_doi = cfg.local_chung.nguong_hang_doi_ha_cap
    bac_1 = cfg.bac_local[0]
    bac_2 = cfg.bac_local[1]
    keep_alive = cfg.local_chung.keep_alive
    temp = temperature if temperature is not None else cfg.local_chung.nhiet_do
    max_tok = max_tokens if max_tokens is not None else cfg.cai_dat_chung.gioi_han_token_ra

    bo_qua_bac_1 = False
    ly_do_bac_1: str | None = None
    ly_do_bac_2: str | None = None

    if so_model > 1 and do_dai_hang_doi > nguong_hang_doi:
        bo_qua_bac_1 = True
        ly_do_bac_1 = (
            f"Bỏ qua bậc 1 vì hàng đợi dài ({do_dai_hang_doi} > {nguong_hang_doi}) "
            f"và so_model_nap_cung_luc={so_model} > 1"
        )
        logger.info("[%s] %s", ma_yeu_cau, ly_do_bac_1)

    if not bo_qua_bac_1:
        co_token_tra_ve = False
        try:
            async for chunk in bo_chay.goi_theo_dong(
                model=bac_1.model,
                messages=tin_nhan,
                num_ctx=bac_1.num_ctx,
                keep_alive=keep_alive,
                temperature=temp,
                max_tokens=max_tok,
                ma_yeu_cau=ma_yeu_cau,
            ):
                co_token_tra_ve = True
                chunk.bac = "chinh"
                yield chunk
            return
        except LoiDauVao:
            raise
        except Exception as err:
            if co_token_tra_ve:
                logger.error("[%s] Bậc 1 bị gián đoạn truyền dòng: %s", ma_yeu_cau, err)
                raise
            ly_do_bac_1 = f"Bậc 1 ({bac_1.model}) thất bại: {type(err).__name__}: {err}"
            logger.warning(
                "[%s] %s, tiến hành hạ cấp sang bậc 2 (%s)",
                ma_yeu_cau,
                ly_do_bac_1,
                bac_2.model,
            )

    # Thử bậc 2 khi bậc 1 lỗi hoặc bị bỏ qua
    try:
        async for chunk in bo_chay.goi_theo_dong(
            model=bac_2.model,
            messages=tin_nhan,
            num_ctx=bac_2.num_ctx,
            keep_alive=keep_alive,
            temperature=temp,
            max_tokens=max_tok,
            ma_yeu_cau=ma_yeu_cau,
        ):
            chunk.bac = "nho"
            yield chunk
        return
    except LoiDauVao:
        raise
    except Exception as err:
        ly_do_bac_2 = f"Bậc 2 ({bac_2.model}) thất bại: {type(err).__name__}: {err}"
        logger.error("[%s] Bậc 2 thất bại: %s", ma_yeu_cau, ly_do_bac_2)

    raise LoiHetBacLocal(
        f"Hết cả hai bậc local cho yêu cầu {ma_yeu_cau}. Bậc 1: {ly_do_bac_1}. Bậc 2: {ly_do_bac_2}.",
        ly_do_bac_1=ly_do_bac_1,
        ly_do_bac_2=ly_do_bac_2,
        ma_yeu_cau=ma_yeu_cau,
    )


async def goi_local(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int = 0,
    phat_theo_dong: bool = False,
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """Điều phối gọi chuỗi local theo thứ tự bậc 1 (chính) rồi bậc 2 (nhỏ)."""
    cfg = cau_hinh_he_thong or cau_hinh
    runner = bo_chay or lay_bo_chay()

    if phat_theo_dong:
        return LuongKetQuaDong(
            _goi_local_theo_dong(
                tin_nhan,
                ma_yeu_cau=ma_yeu_cau,
                do_dai_hang_doi=do_dai_hang_doi,
                bo_chay=runner,
                cfg=cfg,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )

    so_model = cfg.so_model_nap_cung_luc
    nguong_hang_doi = cfg.local_chung.nguong_hang_doi_ha_cap
    bac_1 = cfg.bac_local[0]
    bac_2 = cfg.bac_local[1]
    keep_alive = cfg.local_chung.keep_alive
    temp = temperature if temperature is not None else cfg.local_chung.nhiet_do
    max_tok = max_tokens if max_tokens is not None else cfg.cai_dat_chung.gioi_han_token_ra

    bo_qua_bac_1 = False
    ly_do_bac_1: str | None = None
    ly_do_bac_2: str | None = None

    # Hàng đợi dài chỉ bỏ qua bậc 1 khi hệ thống nạp đồng thời >= 2 model.
    # Khi so_model_nap_cung_luc = 1, đổi model tốn 5-20s nên tuyệt đối không hạ cấp vì hàng đợi.
    if so_model > 1 and do_dai_hang_doi > nguong_hang_doi:
        bo_qua_bac_1 = True
        ly_do_bac_1 = (
            f"Bỏ qua bậc 1 vì hàng đợi dài ({do_dai_hang_doi} > {nguong_hang_doi}) "
            f"và so_model_nap_cung_luc={so_model} > 1"
        )
        logger.info("[%s] %s", ma_yeu_cau, ly_do_bac_1)

    if not bo_qua_bac_1:
        try:
            kq_1 = await runner.goi(
                model=bac_1.model,
                messages=tin_nhan,
                num_ctx=bac_1.num_ctx,
                keep_alive=keep_alive,
                temperature=temp,
                max_tokens=max_tok,
                ma_yeu_cau=ma_yeu_cau,
            )
            kq_1.bac = "chinh"
            kq_1.do_dai_hang_doi = do_dai_hang_doi
            return kq_1
        except LoiDauVao:
            raise
        except Exception as err:
            ly_do_bac_1 = f"Bậc 1 ({bac_1.model}) thất bại: {type(err).__name__}: {err}"
            logger.warning(
                "[%s] %s, tiến hành hạ cấp sang bậc 2 (%s)",
                ma_yeu_cau,
                ly_do_bac_1,
                bac_2.model,
            )

    # Thử tiếp bậc 2
    try:
        kq_2 = await runner.goi(
            model=bac_2.model,
            messages=tin_nhan,
            num_ctx=bac_2.num_ctx,
            keep_alive=keep_alive,
            temperature=temp,
            max_tokens=max_tok,
            ma_yeu_cau=ma_yeu_cau,
        )
        kq_2.bac = "nho"
        kq_2.do_dai_hang_doi = do_dai_hang_doi
        return kq_2
    except LoiDauVao:
        raise
    except Exception as err:
        ly_do_bac_2 = f"Bậc 2 ({bac_2.model}) thất bại: {type(err).__name__}: {err}"
        logger.error("[%s] Bậc 2 thất bại: %s", ma_yeu_cau, ly_do_bac_2)

    raise LoiHetBacLocal(
        f"Hết cả hai bậc local cho yêu cầu {ma_yeu_cau}. Bậc 1: {ly_do_bac_1}. Bậc 2: {ly_do_bac_2}.",
        ly_do_bac_1=ly_do_bac_1,
        ly_do_bac_2=ly_do_bac_2,
        ma_yeu_cau=ma_yeu_cau,
    )


async def ham_nong(
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> bool:
    """Hâm nóng mô hình bậc 1 bằng cách gửi yêu cầu 'xin chào' với max_tokens=1.

    CHỈ hâm nóng bậc 1; không bao giờ hâm nóng bậc 2 khi so_model_nap_cung_luc = 1.
    Chạy trong sự kiện lifespan nhưng không chặn khởi động nếu thất bại.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    runner = bo_chay or lay_bo_chay()
    bac_1 = cfg.bac_local[0]

    try:
        logger.info("Bắt đầu hâm nóng mô hình bậc 1 (%s)...", bac_1.model)
        await runner.goi(
            model=bac_1.model,
            messages=[{"role": "user", "content": "xin chào"}],
            num_ctx=bac_1.num_ctx,
            keep_alive=cfg.local_chung.keep_alive,
            temperature=cfg.local_chung.nhiet_do,
            max_tokens=1,
            ma_yeu_cau="ham_nong_khoi_dong",
        )
        if isinstance(runner, BoChayOllama):
            await runner.thiet_lap_keep_alive(bac_1.model, cfg.local_chung.keep_alive)
        logger.info("Hâm nóng mô hình bậc 1 (%s) thành công.", bac_1.model)
        return True
    except Exception as err:
        logger.warning(
            "Hâm nóng mô hình bậc 1 thất bại (%s): %s. Không chặn tiến trình khởi động.",
            bac_1.model,
            err,
        )
        return False


async def doc_ngu_canh_thuc_te(
    model: str,
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> int | None:
    """Đọc kích thước cửa sổ ngữ cảnh thực tế của model và cảnh báo nếu có độ lệch."""
    cfg = cau_hinh_he_thong or cau_hinh
    runner = bo_chay or lay_bo_chay()
    ngu_canh_thuc_te = await runner.doc_ngu_canh_thuc_te(model)

    num_ctx_cau_hinh: int | None = None
    for b in cfg.bac_local:
        if b.model == model:
            num_ctx_cau_hinh = b.num_ctx
            break

    if ngu_canh_thuc_te is not None and num_ctx_cau_hinh is not None:
        if ngu_canh_thuc_te != num_ctx_cau_hinh:
            logger.warning(
                "Cảnh báo độ lệch ngữ cảnh: model '%s' đang dùng context_length=%d, "
                "trong khi num_ctx trong cấu hình là %d. (Ollama có thể tự hạ ngữ cảnh khi VRAM căng)",
                model,
                ngu_canh_thuc_te,
                num_ctx_cau_hinh,
            )

    return ngu_canh_thuc_te
