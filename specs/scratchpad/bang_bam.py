"""Lưu hoặc so dấu băm các khối được bảo vệ (prompt, danhgia, mã) trước và sau khi viết lại văn xuôi.

Cách dùng: python bang_bam.py luu | so
"""
import hashlib
import json
import pathlib
import re
import sys

GOC = pathlib.Path(__file__).parent
TEP = sorted((GOC / "src").glob("*.md")) + [GOC / "so_tay_mo_dau.md"]
BAO_VE = {"prompt", "danhgia", "bash", "yaml", "text", "json", "nginx", "python", "dockerfile", "bia"}


def bam(p):
    s = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    kq = []
    for m in re.finditer(r"^```(\w*)\n(.*?)^```", s, re.S | re.M):
        if (m.group(1) or "text") in BAO_VE:
            kq.append(hashlib.sha256(m.group(2).encode()).hexdigest()[:16])
    return kq


du_lieu = {p.name: bam(p) for p in TEP if not p.name.startswith("_")}
tep_luu = GOC / "bam_goc.json"
if sys.argv[1] == "luu":
    tep_luu.write_text(json.dumps(du_lieu, indent=1), encoding="utf-8")
    print({k: len(v) for k, v in du_lieu.items()})
else:
    goc = json.loads(tep_luu.read_text(encoding="utf-8"))
    loi = [k for k in goc if goc[k] != du_lieu.get(k)]
    print("KHỚP: mọi khối được bảo vệ giữ nguyên" if not loi else f"LỆCH ở: {loi}")
    sys.exit(1 if loi else 0)
