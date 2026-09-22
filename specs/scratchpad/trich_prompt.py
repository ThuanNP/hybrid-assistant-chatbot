"""Sinh bản nháp sổ tay prompt Antigravity từ Phần C (cùng nguồn với tệp hướng dẫn)."""
import pathlib
import re

GOC = pathlib.Path(__file__).parent
SRC = GOC / "src"
PHIEN_BAN = {1: "0.1.0", 2: "0.2.0", 3: "0.3.0", 4: "0.4.0", 5: "1.0.0", 6: "1.1.0", 7: "1.2.0",
             8: "2.0.0", 9: "2.1.0", 10: "2.2.0", 11: "2.3.0"}

noi = "\n".join((SRC / t).read_text(encoding="utf-8") for t in
                ["c1-giai-doan-01-04.md", "c2-giai-doan-05-07.md", "c3-giai-doan-08-11.md"])


def lay_khoi(than, nhan):
    return re.findall(rf"^```{nhan}\n(.*?)^```", than, re.S | re.M)


def lay_muc(than, tieu_de):
    m = re.search(rf"^\*\*{re.escape(tieu_de)}\*\*\n\n(.*?)(?=\n\n(?:\*\*|```|###)|\Z)", than, re.S | re.M)
    return m.group(1).strip() if m else ""


ra = [(GOC / "so_tay_mo_dau.md").read_text(encoding="utf-8").rstrip(), ""]
cac_gd = re.split(r"^(## Giai đoạn \d+: .*)$", noi, flags=re.M)
for k in range(1, len(cac_gd), 2):
    td_gd, than_gd = cac_gd[k], cac_gd[k + 1]
    n_gd = int(re.search(r"Giai đoạn (\d+)", td_gd).group(1))
    dau, *_ = re.split(r"^### PROMPT", than_gd, maxsplit=1, flags=re.M)
    thao_tac = dau.strip().split("\n\n")[0]
    bang = re.search(r"^\| LÀM GÌ.*?(?=\n\n)", dau, re.S | re.M)
    dod = lay_muc(dau, "Điều kiện hoàn thành")
    ra += [td_gd, "", thao_tac, ""]
    if bang:
        ra += [bang.group(0), ""]
    for m in re.finditer(r"^### (PROMPT (\d+)\..*?)\n(.*?)(?=^### PROMPT|\Z)", than_gd, re.S | re.M):
        td, so, than = m.group(1), m.group(2), m.group(3)
        che_do = re.search(r"^\*\*Chế độ:\*\*.*$", than, re.M).group(0)
        muc_tieu = re.search(r"^\*\*Mục tiêu\.\*\*.*?(?=\n\n\*\*|\n\n```)", than, re.S | re.M)
        lam_truoc = re.search(r"^\*\*Làm trước\.\*\*.*?(?=\n\n)", than, re.S | re.M)
        ra += [f"### {td}", "", che_do, ""]
        if muc_tieu:
            ra += [muc_tieu.group(0), ""]
        if lam_truoc:
            ra += [lam_truoc.group(0), ""]
        ra += ["```prompt", lay_khoi(than, "prompt")[0].rstrip("\n"), "```", ""]
        tra_ve = lay_muc(than, "Agent phải trả về")
        ra += ["**Agent phải trả về** (đánh dấu khi đã kiểm)", ""]
        for dong in tra_ve.splitlines():
            if dong.startswith("- "):
                ra.append("- ☐ " + dong[2:])
            elif dong.strip():
                ra[-1] += " " + dong.strip()
        ra += ["", "**Tự đánh giá** (agent tự chạy; người dùng đối chiếu bảng ĐẠT/CHƯA ĐẠT)", "",
               "```danhgia", lay_khoi(than, "danhgia")[0].rstrip("\n"), "```", ""]
        for nhan in ("batbuoc", "meo"):
            for kh in lay_khoi(than, nhan):
                ra += [f"```{nhan}", kh.rstrip("\n"), "```", ""]
    # prompt chốt giai đoạn
    v = PHIEN_BAN[n_gd]
    tieu_chi = []
    for d in dod.splitlines():
        if d.startswith("- "):
            tieu_chi.append(d[2:].strip())
        elif d.strip() and tieu_chi:
            tieu_chi[-1] += " " + d.strip()
    tieu_chi = [t.replace("`", "") for t in tieu_chi]
    tieu_chi = [t for t in tieu_chi if not t.startswith("Phát hành phiên bản")]
    ra += [f"### Chốt Giai đoạn {n_gd}", "", "**Chế độ:** Editor View · **Đọc Plan:** Không", "",
           f"**Mục tiêu.** Rà điều kiện hoàn thành, cập nhật tài liệu và phát hành phiên bản {v}.", "", "```prompt",
           f"Chốt Giai đoạn {n_gd}. Đọc AGENTS.md và .agents/rules/versioning.md trước.",
           "1. Rà từng điều kiện hoàn thành sau, chạy lệnh kiểm chứng tương ứng và ghi kết quả:"]
    ra += [f"   - {t}" for t in tieu_chi]
    ra += ["2. Cập nhật mục \"Không làm ở giai đoạn hiện tại\" trong AGENTS.md: bỏ các việc vừa làm xong.",
           "3. Cập nhật README.md (cách chạy, biến môi trường mới nếu có).",
           f"4. Phát hành {v} theo .agents/rules/versioning.md: nâng số ở backend/pyproject.toml"
           + (" và" if n_gd >= 4 else " (frontend/package.json chưa có, tạo ở PROMPT 14),"),
           ("   frontend/package.json, " if n_gd >= 4 else "   ") + "ghi CHANGELOG.md (Thêm / Thay đổi / Sửa lỗi), commit,",
           f"   gắn thẻ v{v} và giai-doan-{n_gd} trên cùng commit.",
           "5. Tạo Walkthrough tóm tắt giai đoạn: đã làm gì, chưa làm gì, rủi ro còn lại.",
           "",
           "TỰ ĐÁNH GIÁ - trả bảng Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT cho từng điều kiện ở bước 1, cộng:",
           f"- git tag --points-at HEAD -> kỳ vọng: có v{v} và giai-doan-{n_gd}",
           (f"- grep -n \"{v}\" backend/pyproject.toml frontend/package.json CHANGELOG.md -> kỳ vọng: có ở cả ba tệp"
            if n_gd >= 4 else f"- grep -n \"{v}\" backend/pyproject.toml CHANGELOG.md -> kỳ vọng: có ở cả hai tệp"),
           "Còn dòng CHƯA ĐẠT thì KHÔNG gắn thẻ, dừng lại và báo nguyên nhân.",
           "```", ""]

(GOC / "src_so_tay.md").write_text("\n".join(ra) + "\n", encoding="utf-8")
print("Đã ghi src_so_tay.md,", sum(1 for x in ra if x.startswith("### PROMPT")), "prompt")
