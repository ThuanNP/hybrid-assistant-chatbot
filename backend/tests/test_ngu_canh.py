"""Bộ kiểm thử cho mô-đun quản lý ngữ cảnh hội thoại (ngu_canh.py).

Tuân thủ đầy đủ 6 kịch bản kiểm thử bắt buộc:
1. Cắt đúng số lượt khi lịch sử vượt ngân sách.
2. Không bao giờ cắt lời nhắc hệ thống.
3. Không cắt lẻ nửa cặp (luôn giữ theo cặp câu hỏi + câu đáp).
4. Cờ da_cat và thông báo đánh dấu hoạt động chính xác.
5. Ném ngoại lệ NGU_CANH_QUA_DAI khi riêng tin nhắn mới cộng lời nhắc hệ thống vượt ngân sách.
6. Ngân sách token của chuỗi đầy đủ [0, 1, 2, 3, 4] bằng ngân sách của bậc nho local.
"""

import pytest

from app.config import (
    CauHinhBacLocal,
    CauHinhCaiDatChung,
    CauHinhHeThong,
    CauHinhTangDamMay,
    cau_hinh,
)
from app.core.loi import LoiNguCanhQuaDai, NGU_CANH_QUA_DAI
from app.chat.ngu_canh import (
    THONG_BAO_CAT_NGU_CANH,
    KetQuaNguCanh,
    dung_ngu_canh,
    tinh_ngan_sach_token,
    uoc_luong_so_luot_giu_duoc,
)
from app.llm.chinh_sach import Tang
from app.llm.dem_token import dem_token


def _tao_cau_hinh_gia_lap(
    num_ctx_chinh: int = 8192,
    num_ctx_nho: int = 4096,
    gioi_han_token_ra: int = 1024,
    ngu_canh_du_phong_token: int = 512,
    he_so_an_toan_token: float = 1.15,
) -> CauHinhHeThong:
    """Tạo đối tượng CauHinhHeThong giả lập với các thông số ngữ cảnh xác định."""
    cfg = cau_hinh.model_copy(deep=True)
    cfg.bac_local = [
        CauHinhBacLocal(bac="chinh", model="qwen3.5:4b-q8_0", num_ctx=num_ctx_chinh),
        CauHinhBacLocal(bac="nho", model="qwen3.5:2b-q8_0", num_ctx=num_ctx_nho),
    ]
    cfg.cai_dat_chung = CauHinhCaiDatChung(
        so_lan_thu_lai_moi_tang=2,
        giay_gian_cach_dau=0.5,
        gioi_han_token_ra=gioi_han_token_ra,
        ngu_canh_du_phong_token=ngu_canh_du_phong_token,
        he_so_an_toan_token=he_so_an_toan_token,
    )
    cfg.chuoi_dam_may = [
        CauHinhTangDamMay(
            tang=1,
            ten="gemini",
            model="gemini/gemini-3.5-flash-lite",
            api_key_env="GOOGLE_API_KEY",
            gia_vao_usd_moi_trieu=0.3,
            gia_ra_usd_moi_trieu=2.5,
            cua_so_ngu_canh=1000000,
        ),
        CauHinhTangDamMay(
            tang=2,
            ten="openrouter_auto",
            model="openrouter/auto",
            api_key_env="OPENROUTER_API_KEY",
            gia_vao_usd_moi_trieu=0.5,
            gia_ra_usd_moi_trieu=3.0,
            cua_so_ngu_canh=128000,
        ),
        CauHinhTangDamMay(
            tang=3,
            ten="claude",
            model="anthropic/claude-sonnet-5",
            api_key_env="ANTHROPIC_API_KEY",
            gia_vao_usd_moi_trieu=3.0,
            gia_ra_usd_moi_trieu=15.0,
            cua_so_ngu_canh=200000,
        ),
        CauHinhTangDamMay(
            tang=4,
            ten="openai",
            model="openai/gpt-5.6-terra",
            api_key_env="OPENAI_API_KEY",
            gia_vao_usd_moi_trieu=2.0,
            gia_ra_usd_moi_trieu=12.0,
            cua_so_ngu_canh=400000,
        ),
    ]
    return cfg


def test_cat_dung_so_luot() -> None:
    """1. Kiểm tra cắt đúng số lượt khi lịch sử hội thoại vượt quá ngân sách."""
    cfg = _tao_cau_hinh_gia_lap(num_ctx_nho=2000, gioi_han_token_ra=500, ngu_canh_du_phong_token=200, he_so_an_toan_token=1.0)
    # Ngân sách thô = 2000 - 500 - 200 = 1300 token.
    chuoi = [Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=2000)]
    loi_nhac = "Lời nhắc hệ thống ngắn"
    tin_moi = "Câu hỏi mới"

    # Mỗi cặp gồm câu hỏi và đáp, dài khoảng 300 token
    doan_dai = "văn bản nghiệp vụ điện lực tra cứu chỉ số công tơ " * 25
    lich_su = [
        {"role": "user", "content": f"Câu hỏi 1: {doan_dai}"},
        {"role": "assistant", "content": f"Trả lời 1: {doan_dai}"},
        {"role": "user", "content": f"Câu hỏi 2: {doan_dai}"},
        {"role": "assistant", "content": f"Trả lời 2: {doan_dai}"},
        {"role": "user", "content": f"Câu hỏi 3: {doan_dai}"},
        {"role": "assistant", "content": f"Trả lời 3: {doan_dai}"},
        {"role": "user", "content": f"Câu hỏi 4: {doan_dai}"},
        {"role": "assistant", "content": f"Trả lời 4: {doan_dai}"},
    ]

    kq = dung_ngu_canh(
        lich_su,
        tin_moi,
        chuoi,
        cau_hinh_he_thong=cfg,
        loi_nhac_he_thong=loi_nhac,
    )

    assert kq.da_cat is True
    assert kq.so_luot_bi_cat > 0
    # Tổng số cặp giữ lại phải bằng 4 trừ đi số lượt bị cắt
    so_cap_giu = (len(kq.danh_sach) - 3) // 2  # Trừ system, thong_bao, tin_moi
    assert so_cap_giu == 4 - kq.so_luot_bi_cat


def test_khong_bao_gio_cat_loi_nhac_he_thong() -> None:
    """2. Kiểm tra lời nhắc hệ thống luôn luôn được giữ ở đầu danh sách dù cắt hết lịch sử."""
    cfg = _tao_cau_hinh_gia_lap(num_ctx_nho=1800, gioi_han_token_ra=500, ngu_canh_du_phong_token=200, he_so_an_toan_token=1.0)
    chuoi = [Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=1800)]
    loi_nhac = "Đây là Lời Nhắc Hệ Thống Tối Quan Trọng Bắt Buộc Không Được Cắt"
    tin_moi = "Tin nhắn người dùng"

    doan_dai = "dữ liệu lịch sử hội thoại rất dài cần cắt bỏ " * 40
    lich_su = [
        {"role": "user", "content": doan_dai},
        {"role": "assistant", "content": doan_dai},
    ]

    kq = dung_ngu_canh(
        lich_su,
        tin_moi,
        chuoi,
        cau_hinh_he_thong=cfg,
        loi_nhac_he_thong=loi_nhac,
    )

    assert kq.danh_sach[0]["role"] == "system"
    assert kq.danh_sach[0]["content"] == loi_nhac
    assert kq.danh_sach[-1]["role"] == "user"
    assert kq.danh_sach[-1]["content"] == tin_moi


def test_khong_cat_le_nua_cap() -> None:
    """3. Kiểm tra việc cắt tỉa theo CẶP hoàn chỉnh, không bao giờ để lại nửa cặp lẻ."""
    cfg = _tao_cau_hinh_gia_lap(num_ctx_nho=2500, gioi_han_token_ra=500, ngu_canh_du_phong_token=200, he_so_an_toan_token=1.0)
    chuoi = [Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=2500)]
    loi_nhac = "Hệ thống"
    tin_moi = "Câu hỏi mới"

    doan_300 = "thông tin kiểm tra định kỳ công tơ điện tử " * 30
    lich_su = [
        {"role": "user", "content": f"Hỏi 1: {doan_300}"},
        {"role": "assistant", "content": f"Đáp 1: {doan_300}"},
        {"role": "user", "content": f"Hỏi 2: {doan_300}"},
        {"role": "assistant", "content": f"Đáp 2: {doan_300}"},
        {"role": "user", "content": f"Hỏi 3: {doan_300}"},
        {"role": "assistant", "content": f"Đáp 3: {doan_300}"},
    ]

    kq = dung_ngu_canh(
        lich_su,
        tin_moi,
        chuoi,
        cau_hinh_he_thong=cfg,
        loi_nhac_he_thong=loi_nhac,
    )

    # Các tin nhắn sau thông báo cắt (bỏ system đầu, thông báo cắt, và tin mới cuối)
    tin_lich_su_giu = kq.danh_sach[2:-1]
    assert len(tin_lich_su_giu) % 2 == 0
    for idx in range(0, len(tin_lich_su_giu), 2):
        assert tin_lich_su_giu[idx]["role"] == "user"
        assert tin_lich_su_giu[idx + 1]["role"] == "assistant"


def test_co_da_cat_va_thong_bao_dung() -> None:
    """4. Kiểm tra cờ da_cat và thông báo đánh dấu khi có hoặc không có cắt tỉa."""
    cfg = _tao_cau_hinh_gia_lap()
    chuoi = [Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=4096)]

    # Trường hợp 1: Ngắn, không cắt tỉa
    lich_su_ngan = [
        {"role": "user", "content": "Xin chào trợ lý"},
        {"role": "assistant", "content": "Chào Anh/Chị, tôi có thể hỗ trợ gì ạ?"},
    ]
    kq_khong_cat = dung_ngu_canh(
        lich_su_ngan,
        "Hôm nay trời nắng không?",
        chuoi,
        cau_hinh_he_thong=cfg,
        loi_nhac_he_thong="Lời nhắc",
    )
    assert kq_khong_cat.da_cat is False
    assert kq_khong_cat.so_luot_bi_cat == 0
    assert not any(m["content"] == THONG_BAO_CAT_NGU_CANH for m in kq_khong_cat.danh_sach)

    # Trường hợp 2: Dài, có cắt tỉa
    cfg_hep = _tao_cau_hinh_gia_lap(num_ctx_nho=1600, gioi_han_token_ra=500, ngu_canh_du_phong_token=200, he_so_an_toan_token=1.0)
    lich_su_dai = [
        {"role": "user", "content": "Dòng trao đổi rất dài " * 50},
        {"role": "assistant", "content": "Câu phản hồi dài " * 50},
        {"role": "user", "content": "Dòng trao đổi thứ hai " * 50},
        {"role": "assistant", "content": "Câu phản hồi thứ hai " * 50},
    ]
    kq_co_cat = dung_ngu_canh(
        lich_su_dai,
        "Câu hỏi cuối",
        chuoi,
        cau_hinh_he_thong=cfg_hep,
        loi_nhac_he_thong="Lời nhắc",
    )
    assert kq_co_cat.da_cat is True
    assert kq_co_cat.so_luot_bi_cat > 0
    # Phải có thông báo đánh dấu nằm ngay sau lời nhắc hệ thống
    assert kq_co_cat.danh_sach[1]["content"] == THONG_BAO_CAT_NGU_CANH


def test_nem_ngu_canh_qua_dai_khi_rieng_tin_nhan_moi_da_vuot() -> None:
    """5. Ném lỗi có cấu trúc NGU_CANH_QUA_DAI khi riêng tin nhắn mới vượt ngân sách."""
    cfg = _tao_cau_hinh_gia_lap(num_ctx_nho=1000, gioi_han_token_ra=400, ngu_canh_du_phong_token=100, he_so_an_toan_token=1.0)
    # Ngân sách thô = 1000 - 400 - 100 = 500 token
    chuoi = [Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=1000)]
    loi_nhac = "Lời nhắc hệ thống"
    tin_moi_sieu_dai = "nội dung tin nhắn người dùng siêu dài " * 200  # > 1000 token

    with pytest.raises((NGU_CANH_QUA_DAI, LoiNguCanhQuaDai)) as exc_info:
        dung_ngu_canh(
            [],
            tin_moi_sieu_dai,
            chuoi,
            cau_hinh_he_thong=cfg,
            loi_nhac_he_thong=loi_nhac,
        )

    loi = exc_info.value
    assert isinstance(loi, LoiNguCanhQuaDai)
    assert loi.ma_loi == "NGU_CANH_QUA_DAI"
    assert loi.so_token > loi.ngan_sach


def test_ngan_sach_chuoi_day_du_bang_ngan_sach_bac_nho_local() -> None:
    """6. Ngân sách của chuỗi [0, 1, 2, 3, 4] đúng bằng ngân sách của bậc nho local."""
    cfg = _tao_cau_hinh_gia_lap(num_ctx_chinh=16384, num_ctx_nho=8192)

    chuoi_day_du = [
        Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=16384),
        Tang(so=1, nguon="dam_may", ten="gemini", cua_so_ngu_canh=1000000),
        Tang(so=2, nguon="dam_may", ten="openrouter_auto", cua_so_ngu_canh=128000),
        Tang(so=3, nguon="dam_may", ten="claude", cua_so_ngu_canh=200000),
        Tang(so=4, nguon="dam_may", ten="openai", cua_so_ngu_canh=400000),
    ]

    chuoi_chi_local = [
        Tang(so=0, nguon="local", ten="local", cua_so_ngu_canh=16384),
    ]

    ngan_sach_day_du = tinh_ngan_sach_token(chuoi_day_du, cfg)
    ngan_sach_local = tinh_ngan_sach_token(chuoi_chi_local, cfg)

    # Kỳ vọng: Ngân sách của chuỗi [0, 1, 2, 3, 4] bằng ngân sách của bậc nho local (8192)
    assert ngan_sach_day_du == ngan_sach_local
    cua_so_nho = 8192
    ngan_sach_ky_vong = int(
        (cua_so_nho - cfg.cai_dat_chung.gioi_han_token_ra - cfg.cai_dat_chung.ngu_canh_du_phong_token)
        / cfg.cai_dat_chung.he_so_an_toan_token
    )
    assert ngan_sach_day_du == ngan_sach_ky_vong

    # Kiểm tra thêm hàm uoc_luong_so_luot_giu_duoc
    so_luot = uoc_luong_so_luot_giu_duoc(chuoi_day_du, cfg)
    assert so_luot > 0
