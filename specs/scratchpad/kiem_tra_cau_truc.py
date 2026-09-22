"""Kiểm tra cấu trúc bản nháp: đủ 11 giai đoạn, PROMPT 1..55 liên tục, mỗi prompt đủ thành phần."""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).parent / "src"
tep = ["c1-giai-doan-01-04.md", "c2-giai-doan-05-07.md", "c3-giai-doan-08-11.md"]
noi = "\n".join((SRC / t).read_text(encoding="utf-8") for t in tep)
loi = []

gd = [int(x) for x in re.findall(r"^## Giai đoạn (\d+): ", noi, re.M)]
if gd != list(range(1, 12)):
    loi.append(f"Giai đoạn không liên tục: {gd}")
for m in re.finditer(r"^## Giai đoạn (\d+): (.*)$", noi, re.M):
    if "—" in m.group(2):
        loi.append(f"Tiêu đề GĐ{m.group(1)} có dấu —")

khoi = re.split(r"^### (PROMPT \d+\..*)$", noi, flags=re.M)
so = []
for i in range(1, len(khoi), 2):
    td, than = khoi[i], khoi[i + 1].split("\n## Giai đoạn")[0]
    n = int(re.match(r"PROMPT (\d+)", td).group(1))
    so.append(n)
    can = {
        "Chế độ": "**Chế độ:**" in than,
        "Mục tiêu": "**Mục tiêu.**" in than,
        "khối prompt": "```prompt" in than,
        "TỰ ĐÁNH GIÁ trong prompt": bool(re.search(r"```prompt.*?TỰ ĐÁNH GIÁ.*?```", than, re.S)),
        "Agent phải trả về": "**Agent phải trả về**" in than,
        "Tự đánh giá": "**Tự đánh giá**" in than and "```danhgia" in than,
    }
    for k, ok in can.items():
        if not ok:
            loi.append(f"PROMPT {n} thiếu {k}")
    if "Đọc Plan:** Có" in than and "Đọc Implementation Plan" not in than:
        loi.append(f"PROMPT {n}: Đọc Plan Có nhưng khối prompt không yêu cầu đọc Plan")
if so != list(range(1, 56)):
    loi.append(f"Số prompt: {so}")

tat_ca = "\n".join(p.read_text(encoding="utf-8") for p in SRC.glob("*.md") if not p.name.startswith("_"))
for cam in ["EVN", "SmartPro", "business-assistant", "smartpro.vn"]:
    if cam.lower() in tat_ca.lower():
        loi.append(f"Còn chuỗi cấm: {cam}")
if tat_ca.count("```") % 2:
    loi.append("Số rào ``` lẻ")
for m in re.finditer(r"(?<![\w./-])v\d+\.\d+(?![\w.])", tat_ca):
    loi.append(f"Nhãn phiên bản kiểu cũ: {m.group(0)}")

print("\n".join(loi) if loi else f"ĐẠT: 11 giai đoạn, {len(so)} prompt, đủ thành phần")
sys.exit(1 if loi else 0)
