"""Kiểm thử đơn vị cho thuật toán cắt đoạn và quy tắc từ chối siêu dữ liệu.

Tuân thủ:
- Chạy hoàn toàn trên Windows qua `uv run --frozen pytest tests/test_cat_doan.py -v`.
- Không phụ thuộc vào thư viện Docling (dùng văn bản Markdown mẫu).
- Quy chuẩn naming.md, type_safety.md, clean_code.md.
"""

from pathlib import Path

import pytest
import yaml

from app.rag.cat_doan import (
    cat_doan,
    kiem_tra_dong_muc_luc,
    nhan_dien_tieu_de,
)
from app.rag.nap_tai_lieu import (
    kiem_tra_dinh_dang,
    kiem_tra_sieu_du_lieu,
    nap_mot_tai_lieu,
)

VAN_BAN_PHAP_QUY_MAU = """# QUYẾT ĐỊNH BAN HÀNH QUY ĐỊNH
Điều 1. Ban hành kèm theo Quyết định này Quy định về kiểm tra hoạt động điện lực.
Điều 2. Quyết định này có hiệu lực thi hành kể từ ngày 01 tháng 01 năm 2026.
Điều 3. Chánh Văn phòng, Giám đốc các đơn vị chịu trách nhiệm thi hành Quyết định này.

# QUY ĐỊNH VỀ KIỂM TRA HOẠT ĐỘNG ĐIỆN LỰC
CHƯƠNG I: NHỮNG QUY ĐỊNH CHUNG
Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng
Quy định này điều chỉnh các hoạt động kiểm tra cung cấp và sử dụng điện năng.
Điều 2. Giải thích từ ngữ
Trong Quy định này, các từ ngữ dưới đây được hiểu như sau: điện lực là doanh nghiệp được cấp phép.

CHƯƠNG II: TRÌNH TỰ KIỂM TRA
Điều 5. Dịch vụ cấp điện mới hạ áp
Khoản 1. Tiếp nhận hồ sơ khách hàng.
Khoản 2. Khảo sát hiện trường và lập phương án cấp điện trong vòng 03 ngày làm việc.
"""


def test_cat_doan_dung_theo_dieu() -> None:
    """Kiểm tra việc cắt văn bản pháp quy đúng theo từng Điều với đường dẫn mục chính xác."""
    cac_doan = cat_doan(VAN_BAN_PHAP_QUY_MAU, token_doan_toi_da=500)
    assert len(cac_doan) >= 5

    # Tìm đoạn Điều 1 của Quyết định
    dieu_1_qd = next((d for d in cac_doan if d.duong_dan_muc == "Quyết định > Điều 1"), None)
    assert dieu_1_qd is not None
    assert "Ban hành kèm theo Quyết định" in dieu_1_qd.noi_dung

    # Tìm đoạn Điều 2 của Quyết định
    dieu_2_qd = next((d for d in cac_doan if d.duong_dan_muc == "Quyết định > Điều 2"), None)
    assert dieu_2_qd is not None
    assert "có hiệu lực thi hành" in dieu_2_qd.noi_dung


def test_phan_biet_dieu_trung_lap_quyet_dinh_va_chuong() -> None:
    """Kiểm tra Điều có cùng số thứ tự được phân biệt qua duong_dan_muc."""
    cac_doan = cat_doan(VAN_BAN_PHAP_QUY_MAU, token_doan_toi_da=500)

    # Điều 1 ở phần Quyết định
    dieu_1_qd = next((d for d in cac_doan if d.duong_dan_muc == "Quyết định > Điều 1"), None)
    assert dieu_1_qd is not None

    # Điều 1 ở Chương I
    dieu_1_ch1 = next((d for d in cac_doan if d.duong_dan_muc == "Chương I > Điều 1"), None)
    assert dieu_1_ch1 is not None

    # Điều 5 và Khoản 2 ở Chương II
    khoan_2_ch2 = next(
        (d for d in cac_doan if d.duong_dan_muc == "Chương II > Điều 5 > Khoản 2"), None
    )
    assert khoan_2_ch2 is not None
    assert "Khảo sát hiện trường" in khoan_2_ch2.noi_dung


def test_muc_dai_bi_cat_van_giu_tieu_de() -> None:
    """Mục dài hơn token_doan_toi_da thì cắt tiếp theo đoạn văn, MỌI phần giữ nguyên tieu_de_muc."""
    doan_dai = (
        "Cán bộ công nhân viên ngành điện cần tuyệt đối tuân thủ quy tắc an toàn lao động khi "
        "thao tác trên lưới điện cao áp và hạ áp theo quy định hiện hành của Tập đoàn Điện lực. "
    ) * 15

    van_ban = f"Điều 10. Quy trình bảo hộ lao động\n\n{doan_dai}\n\n{doan_dai}"
    # Đặt token_doan_toi_da nhỏ (ví dụ 100) để kích hoạt chia nhỏ
    cac_doan = cat_doan(van_ban, token_doan_toi_da=100)

    assert len(cac_doan) > 1
    for d in cac_doan:
        assert "Điều 10" in d.tieu_de_muc
        assert d.duong_dan_muc == "Điều 10"
        assert d.so_token > 0
        assert d.noi_dung_nhung.startswith(d.tieu_de_muc)


def test_bang_khong_bi_cat_ngang() -> None:
    """Kiểm tra bảng Markdown không bao giờ bị cắt giữa hàng khi phân chia đoạn."""
    bang_md = (
        "| STT | Loại dịch vụ | Thời gian giải quyết |\n"
        "| :--- | :--- | :--- |\n"
        "| 1 | Cấp điện mới hạ áp | 03 ngày |\n"
        "| 2 | Thay đổi công suất | 02 ngày |\n"
        "| 3 | Di dời công tơ | 05 ngày |\n"
        "| 4 | Kiểm tra công tơ | 03 ngày |"
    )
    doan_van = "Dưới đây là bảng tiến độ thực hiện các dịch vụ cấp điện:\n\n"
    van_ban = f"Điều 8. Tiến độ dịch vụ khách hàng\n\n{doan_van}{bang_md}"

    cac_doan = cat_doan(van_ban, token_doan_toi_da=500)
    assert len(cac_doan) == 1

    noi_dung = cac_doan[0].noi_dung
    # Toàn bộ 4 hàng của bảng phải nằm trọn vẹn trong một đoạn
    assert "| 1 | Cấp điện mới hạ áp | 03 ngày |" in noi_dung
    assert "| 4 | Kiểm tra công tơ | 03 ngày |" in noi_dung


def test_bo_qua_dong_muc_luc() -> None:
    """Kiểm tra nhận diện và bỏ qua dòng mục lục kết thúc bằng số trang."""
    dong_ml_1 = "Điều 5. Dịch vụ cấp điện mới hạ áp 05"
    dong_ml_2 = "Điều 12. Xử lý sự cố lưới điện..... 24"
    dong_hop_le = "Điều 5. Dịch vụ cấp điện mới hạ áp"

    assert kiem_tra_dong_muc_luc(dong_ml_1) is True
    assert kiem_tra_dong_muc_luc(dong_ml_2) is True
    assert kiem_tra_dong_muc_luc(dong_hop_le) is False

    # Khi gọi nhan_dien_tieu_de với dòng mục lục thì trả về None
    assert nhan_dien_tieu_de(dong_ml_1) is None
    assert nhan_dien_tieu_de(dong_hop_le) is not None


def test_kiem_tra_dinh_dang_khong_ho_tro() -> None:
    """Kiểm tra từ chối các định dạng ngoài PDF, DOCX, HTML, MD."""
    assert kiem_tra_dinh_dang(Path("van_ban.doc")) is False
    assert kiem_tra_dinh_dang(Path("anh_scan.png")) is False
    assert kiem_tra_dinh_dang(Path("van_ban.pdf")) is True
    assert kiem_tra_dinh_dang(Path("van_ban.docx")) is True
    assert kiem_tra_dinh_dang(Path("huong_dan.md")) is True


def test_thieu_sieu_du_lieu_tu_choi(tmp_path: Path) -> None:
    """Kiểm tra từ chối nạp khi thiếu tệp .meta.yaml hoặc thiếu trường bắt buộc."""
    tep_van_ban = tmp_path / "van_ban_test.md"
    tep_van_ban.write_text("# Nội dung thử nghiệm\nĐiều 1. Thử nghiệm", encoding="utf-8")

    # 1. Chưa có tệp .meta.yaml
    sieu_du_lieu, loi = kiem_tra_sieu_du_lieu(tep_van_ban)
    assert sieu_du_lieu is None
    assert loi == "thiếu siêu dữ liệu"

    # 2. Tạo tệp .meta.yaml nhưng thiếu trường 'tinh_trang'
    tep_meta = tmp_path / "van_ban_test.meta.yaml"
    du_lieu_meta = {
        "ma_tai_lieu": "TEST-01",
        "tieu_de": "Văn bản kiểm thử",
        "loai_van_ban": "huong_dan",
        # Thiếu tinh_trang
        "pham_vi_doc": ["CNTT"],
        "ngay_ban_hanh": "2026-01-01",
        "don_vi_quan_ly": "Phòng CNTT",
    }
    with open(tep_meta, "w", encoding="utf-8") as f:
        yaml.safe_dump(du_lieu_meta, f)

    sieu_du_lieu, loi = kiem_tra_sieu_du_lieu(tep_van_ban)
    assert sieu_du_lieu is None
    assert loi == "thiếu siêu dữ liệu: tinh_trang"


@pytest.mark.asyncio
async def test_nap_mot_tai_lieu_md_thieu_meta_bi_tu_choi(tmp_path: Path) -> None:
    """Kiểm tra hàm nap_mot_tai_lieu trả về TỪ CHỐI khi tệp .md thiếu siêu dữ liệu."""
    tep_van_ban = tmp_path / "tai_lieu_chua_co_meta.md"
    tep_van_ban.write_text("# Tài liệu nội bộ\nNội dung không có meta", encoding="utf-8")

    kq = await nap_mot_tai_lieu(tep_van_ban)
    assert kq.trang_thai == "TỪ CHỐI"
    assert kq.ly_do == "thiếu siêu dữ liệu"
    assert kq.so_doan == 0
