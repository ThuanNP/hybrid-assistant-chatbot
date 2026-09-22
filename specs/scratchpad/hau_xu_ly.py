"""Đồng bộ các bản nháp: tên dự án, tiền tố /api/v1, cổng Keycloak, phiên bản SemVer ở điều kiện hoàn thành."""
import pathlib
import re

SRC = pathlib.Path(__file__).parent / "src"
TEP = sorted(p for p in SRC.glob("*.md") if not p.name.startswith("_"))

ROUTE = (r"chat|hoi-thoai|chi-phi|models|hang-doi|ngu-canh|toi|dang-nhap|lam-moi-token|dang-xuat|doi-mat-khau|"
         r"chi-so|giam-sat|quan-tri|cau-hinh-dang-nhap|phan-hoi|tai-lieu")
PHIEN_BAN = {1: "0.1.0", 2: "0.2.0", 3: "0.3.0", 4: "0.4.0", 5: "1.0.0", 6: "1.1.0", 7: "1.2.0",
             8: "2.0.0", 9: "2.1.0", 10: "2.2.0", 11: "2.3.0"}


def dong_the(m):
    n = int(m.group(1))
    v = PHIEN_BAN[n]
    them = " (trước đó phát hành `1.0.0-rc.1` cho nhóm dùng thử)" if n == 5 else ""
    if n == 8:
        them = " (MAJOR vì đổi cơ chế xác thực; đường dẫn vẫn `/api/v1/`)"
    return (f"- Phát hành phiên bản `{v}`{them} theo `.agents/rules/versioning.md`: nâng số ở "
            f"backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v{v}` và "
            f"`git tag giai-doan-{n}` trên cùng commit")


dem = {}
for p in TEP:
    s = p.read_text(encoding="utf-8")
    goc = s
    s = s.replace("business-assistant-chatbot", "hybrid-assistant-chatbot")
    # tiền tố API
    s = re.sub(rf"(?<![\w.])/api/(?=({ROUTE})\b)", "/api/v1/", s)
    s = re.sub(rf"(localhost:8000)/(?=({ROUTE})\b)", r"\1/api/v1/", s)
    s = s.replace("Endpoint nghiệp vụ đặt dưới tiền tố /api;", "Endpoint nghiệp vụ đặt dưới tiền tố /api/v1 (theo .agents/rules/versioning.md);")
    s = s.replace('apiGoc = "/api"', 'apiGoc = "/api/v1"')
    # Keycloak dời sang cổng 8180 để không trùng giao diện Angular (8080)
    if p.name.startswith("c3"):
        s = s.replace("127.0.0.1:8080:8080", "127.0.0.1:8180:8080")
        s = s.replace("localhost:8080", "localhost:8180")
        s = s.replace("Cổng 8080 chỉ mở ra localhost", "Cổng 8180 (ánh xạ vào 8080 trong container) chỉ mở ra localhost")
        s = s.replace('"8080/realms"', '"8180/realms"').replace("8080/realms\" ", "8180/realms\" ")
    # điều kiện hoàn thành: phát hành SemVer
    s = re.sub(r"^- Gắn thẻ git: `git tag giai-doan-(\d+)`\s*$", dong_the, s, flags=re.M)
    if s != goc:
        p.write_text(s, encoding="utf-8")
        dem[p.name] = sum(1 for a, b in zip(goc.splitlines(), s.splitlines()) if a != b)
print(dem)
