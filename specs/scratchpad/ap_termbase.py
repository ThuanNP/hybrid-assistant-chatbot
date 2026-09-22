"""Áp termbase cho VĂN XUÔI (ngoài khối được bảo vệ; batbuoc/meo tính là văn xuôi)."""
import pathlib
import re

GOC = pathlib.Path(__file__).parent
TEP = sorted((GOC / "src").glob("*.md")) + [GOC / "so_tay_mo_dau.md"]
BAO_VE = {"prompt", "danhgia", "bash", "yaml", "text", "json", "nginx", "python", "dockerfile", "bia"}

CUM = [
    # khẩu ngữ
    ("môi trường chạy thật", "môi trường vận hành"),
    ("Đóng gói chạy thật", "Đóng gói cho môi trường vận hành"),
    ("đóng gói chạy thật", "đóng gói cho môi trường vận hành"),
    ("khi chạy thật", "khi vận hành chính thức"),
    ("Chốt chặn cuối cùng", "Tầng dự phòng cuối cùng"),
    ("local làm chốt chặn khi", "local làm tầng dự phòng cuối cùng khi"),
    ("nếu muốn chốt chặn cuối rẻ", "nếu muốn tầng dự phòng cuối cùng rẻ hơn"),
    # backend / frontend
    ("Back-end", "Backend"), ("back-end", "backend"), ("Front-end", "Frontend"), ("front-end", "frontend"),
]


def sua_dong(d):
    for a, b in CUM:
        d = d.replace(a, b)
    d = re.sub(r"(?<!tham chiếu )\bmô hình(?! tham chiếu)", "model", d)
    d = re.sub(r"\bMô hình(?! tham chiếu)", "Model", d)
    d = d.replace("–", "-")
    return d


tong = 0
for p in TEP:
    if p.name.startswith("_"):
        continue
    dong = p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    trong, nhan = False, ""
    for i, d in enumerate(dong):
        m = re.match(r"^```(\w*)\s*$", d.strip())
        if m:
            if not trong:
                trong, nhan = True, (m.group(1) or "text")
            else:
                trong = False
            continue
        if trong and nhan in BAO_VE:
            continue
        moi = sua_dong(d)
        if moi != d:
            dong[i] = moi
            tong += 1
    p.write_text("\n".join(dong), encoding="utf-8")
print("số dòng đã sửa:", tong)
