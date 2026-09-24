"""Kết nối và điều phối bộ chạy mô hình cục bộ (Ollama, LM Studio)."""

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Literal, overload

import httpx
from pydantic import BaseModel

from app.config import CauHinhBacLocal, CauHinhHeThong, cau_hinh
from app.core.loi import LoiDauVao, LoiHetBacLocal
from app.llm.dem_token import dem_token

logger = logging.getLogger(__name__)

# Chỉ ba loại lỗi này kích hoạt hạ cấp: quá hạn và lỗi kết nối (TransportError bao cả
# TimeoutException), lỗi 5xx (HTTPStatusError). Lỗi khác là lỗi mã nguồn, phải nổi lên.
LOI_KICH_HOAT_HA_CAP = (httpx.TransportError, httpx.HTTPStatusError)

HEADER_BO_CHAY = {"Authorization": "Bearer local", "Content-Type": "application/json"}


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


class KetQuaNhungLocal(BaseModel):
    """Kết quả tạo vector nhúng từ bộ chạy cục bộ."""

    vectors: list[list[float]]
    model: str
    so_chieu: int
    do_tre_ms: float
    token_vao: int


class MauTho(BaseModel):
    """Dữ liệu đọc được từ một phản hồi hoặc một dòng phát, chung cho mọi bộ chạy."""

    noi_dung: str = ""
    token_vao: int | None = None
    token_ra: int | None = None
    thoi_gian_nap_ms: float | None = None
    thoi_gian_sinh_giay: float | None = None
    ket_thuc: bool = False


class ThongTinModelDangNap(BaseModel):
    """Thông tin mô hình đang nạp trong VRAM/RAM của bộ chạy."""

    ten: str
    kich_thuoc_byte: int | None = None
    kich_thuoc_vram_byte: int | None = None
    het_han_luc: str | None = None


def _chuan_hoa_url_goc(dia_chi: str) -> str:
    """Lấy địa chỉ gốc của dịch vụ (bỏ hậu tố /v1) để gọi các API riêng như /api/chat."""
    return dia_chi.rstrip("/").removesuffix("/v1")


def _tinh_toc_do(so_token: int, thoi_gian_giay: float) -> float:
    """Tính tok/s, tránh chia cho 0 khi thời gian sinh quá ngắn."""
    return round(so_token / max(thoi_gian_giay, 0.001), 2) if so_token > 0 else 0.0


def _doc_json(dong: str) -> dict[str, Any] | None:
    """Đọc một chuỗi JSON; trả None nếu không phải đối tượng JSON hợp lệ."""
    try:
        du_lieu = json.loads(dong)
    except json.JSONDecodeError:
        return None
    return du_lieu if isinstance(du_lieu, dict) else None


def _loi_dau_vao(ma_trang_thai: int, noi_dung_loi: str, ma_yeu_cau: str) -> LoiDauVao:
    """Tạo LoiDauVao cho phản hồi 4xx: lỗi do yêu cầu sai, không được hạ cấp."""
    return LoiDauVao(
        f"Lỗi client từ bộ chạy ({ma_trang_thai}): {noi_dung_loi}",
        ma_trang_thai=ma_trang_thai,
        ma_yeu_cau=ma_yeu_cau,
        chi_tiet=noi_dung_loi,
    )


class BoChay(ABC):
    """Giao diện trừu tượng cho bộ chạy mô hình cục bộ.

    Lớp con khai báo endpoint chat, thân yêu cầu và cách đọc phản hồi; phần gửi,
    xử lý lỗi và đo chỉ số dùng chung ở đây.
    """

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
    def _url_chat(self) -> str:
        """Endpoint gọi hội thoại của bộ chạy."""

    @abstractmethod
    def _url_nhung(self) -> str:
        """Endpoint tạo vector nhúng của bộ chạy."""

    @abstractmethod
    async def nhung(
        self,
        model: str,
        van_ban: list[str],
        *,
        keep_alive: str = "30m",
        timeout_giay: float | None = None,
        ma_yeu_cau: str = "",
    ) -> KetQuaNhungLocal:
        """Tạo vector nhúng từ danh sách văn bản."""

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

    @abstractmethod
    def _doc_phan_hoi(self, du_lieu: dict[str, Any]) -> MauTho:
        """Đọc phản hồi không phát theo dòng."""

    @abstractmethod
    def _doc_dong(self, dong: str) -> MauTho | None:
        """Đọc một dòng của luồng phát; trả None với dòng không mang dữ liệu."""

    @abstractmethod
    async def liet_ke_model(self) -> list[str]:
        """Liệt kê danh sách các mô hình có sẵn trong bộ chạy."""

    @abstractmethod
    async def model_dang_nap(self) -> list[str]:
        """Liệt kê danh sách các mô hình đang được nạp vào VRAM/RAM."""

    @abstractmethod
    async def doc_trang_thai_bo_chay(self) -> list[ThongTinModelDangNap]:
        """Đọc danh sách các mô hình đang nạp kèm kích thước, VRAM và thời điểm hết hạn."""

    @abstractmethod
    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc kích thước cửa sổ ngữ cảnh thực tế mà bộ chạy đang dùng cho model."""

    async def _gui(
        self,
        phuong_thuc: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Gửi yêu cầu qua client dùng chung (nếu có) hoặc client tạm, luôn có timeout."""
        han = timeout if timeout is not None else self.timeout_giay
        if self._client is not None:
            return await self._client.request(
                phuong_thuc, url, json=json_body, headers=headers, timeout=han
            )
        async with httpx.AsyncClient(timeout=han) as client:
            return await client.request(phuong_thuc, url, json=json_body, headers=headers)

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
        than = self._tao_than_yeu_cau(
            model, messages, stream=False, num_ctx=num_ctx, keep_alive=keep_alive,
            temperature=temperature, max_tokens=max_tokens,
        )
        phan_hoi = await self._gui(
            "POST", self._url_chat(), json_body=than, headers=HEADER_BO_CHAY, timeout=timeout_giay
        )
        if 400 <= phan_hoi.status_code < 500:
            raise _loi_dau_vao(phan_hoi.status_code, phan_hoi.text, ma_yeu_cau)
        phan_hoi.raise_for_status()

        do_tre_ms = round((time.perf_counter() - t0) * 1000, 2)
        mau = self._doc_phan_hoi(phan_hoi.json())
        token_vao = (
            mau.token_vao
            if mau.token_vao is not None
            else sum(dem_token(m.get("content", "")) for m in messages if isinstance(m, dict))
        )
        token_ra = mau.token_ra if mau.token_ra is not None else dem_token(mau.noi_dung)
        sinh_giay = mau.thoi_gian_sinh_giay if mau.thoi_gian_sinh_giay is not None else do_tre_ms / 1000
        return KetQuaGoiLocal(
            noi_dung=mau.noi_dung,
            model=model,
            bac="",
            thoi_gian_nap_ms=mau.thoi_gian_nap_ms if mau.thoi_gian_nap_ms is not None else do_tre_ms,
            do_tre_ms=do_tre_ms,
            toc_do_tok_s=_tinh_toc_do(token_ra, sinh_giay),
            token_vao=token_vao,
            token_ra=token_ra,
            ma_yeu_cau=ma_yeu_cau,
        )

    async def _boc_luong(
        self, phan_hoi: httpx.Response, *, model: str, ma_yeu_cau: str, t0: float
    ) -> AsyncIterator[KetQuaDongLocal]:
        """Phát từng mẩu nội dung, dừng ở dòng kết thúc, cuối cùng phát mẩu chỉ số."""
        t_dau_tien: float | None = None
        token_vao = 0
        token_ra = 0
        van_ban_da_nhan = ""
        async for dong in phan_hoi.aiter_lines():
            mau = self._doc_dong(dong)
            if mau is None:
                continue
            token_vao = mau.token_vao if mau.token_vao is not None else token_vao
            if mau.noi_dung:
                t_dau_tien = t_dau_tien or time.perf_counter()
                van_ban_da_nhan += mau.noi_dung
                token_ra += 1
                yield KetQuaDongLocal(
                    noi_dung=mau.noi_dung, model=model, bac="", ma_yeu_cau=ma_yeu_cau
                )
            token_ra = mau.token_ra if mau.token_ra is not None else token_ra
            if mau.ket_thuc:
                break

        t_ket_thuc = time.perf_counter()
        moc_dau = t_dau_tien or t_ket_thuc
        if token_ra == 0 and van_ban_da_nhan:
            token_ra = dem_token(van_ban_da_nhan)
        yield KetQuaDongLocal(
            noi_dung="",
            da_xong=True,
            model=model,
            bac="",
            ma_yeu_cau=ma_yeu_cau,
            thoi_gian_nap_ms=round((moc_dau - t0) * 1000, 2),
            do_tre_ms=round((t_ket_thuc - t0) * 1000, 2),
            toc_do_tok_s=_tinh_toc_do(token_ra, t_ket_thuc - moc_dau),
            token_vao=token_vao,
            token_ra=token_ra,
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
        """Gửi yêu cầu hoàn thành hội thoại dạng phát theo dòng."""
        t0 = time.perf_counter()
        than = self._tao_than_yeu_cau(
            model, messages, stream=True, num_ctx=num_ctx, keep_alive=keep_alive,
            temperature=temperature, max_tokens=max_tokens,
        )
        han = timeout_giay if timeout_giay is not None else self.timeout_giay
        client = self._client or httpx.AsyncClient(timeout=han)
        try:
            async with client.stream(
                "POST", self._url_chat(), headers=HEADER_BO_CHAY, json=than, timeout=han
            ) as phan_hoi:
                if 400 <= phan_hoi.status_code < 500:
                    noi_dung_loi = (await phan_hoi.aread()).decode("utf-8", errors="replace")
                    raise _loi_dau_vao(phan_hoi.status_code, noi_dung_loi, ma_yeu_cau)
                phan_hoi.raise_for_status()
                async for mau in self._boc_luong(
                    phan_hoi, model=model, ma_yeu_cau=ma_yeu_cau, t0=t0
                ):
                    yield mau
        finally:
            if self._client is None:
                await client.aclose()


class BoChayOllama(BoChay):
    """Bộ chạy Ollama qua API riêng /api/chat.

    Không dùng /v1/chat/completions: giao diện tương thích OpenAI của Ollama bỏ qua
    keep_alive và options.num_ctx (đã kiểm chứng trên Ollama 0.34), khiến model nạp với
    ngữ cảnh mặc định và bị giải phóng theo thời gian mặc định.
    """

    def __init__(
        self,
        dia_chi: str,
        timeout_giay: float = 120.0,
        client: httpx.AsyncClient | None = None,
        *,
        suy_luan: bool = False,
    ) -> None:
        super().__init__(dia_chi, timeout_giay, client)
        self.suy_luan = suy_luan

    def _url_chat(self) -> str:
        return f"{_chuan_hoa_url_goc(self.dia_chi)}/api/chat"

    def _url_nhung(self) -> str:
        return f"{_chuan_hoa_url_goc(self.dia_chi)}/api/embed"

    async def nhung(
        self,
        model: str,
        van_ban: list[str],
        *,
        keep_alive: str = "30m",
        timeout_giay: float | None = None,
        ma_yeu_cau: str = "",
    ) -> KetQuaNhungLocal:
        """Tạo vector nhúng qua POST /api/embed của Ollama.

        Không dùng /v1/embeddings vì giao diện tương thích OpenAI của Ollama bỏ qua keep_alive.
        """
        if not van_ban:
            return KetQuaNhungLocal(
                vectors=[],
                model=model,
                so_chieu=0,
                do_tre_ms=0.0,
                token_vao=0,
            )
        t0 = time.perf_counter()
        than = {
            "model": model,
            "input": van_ban,
            "keep_alive": keep_alive,
        }
        phan_hoi = await self._gui(
            "POST", self._url_nhung(), json_body=than, headers=HEADER_BO_CHAY, timeout=timeout_giay
        )
        if 400 <= phan_hoi.status_code < 500:
            raise _loi_dau_vao(phan_hoi.status_code, phan_hoi.text, ma_yeu_cau)
        phan_hoi.raise_for_status()

        do_tre_ms = round((time.perf_counter() - t0) * 1000, 2)
        du_lieu = phan_hoi.json()
        vectors: list[list[float]] = du_lieu.get("embeddings") or []
        token_vao = du_lieu.get("prompt_eval_count")
        if token_vao is None:
            token_vao = sum(dem_token(t) for t in van_ban)
        so_chieu = len(vectors[0]) if vectors else 0
        return KetQuaNhungLocal(
            vectors=vectors,
            model=model,
            so_chieu=so_chieu,
            do_tre_ms=do_tre_ms,
            token_vao=token_vao,
        )

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
        # keep_alive nằm ở CẤP CAO NHẤT, ngang cấp options; đặt trong options sẽ bị bỏ qua
        tuy_chon: dict[str, Any] = {"num_ctx": num_ctx, "temperature": temperature}
        if max_tokens is not None:
            tuy_chon["num_predict"] = max_tokens
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "think": self.suy_luan,
            "keep_alive": keep_alive,
            "options": tuy_chon,
        }

    def _doc_phan_hoi(self, du_lieu: dict[str, Any]) -> MauTho:
        # Thời gian tới token đầu tiên = nạp model + xử lý câu hỏi (Ollama đo bằng nano giây)
        nap_ns = (du_lieu.get("load_duration") or 0) + (du_lieu.get("prompt_eval_duration") or 0)
        sinh_ns = du_lieu.get("eval_duration")
        return MauTho(
            noi_dung=str(du_lieu.get("message", {}).get("content", "")),
            token_vao=du_lieu.get("prompt_eval_count"),
            token_ra=du_lieu.get("eval_count"),
            thoi_gian_nap_ms=round(nap_ns / 1e6, 2) if nap_ns else None,
            thoi_gian_sinh_giay=sinh_ns / 1e9 if sinh_ns else None,
            ket_thuc=True,
        )

    def _doc_dong(self, dong: str) -> MauTho | None:
        # Luồng của /api/chat là NDJSON: mỗi dòng một đối tượng, dòng cuối có done=true
        du_lieu = _doc_json(dong.strip()) if dong.strip() else None
        if du_lieu is None:
            return None
        return MauTho(
            noi_dung=str(du_lieu.get("message", {}).get("content", "")),
            token_vao=du_lieu.get("prompt_eval_count"),
            token_ra=du_lieu.get("eval_count"),
            ket_thuc=bool(du_lieu.get("done")),
        )

    async def _doc_danh_sach(self, duong_dan: str) -> list[dict[str, Any]]:
        """Đọc danh sách model từ /api/tags hoặc /api/ps."""
        phan_hoi = await self._gui("GET", f"{_chuan_hoa_url_goc(self.dia_chi)}{duong_dan}")
        phan_hoi.raise_for_status()
        return list(phan_hoi.json().get("models", []))

    async def liet_ke_model(self) -> list[str]:
        """Lấy danh sách các mô hình đã tải về thông qua GET /api/tags."""
        return [m["name"] for m in await self._doc_danh_sach("/api/tags") if m.get("name")]

    async def doc_trang_thai_bo_chay(self) -> list[ThongTinModelDangNap]:
        """Đọc danh sách model đang nạp từ GET /api/ps kèm kích thước, VRAM và hết hạn."""
        models = await self._doc_danh_sach("/api/ps")
        ket_qua: list[ThongTinModelDangNap] = []
        for m in models:
            ten = str(m.get("name") or m.get("model") or "")
            if not ten:
                continue
            kich_thuoc = int(m["size"]) if m.get("size") is not None else None
            kich_thuoc_vram = int(m["size_vram"]) if m.get("size_vram") is not None else None
            het_han = m.get("expires_at")
            ket_qua.append(
                ThongTinModelDangNap(
                    ten=ten,
                    kich_thuoc_byte=kich_thuoc,
                    kich_thuoc_vram_byte=kich_thuoc_vram,
                    het_han_luc=str(het_han) if het_han else None,
                )
            )
        return ket_qua

    async def model_dang_nap(self) -> list[str]:
        """Lấy danh sách mô hình đang nạp trong VRAM thông qua doc_trang_thai_bo_chay()."""
        return [m.ten for m in await self.doc_trang_thai_bo_chay()]

    async def _ngu_canh_tu_ps(self, model: str) -> int | None:
        """Đọc context_length của model đang nạp từ /api/ps."""
        for m in await self._doc_danh_sach("/api/ps"):
            if model in (m.get("name"), m.get("model")) and m.get("context_length"):
                return int(m["context_length"])
        return None

    async def _ngu_canh_tu_show(self, model: str) -> int | None:
        """Đọc context_length khai báo của model từ POST /api/show."""
        phan_hoi = await self._gui(
            "POST", f"{_chuan_hoa_url_goc(self.dia_chi)}/api/show", json_body={"model": model}
        )
        phan_hoi.raise_for_status()
        du_lieu = phan_hoi.json()
        for khoa, gia_tri in du_lieu.get("model_info", {}).items():
            if khoa.endswith(".context_length"):
                return int(gia_tri)
        gia_tri_chi_tiet = du_lieu.get("details", {}).get("context_length")
        return int(gia_tri_chi_tiet) if gia_tri_chi_tiet else None

    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc cửa sổ ngữ cảnh thực tế: ưu tiên /api/ps (đang nạp), sau đó /api/show."""
        try:
            return await self._ngu_canh_tu_ps(model) or await self._ngu_canh_tu_show(model)
        except LOI_KICH_HOAT_HA_CAP as err:
            logger.warning("Không đọc được ngữ cảnh thực tế của %s: %s", model, err)
            return None


class BoChayLMStudio(BoChay):
    """Bộ chạy LM Studio qua giao diện /v1 tương thích OpenAI (phát theo dòng dạng SSE)."""

    def _url_chat(self) -> str:
        return f"{self.dia_chi.rstrip('/')}/chat/completions"

    def _url_nhung(self) -> str:
        dia_chi = self.dia_chi.rstrip("/")
        if not dia_chi.endswith("/v1"):
            dia_chi = f"{dia_chi}/v1"
        return f"{dia_chi}/embeddings"

    async def nhung(
        self,
        model: str,
        van_ban: list[str],
        *,
        keep_alive: str = "30m",
        timeout_giay: float | None = None,
        ma_yeu_cau: str = "",
    ) -> KetQuaNhungLocal:
        """Tạo vector nhúng qua POST /v1/embeddings của LM Studio."""
        if not van_ban:
            return KetQuaNhungLocal(
                vectors=[],
                model=model,
                so_chieu=0,
                do_tre_ms=0.0,
                token_vao=0,
            )
        t0 = time.perf_counter()
        than = {
            "model": model,
            "input": van_ban,
        }
        phan_hoi = await self._gui(
            "POST", self._url_nhung(), json_body=than, headers=HEADER_BO_CHAY, timeout=timeout_giay
        )
        if 400 <= phan_hoi.status_code < 500:
            raise _loi_dau_vao(phan_hoi.status_code, phan_hoi.text, ma_yeu_cau)
        phan_hoi.raise_for_status()

        do_tre_ms = round((time.perf_counter() - t0) * 1000, 2)
        du_lieu = phan_hoi.json()
        danh_sach_data = du_lieu.get("data") or []
        danh_sach_data.sort(key=lambda x: x.get("index", 0))
        vectors: list[list[float]] = [item["embedding"] for item in danh_sach_data if "embedding" in item]
        usage = du_lieu.get("usage") or {}
        token_vao = usage.get("prompt_tokens")
        if token_vao is None:
            token_vao = sum(dem_token(t) for t in van_ban)
        so_chieu = len(vectors[0]) if vectors else 0
        return KetQuaNhungLocal(
            vectors=vectors,
            model=model,
            so_chieu=so_chieu,
            do_tre_ms=do_tre_ms,
            token_vao=token_vao,
        )

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
        # LM Studio quản lý ngữ cảnh và thời gian giữ model khi nạp, nên bỏ options và keep_alive
        than: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens is not None:
            than["max_tokens"] = max_tokens
        return than

    def _doc_phan_hoi(self, du_lieu: dict[str, Any]) -> MauTho:
        lua_chon = du_lieu.get("choices") or []
        usage = du_lieu.get("usage") or {}
        return MauTho(
            noi_dung=str(lua_chon[0]["message"]["content"]) if lua_chon else "",
            token_vao=usage.get("prompt_tokens"),
            token_ra=usage.get("completion_tokens"),
            ket_thuc=True,
        )

    def _doc_dong(self, dong: str) -> MauTho | None:
        # SSE: chỉ dòng "data:" mang dữ liệu; "data: [DONE]" kết thúc; dòng rỗng và
        # dòng chú thích (bắt đầu bằng ":") bị bỏ qua
        dong = dong.strip()
        if not dong.startswith("data:"):
            return None
        noi_dung_dong = dong[5:].strip()
        if noi_dung_dong == "[DONE]":
            return MauTho(ket_thuc=True)
        du_lieu = _doc_json(noi_dung_dong)
        if du_lieu is None:
            return None
        lua_chon = du_lieu.get("choices") or []
        usage = du_lieu.get("usage") or {}
        return MauTho(
            noi_dung=str(lua_chon[0].get("delta", {}).get("content") or "") if lua_chon else "",
            token_vao=usage.get("prompt_tokens"),
            token_ra=usage.get("completion_tokens"),
        )

    async def _doc_models(self) -> list[dict[str, Any]]:
        """Đọc danh sách model từ endpoint /models chuẩn OpenAI."""
        phan_hoi = await self._gui("GET", f"{self.dia_chi.rstrip('/')}/models")
        phan_hoi.raise_for_status()
        return list(phan_hoi.json().get("data", []))

    async def liet_ke_model(self) -> list[str]:
        """Lấy danh sách các mô hình qua endpoint /models chuẩn OpenAI."""
        return [m["id"] for m in await self._doc_models() if m.get("id")]

    async def _doc_models_v0(self) -> list[dict[str, Any]]:
        """Đọc danh sách model từ REST API /api/v0/models của LM Studio."""
        phan_hoi = await self._gui("GET", f"{_chuan_hoa_url_goc(self.dia_chi)}/api/v0/models")
        phan_hoi.raise_for_status()
        return list(phan_hoi.json().get("data", []))

    async def doc_trang_thai_bo_chay(self) -> list[ThongTinModelDangNap]:
        """Đọc danh sách model đang nạp từ REST API /api/v0/models của LM Studio."""
        try:
            danh_sach = await self._doc_models_v0()
        except LOI_KICH_HOAT_HA_CAP:
            danh_sach = await self._doc_models()
        ket_qua: list[ThongTinModelDangNap] = []
        for m in danh_sach:
            trang_thai = m.get("state")
            if trang_thai is None or trang_thai == "loaded":
                ten = str(m.get("id") or m.get("name") or "")
                if not ten:
                    continue
                kich_thuoc = int(m["size_bytes"]) if m.get("size_bytes") is not None else None
                ket_qua.append(
                    ThongTinModelDangNap(
                        ten=ten,
                        kich_thuoc_byte=kich_thuoc,
                        kich_thuoc_vram_byte=None,
                        het_han_luc=None,
                    )
                )
        return ket_qua

    async def model_dang_nap(self) -> list[str]:
        """LM Studio trả danh sách model đang nạp thông qua doc_trang_thai_bo_chay()."""
        return [m.ten for m in await self.doc_trang_thai_bo_chay()]

    async def doc_ngu_canh_thuc_te(self, model: str) -> int | None:
        """Đọc ngữ cảnh từ trường context_length trong danh sách /models nếu có."""
        try:
            danh_sach = await self._doc_models()
        except LOI_KICH_HOAT_HA_CAP as err:
            logger.warning("Không đọc được ngữ cảnh thực tế của %s: %s", model, err)
            return None
        for m in danh_sach:
            gia_tri = m.get("context_length") or m.get("max_context_length")
            if m.get("id") == model and gia_tri:
                return int(gia_tri)
        return None


def lay_bo_chay(
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> BoChay:
    """Khởi tạo bộ chạy theo LOAI_BO_CHAY của cấu hình được truyền (mặc định: toàn cục)."""
    cfg = cau_hinh_he_thong or cau_hinh
    bo_chay = cfg.bo_chay
    han = float(bo_chay.timeout_giay)
    if bo_chay.loai == "ollama":
        return BoChayOllama(
            dia_chi=bo_chay.dia_chi,
            timeout_giay=han,
            client=client,
            suy_luan=cfg.local_chung.suy_luan,
        )
    if bo_chay.loai == "lmstudio":
        return BoChayLMStudio(dia_chi=bo_chay.dia_chi, timeout_giay=han, client=client)
    raise ValueError(f"LOAI_BO_CHAY không hợp lệ: '{bo_chay.loai}'. Chỉ hỗ trợ ollama hoặc lmstudio.")


def _lap_ke_hoach_bac(
    cfg: CauHinhHeThong,
    do_dai_hang_doi: int,
    ma_yeu_cau: str,
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> tuple[list[CauHinhBacLocal], dict[str, str]]:
    """Chọn các bậc sẽ thử theo thứ tự; trả kèm lý do đã bỏ qua bậc nào.

    Chú thích kỹ thuật:
    - Khi bac_ep="chinh" hoặc "nho": Ép chạy đúng bậc tương ứng (dùng riêng cho runner).
    - Khi uu_tien_bac_nho=True: Dùng bậc nhỏ để không chiếm khe của model chính,
      và không gửi nội dung hội thoại ra đám mây chỉ để đặt tiêu đề.
    - NGOẠI LỆ: Khi so_model_nap_cung_luc = 1 (gpu8 trên laptop), dùng bậc chinh đang nằm
      trong VRAM, vì nạp bậc nho sẽ đẩy model chính ra và người hỏi tiếp theo phải chờ nạp lại.
    """
    if bac_ep == "chinh":
        return [cfg.bac_local[0]], {}
    if bac_ep == "nho":
        return [cfg.bac_local[1]], {}

    if uu_tien_bac_nho:
        if cfg.so_model_nap_cung_luc == 1:
            ly_do_ngoai_le = (
                f"so_model_nap_cung_luc=1: giữ bậc chinh ({cfg.bac_local[0].model}) "
                "đang nạp trong VRAM để tránh đẩy model ra ngoài"
            )
            logger.info("[%s] %s", ma_yeu_cau, ly_do_ngoai_le)
            return [cfg.bac_local[0]], {}

        ly_do_bac_nho = (
            f"Ưu tiên bậc nho ({cfg.bac_local[1].model}) để không chiếm khe model chính "
            f"khi so_model_nap_cung_luc={cfg.so_model_nap_cung_luc}"
        )
        logger.info("[%s] %s", ma_yeu_cau, ly_do_bac_nho)
        return [cfg.bac_local[1]], {"chinh": ly_do_bac_nho}

    nguong = cfg.local_chung.nguong_hang_doi_ha_cap
    # Khi chỉ nạp được một model, đổi model trong VRAM mất 5-20 giây và đẩy bậc chinh ra,
    # chậm hơn cả việc chờ: không bỏ qua bậc 1 vì hàng đợi.
    if cfg.so_model_nap_cung_luc > 1 and do_dai_hang_doi > nguong:
        ly_do = (
            f"Bỏ qua bậc 1 vì hàng đợi dài ({do_dai_hang_doi} > {nguong}) "
            f"và so_model_nap_cung_luc={cfg.so_model_nap_cung_luc}"
        )
        logger.info("[%s] %s", ma_yeu_cau, ly_do)
        return [cfg.bac_local[1]], {"chinh": ly_do}
    return list(cfg.bac_local), {}


def _ghi_ly_do_that_bai(bac: CauHinhBacLocal, err: Exception, ma_yeu_cau: str) -> str:
    """Ghi nhật ký và trả lý do một bậc thất bại để gom vào LoiHetBacLocal."""
    ly_do = f"Bậc {bac.bac} ({bac.model}) thất bại: {type(err).__name__}: {err}"
    logger.warning("[%s] %s", ma_yeu_cau, ly_do)
    return ly_do


def _loi_het_bac(ly_do: dict[str, str], ma_yeu_cau: str) -> LoiHetBacLocal:
    """Tạo LoiHetBacLocal kèm lý do của từng bậc."""
    return LoiHetBacLocal(
        f"Hết cả hai bậc local cho yêu cầu {ma_yeu_cau}. "
        f"Bậc 1: {ly_do.get('chinh')}. Bậc 2: {ly_do.get('nho')}.",
        ly_do_bac_1=ly_do.get("chinh"),
        ly_do_bac_2=ly_do.get("nho"),
        ma_yeu_cau=ma_yeu_cau,
    )


def _tham_so_goi(
    cfg: CauHinhHeThong, temperature: float | None, max_tokens: int | None
) -> dict[str, Any]:
    """Gom tham số gọi dùng chung cho mọi bậc."""
    return {
        "keep_alive": cfg.local_chung.keep_alive,
        "temperature": temperature if temperature is not None else cfg.local_chung.nhiet_do,
        "max_tokens": max_tokens if max_tokens is not None else cfg.cai_dat_chung.gioi_han_token_ra,
    }


async def _goi_local_mot_lan(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int,
    bo_chay: BoChay,
    cfg: CauHinhHeThong,
    tham_so: dict[str, Any],
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> KetQuaGoiLocal:
    """Thử lần lượt từng bậc cho lời gọi không phát theo dòng."""
    cac_bac, ly_do = _lap_ke_hoach_bac(
        cfg, do_dai_hang_doi, ma_yeu_cau, uu_tien_bac_nho=uu_tien_bac_nho, bac_ep=bac_ep
    )
    for bac in cac_bac:
        try:
            kq = await bo_chay.goi(
                bac.model, tin_nhan, num_ctx=bac.num_ctx, ma_yeu_cau=ma_yeu_cau, **tham_so
            )
        except LOI_KICH_HOAT_HA_CAP as err:
            ly_do[bac.bac] = _ghi_ly_do_that_bai(bac, err, ma_yeu_cau)
            continue
        kq.bac = bac.bac
        kq.do_dai_hang_doi = do_dai_hang_doi
        return kq
    raise _loi_het_bac(ly_do, ma_yeu_cau)


async def _goi_local_theo_dong(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int,
    bo_chay: BoChay,
    cfg: CauHinhHeThong,
    tham_so: dict[str, Any],
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> AsyncIterator[KetQuaDongLocal]:
    """Thử lần lượt từng bậc cho luồng phát theo dòng."""
    cac_bac, ly_do = _lap_ke_hoach_bac(
        cfg, do_dai_hang_doi, ma_yeu_cau, uu_tien_bac_nho=uu_tien_bac_nho, bac_ep=bac_ep
    )
    for bac in cac_bac:
        da_phat = False
        try:
            async for mau in bo_chay.goi_theo_dong(
                bac.model, tin_nhan, num_ctx=bac.num_ctx, ma_yeu_cau=ma_yeu_cau, **tham_so
            ):
                da_phat = True
                mau.bac = bac.bac
                yield mau
            return
        except LOI_KICH_HOAT_HA_CAP as err:
            # Đã gửi một phần câu trả lời cho người dùng thì không thể đổi sang model khác
            if da_phat:
                raise
            ly_do[bac.bac] = _ghi_ly_do_that_bai(bac, err, ma_yeu_cau)
    raise _loi_het_bac(ly_do, ma_yeu_cau)


@overload
async def goi_local(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int = 0,
    phat_theo_dong: Literal[False] = False,
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> KetQuaGoiLocal: ...


@overload
async def goi_local(
    tin_nhan: list[dict[str, str]],
    *,
    ma_yeu_cau: str,
    do_dai_hang_doi: int = 0,
    phat_theo_dong: Literal[True],
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> AsyncIterator[KetQuaDongLocal]: ...


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
    uu_tien_bac_nho: bool = False,
    bac_ep: str | None = None,
) -> KetQuaGoiLocal | AsyncIterator[KetQuaDongLocal]:
    """Gọi chuỗi local theo thứ tự bậc 1 (chinh) rồi bậc 2 (nho).

    Hạ cấp khi quá hạn, lỗi kết nối hoặc 5xx; lỗi 4xx nổi lên dạng LoiDauVao.
    Hết hai bậc thì ném LoiHetBacLocal để router quyết định bước tiếp theo.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    tham_so_chung: dict[str, Any] = {
        "ma_yeu_cau": ma_yeu_cau,
        "do_dai_hang_doi": do_dai_hang_doi,
        "bo_chay": bo_chay or lay_bo_chay(cfg),
        "cfg": cfg,
        "tham_so": _tham_so_goi(cfg, temperature, max_tokens),
        "uu_tien_bac_nho": uu_tien_bac_nho,
        "bac_ep": bac_ep,
    }
    if phat_theo_dong:
        return _goi_local_theo_dong(tin_nhan, **tham_so_chung)
    return await _goi_local_mot_lan(tin_nhan, **tham_so_chung)


async def ham_nong(
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> bool:
    """Nạp sẵn model bậc 1 bằng một lời gọi 'xin chào' với max_tokens=1.

    CHỈ hâm nóng bậc 1; không bao giờ hâm nóng bậc 2 khi so_model_nap_cung_luc = 1.
    Trả False thay vì ném lỗi để không chặn khởi động ứng dụng.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    runner = bo_chay or lay_bo_chay(cfg)
    bac_1 = cfg.bac_local[0]
    try:
        await runner.goi(
            bac_1.model,
            [{"role": "user", "content": "xin chào"}],
            num_ctx=bac_1.num_ctx,
            keep_alive=cfg.local_chung.keep_alive,
            temperature=cfg.local_chung.nhiet_do,
            max_tokens=1,
            ma_yeu_cau="ham_nong_khoi_dong",
        )
    except (*LOI_KICH_HOAT_HA_CAP, LoiDauVao) as err:
        logger.warning("Hâm nóng bậc 1 (%s) thất bại, không chặn khởi động: %s", bac_1.model, err)
        return False
    logger.info("Hâm nóng bậc 1 (%s) thành công.", bac_1.model)
    return True


async def _dang_nap(runner: BoChay, model: str) -> bool:
    """Model có đang nằm trong bộ nhớ của bộ chạy hay không (lỗi mạng coi như không)."""
    try:
        return model in await runner.model_dang_nap()
    except LOI_KICH_HOAT_HA_CAP:
        return False


async def doc_ngu_canh_thuc_te(
    model: str,
    bo_chay: BoChay | None = None,
    cau_hinh_he_thong: CauHinhHeThong | None = None,
) -> int | None:
    """Đọc cửa sổ ngữ cảnh thực tế của model và cảnh báo nếu lệch num_ctx cấu hình.

    Model đang nạp: số đọc được là ngữ cảnh đang dùng, lệch theo hướng nào cũng cảnh báo
    (lớn hơn thì tốn VRAM, nhỏ hơn thì câu hỏi dài bị cắt). Model chưa nạp: số đọc được
    là ngữ cảnh tối đa của model, chỉ cảnh báo khi nhỏ hơn cấu hình.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    runner = bo_chay or lay_bo_chay(cfg)
    thuc_te = await runner.doc_ngu_canh_thuc_te(model)
    cau_hinh_ctx = next((b.num_ctx for b in cfg.bac_local if b.model == model), None)
    if thuc_te is None or cau_hinh_ctx is None or thuc_te == cau_hinh_ctx:
        return thuc_te
    if await _dang_nap(runner, model):
        logger.warning(
            "Model '%s' đang chạy với context_length=%d, khác num_ctx cấu hình %d.",
            model, thuc_te, cau_hinh_ctx,
        )
    elif thuc_te < cau_hinh_ctx:
        logger.warning(
            "Model '%s' chỉ hỗ trợ context_length=%d, nhỏ hơn num_ctx cấu hình %d.",
            model, thuc_te, cau_hinh_ctx,
        )
    return thuc_te


async def kiem_tra_khi_khoi_dong(cau_hinh_he_thong: CauHinhHeThong | None = None) -> None:
    """Hâm nóng bậc 1 rồi so ngữ cảnh thực tế của hai bậc với cấu hình.

    Gọi nền từ lifespan của FastAPI; chỉ ghi nhật ký, không bao giờ làm hỏng khởi động.
    """
    cfg = cau_hinh_he_thong or cau_hinh
    runner = lay_bo_chay(cfg)
    await ham_nong(runner, cfg)
    for bac in cfg.bac_local:
        await doc_ngu_canh_thuc_te(bac.model, runner, cfg)
