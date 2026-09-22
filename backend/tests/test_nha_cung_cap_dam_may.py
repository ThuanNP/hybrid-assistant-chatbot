"""Bộ kiểm thử đơn vị cho kết nối nhà cung cấp đám mây qua LiteLLM (nha_cung_cap_dam_may.py).

Toàn bộ các ca kiểm thử sử dụng monkeypatch để giả lập LiteLLM, tuyệt đối không gọi mạng thật.
"""

from typing import Any

import litellm
import litellm.exceptions
import pytest

from app.config import CauHinhTangDamMay
from app.core.loi import LoiDauVao, LoiTamThoi, LoiVinhVien
from app.llm.nha_cung_cap_dam_may import goi_dam_may

TANG_GEMINI = CauHinhTangDamMay(
    tang=1,
    ten="gemini",
    model="gemini/gemini-3.5-flash-lite",
    api_key_env="GOOGLE_API_KEY",
    gia_vao_usd_moi_trieu=0.30,
    gia_ra_usd_moi_trieu=2.50,
    timeout_giay=60,
    cua_so_ngu_canh=1000000,
)

TANG_OPENROUTER = CauHinhTangDamMay(
    tang=2,
    ten="openrouter_auto",
    model="openrouter/auto",
    api_key_env="OPENROUTER_API_KEY",
    tham_so_them={"cost_tier": "low"},
    gia_vao_usd_moi_trieu=0.50,
    gia_ra_usd_moi_trieu=3.00,
    timeout_giay=90,
    cua_so_ngu_canh=128000,
)


class MockMessage:
    """Đối tượng giả lập message trong phản hồi LiteLLM."""

    def __init__(self, content: str) -> None:
        self.content = content


class MockChoice:
    """Đối tượng giả lập choice trong phản hồi LiteLLM."""

    def __init__(self, content: str) -> None:
        self.message = MockMessage(content)


class MockUsage:
    """Đối tượng giả lập usage token trong phản hồi LiteLLM."""

    def __init__(self, prompt_tokens: int = 15, completion_tokens: int = 25) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class MockResponse:
    """Đối tượng giả lập phản hồi của litellm.acompletion dạng không phát dòng."""

    def __init__(
        self,
        content: str = "Phản hồi thử nghiệm",
        model: str = "gemini/gemini-3.5-flash-lite",
        prompt_tokens: int = 15,
        completion_tokens: int = 25,
    ) -> None:
        self.choices = [MockChoice(content)]
        self.model = model
        self.usage = MockUsage(prompt_tokens, completion_tokens)


@pytest.fixture(autouse=True)
def bo_qua_asyncio_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bỏ qua thời gian ngủ thật trong asyncio.sleep để kiểm thử chạy tức thì."""

    async def sleep_nhanh(_thoi_gian: float) -> None:
        return None

    monkeypatch.setattr("app.llm.nha_cung_cap_dam_may.asyncio.sleep", sleep_nhanh)


async def test_loi_tam_thoi_429_thu_lai_thanh_cong(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 hai lần rồi thành công -> thử lại đúng 3 lần, so_lan_thu = 3."""
    so_lan_goi = 0

    async def gia_lap_acompletion(**_kwargs: Any) -> MockResponse:
        nonlocal so_lan_goi
        so_lan_goi += 1
        if so_lan_goi < 3:
            raise litellm.exceptions.RateLimitError(
                message="Quá tải hạn mức 429",
                llm_provider="gemini",
                model=TANG_GEMINI.model,
            )
        return MockResponse("Thành công sau khi thử lại", model=TANG_GEMINI.model)

    monkeypatch.setattr(litellm, "acompletion", gia_lap_acompletion)
    monkeypatch.setenv("GOOGLE_API_KEY", "khoa-gia-lap-hop-le")

    kq = await goi_dam_may(
        TANG_GEMINI,
        [{"role": "user", "content": "Xin chào"}],
        ma_yeu_cau="req-retry-success",
        so_lan_thu_lai_moi_tang=2,
        giay_gian_cach_dau=0.001,
    )

    assert so_lan_goi == 3
    assert kq.so_lan_thu == 3
    assert kq.noi_dung == "Thành công sau khi thử lại"
    assert kq.model == TANG_GEMINI.model
    assert kq.tang == 1
    assert kq.token_vao == 15
    assert kq.token_ra == 25


async def test_loi_tam_thoi_429_lien_tuc_nem_loi_tam_thoi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 liên tục -> ném LoiTamThoi sau đúng 1 + so_lan_thu_lai_moi_tang lần gọi."""
    so_lan_goi = 0

    async def gia_lap_acompletion(**_kwargs: Any) -> MockResponse:
        nonlocal so_lan_goi
        so_lan_goi += 1
        raise litellm.exceptions.RateLimitError(
            message="Quá tải liên tục 429",
            llm_provider="gemini",
            model=TANG_GEMINI.model,
        )

    monkeypatch.setattr(litellm, "acompletion", gia_lap_acompletion)
    monkeypatch.setenv("GOOGLE_API_KEY", "khoa-gia-lap-hop-le")

    so_lan_thu_lai = 2
    with pytest.raises(LoiTamThoi) as thong_tin_loi:
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Xin chào"}],
            ma_yeu_cau="req-retry-exhausted",
            so_lan_thu_lai_moi_tang=so_lan_thu_lai,
            giay_gian_cach_dau=0.001,
        )

    assert so_lan_goi == 1 + so_lan_thu_lai
    assert thong_tin_loi.value.so_lan_thu == 1 + so_lan_thu_lai
    assert thong_tin_loi.value.ma_trang_thai == 429
    assert thong_tin_loi.value.ma_yeu_cau == "req-retry-exhausted"


async def test_loi_vinh_vien_401_khong_thu_lai(monkeypatch: pytest.MonkeyPatch) -> None:
    """401 sai khoá -> ném LoiVinhVien, không thử lại (đếm số lần gọi = 1)."""
    so_lan_goi = 0

    async def gia_lap_acompletion(**_kwargs: Any) -> MockResponse:
        nonlocal so_lan_goi
        so_lan_goi += 1
        raise litellm.exceptions.AuthenticationError(
            message="Khoá API không hợp lệ",
            llm_provider="gemini",
            model=TANG_GEMINI.model,
        )

    monkeypatch.setattr(litellm, "acompletion", gia_lap_acompletion)
    monkeypatch.setenv("GOOGLE_API_KEY", "khoa-sai-401")

    with pytest.raises(LoiVinhVien) as thong_tin_loi:
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Xin chào"}],
            ma_yeu_cau="req-auth-fail",
            so_lan_thu_lai_moi_tang=2,
            giay_gian_cach_dau=0.001,
        )

    assert so_lan_goi == 1
    assert thong_tin_loi.value.ma_trang_thai == 401
    assert thong_tin_loi.value.ma_yeu_cau == "req-auth-fail"


async def test_loi_dau_vao_400_khong_roi_tang(monkeypatch: pytest.MonkeyPatch) -> None:
    """400 lời nhắc quá dài / bị chặn -> ném LoiDauVao của app.core.loi, không rơi tầng."""
    so_lan_goi = 0

    async def gia_lap_acompletion(**_kwargs: Any) -> MockResponse:
        nonlocal so_lan_goi
        so_lan_goi += 1
        raise litellm.exceptions.BadRequestError(
            message="Context window exceeded",
            llm_provider="gemini",
            model=TANG_GEMINI.model,
        )

    monkeypatch.setattr(litellm, "acompletion", gia_lap_acompletion)
    monkeypatch.setenv("GOOGLE_API_KEY", "khoa-hop-le")

    with pytest.raises(LoiDauVao) as thong_tin_loi:
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Yêu cầu quá dài"}],
            ma_yeu_cau="req-bad-input",
            so_lan_thu_lai_moi_tang=2,
            giay_gian_cach_dau=0.001,
        )

    assert so_lan_goi == 1
    assert isinstance(thong_tin_loi.value, LoiDauVao)
    assert thong_tin_loi.value.ma_trang_thai == 400
    assert thong_tin_loi.value.ma_yeu_cau == "req-bad-input"


async def test_openrouter_auto_ghi_model_thuc_va_uoc_tinh_chi_phi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """openrouter/auto: đọc tên model thực tế trong phản hồi, chi_phi_la_uoc_tinh_tho=True."""
    model_thuc_te = "meta-llama/llama-3.3-70b-instruct"

    async def gia_lap_acompletion(**kwargs: Any) -> MockResponse:
        assert kwargs.get("extra_body") == {"cost_tier": "low"}
        return MockResponse("Câu trả lời từ openrouter", model=model_thuc_te)

    monkeypatch.setattr(litellm, "acompletion", gia_lap_acompletion)
    monkeypatch.setenv("OPENROUTER_API_KEY", "khoa-openrouter-hop-le")

    kq = await goi_dam_may(
        TANG_OPENROUTER,
        [{"role": "user", "content": "Tư vấn điện"}],
        ma_yeu_cau="req-openrouter-auto",
    )

    assert kq.model == model_thuc_te
    assert kq.chi_phi_la_uoc_tinh_tho is True
    assert kq.tang == 2


async def test_khoa_api_khong_xuat_hien_trong_nhat_ky(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Khoá API tuyệt đối không xuất hiện trong bất kỳ bản ghi nhật ký nào."""
    chuoi_khoa_bi_mat = "sk-super-secret-key-that-must-never-be-logged-12345"
    monkeypatch.setenv("GOOGLE_API_KEY", chuoi_khoa_bi_mat)

    # 1. Khi gặp lỗi xác thực 401
    async def gia_lap_loi_401(**_kwargs: Any) -> MockResponse:
        raise litellm.exceptions.AuthenticationError(
            message=f"Unauthorized access with {chuoi_khoa_bi_mat}",
            llm_provider="gemini",
            model=TANG_GEMINI.model,
        )

    monkeypatch.setattr(litellm, "acompletion", gia_lap_loi_401)

    with pytest.raises(LoiVinhVien):
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Test bảo mật khoá"}],
            ma_yeu_cau="req-secret-check-401",
        )

    # 2. Khi gặp lỗi tạm thời 429
    async def gia_lap_loi_429(**_kwargs: Any) -> MockResponse:
        raise litellm.exceptions.RateLimitError(
            message=f"Rate limit for key {chuoi_khoa_bi_mat}",
            llm_provider="gemini",
            model=TANG_GEMINI.model,
        )

    monkeypatch.setattr(litellm, "acompletion", gia_lap_loi_429)

    with pytest.raises(LoiTamThoi):
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Test bảo mật khoá 429"}],
            ma_yeu_cau="req-secret-check-429",
            so_lan_thu_lai_moi_tang=1,
            giay_gian_cach_dau=0.001,
        )

    # 3. Khi thiếu khoá API
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.nha_cung_cap_dam_may.lay_khoa_api", lambda _k: None)

    with pytest.raises(LoiVinhVien):
        await goi_dam_may(
            TANG_GEMINI,
            [{"role": "user", "content": "Test thiếu khoá"}],
            ma_yeu_cau="req-secret-missing",
        )

    # Khẳng định chuỗi khoá bí mật không hề có trong bất kỳ dòng log nào
    assert chuoi_khoa_bi_mat not in caplog.text
