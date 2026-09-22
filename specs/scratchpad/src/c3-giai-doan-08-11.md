## Giai đoạn 8: Đăng nhập một lần doanh nghiệp và bảng quản trị

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View cho PROMPT 35-37 và Manager Surface cho PROMPT 38-39. Trước khi bắt đầu, chạy docker compose up -d để db, backend và frontend đang chạy, và bảo đảm thẻ git giai-doan-7 đã có. Trên Windows, chạy mọi lệnh tự đánh giá trong Git Bash ở gốc repo, sau khi nạp biến môi trường: `set -a && source .env && set +a && export MSYS_NO_PATHCONV=1` (biến cuối để Git Bash không đổi đường dẫn dạng /api/... thành đường dẫn Windows). Lệnh `docker compose exec` luôn kèm `-T` để không lỗi "the input device is not a TTY". Keycloak cần khoảng 1,5 GB RAM; với laptop 64 GB, đặt giới hạn bộ nhớ cho WSL2 trong %UserProfile%\.wslconfig (ví dụ memory=24GB) để Docker Desktop không chiếm hết RAM ở Giai đoạn 9-10.

**Mục tiêu giai đoạn.** Thay cơ chế tài khoản riêng của ứng dụng bằng đăng nhập một lần theo chuẩn OIDC, để quyền của cán bộ, công nhân viên đi theo nhóm trong hệ thống danh tính doanh nghiệp. Đồng thời có bảng quản trị để theo dõi người dùng, hạn mức, chi phí theo phòng ban, tài liệu và nhật ký kiểm toán.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Keycloak trong docker-compose, realm mẫu "doanh-nghiep" có nhóm theo phòng ban | Redis cho hạn mức và semaphore phân tán → Giai đoạn 9 |
| Backend kiểm JWT qua JWKS, thay ruột lay_nguoi_dung_hien_tai | Cổng AI LiteLLM Proxy với khoá ảo theo phòng ban → Giai đoạn 9 |
| Ánh xạ nhóm sang vai_tro, phong_ban, pham_vi_doc, che_do_dinh_tuyen | Quan sát tập trung OpenTelemetry, Grafana, Langfuse → Giai đoạn 9 |
| Angular đăng nhập bằng Authorization Code + PKCE | Kubernetes, nhiều bản sao backend → Giai đoạn 10 |
| Bảng quản trị Angular và API quan_tri | Liên kết danh tính với hệ thống ngoài (LDAP/AD thật) → ngoài phạm vi tài liệu |
| Nhật ký kiểm toán đầy đủ; tài khoản local chỉ còn là đường dự phòng | Tinh chỉnh model → Giai đoạn 11 |

**Điều kiện hoàn thành**

- Đăng nhập giao diện bằng tài khoản Keycloak; không còn trang nhập mật khẩu của ứng dụng khi DANG_NHAP_LOCAL=false.
- Người thuộc nhóm CHAM_SOC_KHACH_HANG luôn được định tuyến chi_local; tài liệu có pham_vi_doc KY_THUAT không trả về cho người thuộc KINH_DOANH.
- Bảng quản trị chỉ mở cho vai trò quan_tri; mọi thao tác quản trị có dòng trong nhat_ky_kiem_toan.
- Toàn bộ kiểm thử cũ vẫn đạt; bộ eval Giai đoạn 5 và Giai đoạn 6 không giảm tỷ lệ đạt.
- Phát hành phiên bản `2.0.0` (MAJOR vì đổi cơ chế xác thực; đường dẫn vẫn `/api/v1/`) theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v2.0.0` và `git tag giai-doan-8` trên cùng commit

### PROMPT 35. Dựng Keycloak và realm mẫu

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Có một nhà cung cấp danh tính chạy tại chỗ, cấu hình bằng tệp để dựng lại được, trước khi đụng tới mã đăng nhập.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: Keycloak dùng cơ sở dữ liệu riêng chứ không dùng chung schema của ứng dụng, và realm được nạp từ tệp export chứ không tạo bằng tay qua giao diện.

```prompt
Đọc AGENTS.md trước. Thêm Keycloak vào dự án. Đây là thay đổi docker-compose nên phải trình Implementation Plan.

1. docker-compose.yml: thêm dịch vụ keycloak dùng image quay.io/keycloak/keycloak, ghim phiên bản cụ thể.
   - Chạy lệnh start-dev --import-realm trong môi trường dev; ghi chú rõ môi trường prod phải dùng start với TLS.
   - Cơ sở dữ liệu: tạo database riêng tên keycloak trong dịch vụ db (script khởi tạo trong deploy/keycloak/init-db.sql).
     KHÔNG dùng chung database của ứng dụng.
   - Cổng 8180 (ánh xạ vào 8080 trong container) chỉ mở ra localhost trong dev (127.0.0.1:8180:8080).
   - Healthcheck dùng endpoint /health/ready trên cổng quản trị 9000 của Keycloak (bật KC_HEALTH_ENABLED=true).
     Image Keycloak không có curl: viết healthcheck bằng bash với /dev/tcp tới localhost:9000.
   - Biến quản trị KC_BOOTSTRAP_ADMIN_USERNAME, KC_BOOTSTRAP_ADMIN_PASSWORD đọc từ .env, không ghi cứng.
2. deploy/keycloak/realm-doanh-nghiep.json: realm "doanh-nghiep" gồm:
   - Client "tro-ly-web": public client, Standard Flow, PKCE S256 bắt buộc, redirect URI http://localhost:8180/* (giao diện qua nginx),
     http://localhost:4200/* (ng serve) và http://localhost:8000/*, web origins tương ứng.
   - Client "tro-ly-api": bearer-only (hoặc chỉ dùng làm audience), có audience mapper để token của tro-ly-web chứa
     aud = tro-ly-api.
   - Nhóm theo phòng ban: /phong-ban/KINH_DOANH, /phong-ban/KY_THUAT, /phong-ban/AN_TOAN,
     /phong-ban/CHAM_SOC_KHACH_HANG, /phong-ban/CNTT.
   - Nhóm vai trò: /vai-tro/quan_tri, /vai-tro/nguoi_dung, /vai-tro/chi_doc.
   - Mapper "groups" đưa danh sách nhóm (đường dẫn đầy đủ) vào access token.
   - Năm người dùng mẫu, email @vidu.com, mỗi người một phòng ban: nv_kinh_doanh, nv_ky_thuat, nv_an_toan, nv_cskh
     (vai trò nguoi_dung) và qt_cntt (vai trò quan_tri, phòng CNTT). Mật khẩu mẫu chỉ dùng cho dev, ghi trong tệp
     realm dev; ghi chú rõ prod lấy người dùng từ IdP thật hoặc bắt buộc đổi mật khẩu lần đầu.
   - Client "tro-ly-thu" CHỈ CHO DEV: confidential, bật Direct Access Grants, dùng để kịch bản kiểm thử lấy token
     không cần trình duyệt. Ghi chú rõ phải xoá hoặc tắt ở prod.
   - Access token sống 5 phút, refresh token 30 phút.
3. .env.example: thêm OIDC_ISSUER (http://keycloak:8080/realms/doanh-nghiep cho backend trong mạng docker),
   OIDC_ISSUER_CONG_KHAI (http://localhost:8180/realms/doanh-nghiep cho trình duyệt), OIDC_CLIENT_ID=tro-ly-web,
   OIDC_AUDIENCE=tro-ly-api, KC_BOOTSTRAP_ADMIN_USERNAME, KC_BOOTSTRAP_ADMIN_PASSWORD, mỗi biến một dòng chú thích.
4. docs/keycloak.md: cách xuất lại realm sau khi sửa trên giao diện (lệnh kc.sh export), cách thêm người dùng mới
   vào nhóm phòng ban, và lưu ý issuer nội bộ khác issuer công khai.
5. scripts/lay_token_thu.py --nguoi <ten>: lấy access token qua client tro-ly-thu, in token ra stdout; từ chối chạy
   khi MOI_TRUONG=prod. Các prompt sau dùng: TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh).
6. Chưa sửa mã backend hay frontend trong prompt này.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. docker compose up -d keycloak && docker compose ps keycloak -> kỳ vọng: trạng thái healthy trong 90 giây.
2. curl -s http://localhost:8180/realms/doanh-nghiep/.well-known/openid-configuration -> kỳ vọng: JSON có issuer và jwks_uri.
3. TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh), giải mã phần payload bằng Python (base64)
   -> kỳ vọng: có trường groups chứa /phong-ban/KINH_DOANH và aud chứa tro-ly-api.
4. docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -l' -> kỳ vọng: có database keycloak tách khỏi database ứng dụng.
5. grep -n "KC_BOOTSTRAP_ADMIN_PASSWORD=" docker-compose.yml -> kỳ vọng: không có giá trị ghi cứng.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Dịch vụ keycloak trong docker-compose, ghim phiên bản, healthcheck, database riêng
- Tệp realm-doanh-nghiep.json nạp tự động, đủ 2 client, 8 nhóm, 5 người dùng mẫu
- Access token chứa groups và aud = tro-ly-api
- .env.example có đủ 6 biến mới kèm chú thích; docs/keycloak.md
- Client tro-ly-thu chỉ cho dev và scripts/lay_token_thu.py lấy được token không cần trình duyệt

**Tự đánh giá**

```danhgia
docker compose up -d keycloak && docker compose ps keycloak                     # kỳ vọng: healthy
curl -s localhost:8180/realms/doanh-nghiep/.well-known/openid-configuration     # kỳ vọng: có issuer, jwks_uri
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -l'                     # kỳ vọng: có database keycloak
python scripts/lay_token_thu.py --nguoi nv_kinh_doanh | cut -c1-20               # kỳ vọng: có chuỗi token
grep -n "KC_BOOTSTRAP_ADMIN_PASSWORD=" docker-compose.yml                       # kỳ vọng: không có kết quả
```

```batbuoc
Realm phải được quản lý bằng tệp export trong deploy/keycloak/. Cấu hình bấm tay trên giao diện sẽ mất khi dựng lại container, và không ai rà soát được ai đã cấp quyền gì.
```

```meo
Issuer mà backend nhìn thấy (http://keycloak:8080) khác issuer trong token do trình duyệt lấy (http://localhost:8180). Đặt KC_HOSTNAME cố định ngay từ đầu để hai bên dùng chung một issuer, tránh lỗi "invalid issuer" mất nửa ngày gỡ.
```

### PROMPT 36. Backend xác thực OIDC và ánh xạ nhóm

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Thay ruột đúng một hàm lay_nguoi_dung_hien_tai như đã hứa từ Giai đoạn 5; mọi nơi khác trong mã không phải sửa.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: không có tệp nào ngoài app/core/xac_thuc.py và cấu hình ánh xạ bị sửa để đổi cơ chế đăng nhập, và token bị kiểm đủ chữ ký, hạn, issuer, audience.

```prompt
Đọc AGENTS.md trước. Sửa app/core/xac_thuc.py để xác thực bằng OIDC. Giữ nguyên chữ ký
async def lay_nguoi_dung_hien_tai(...) -> NguoiDung.

1. Kiểm access token từ header Authorization dạng Bearer:
   - Tải JWKS từ jwks_uri trong .well-known của OIDC_ISSUER, lưu đệm 10 phút; gặp kid lạ thì tải lại một lần.
   - Kiểm chữ ký RS256, exp, nbf, iss = OIDC_ISSUER, aud chứa OIDC_AUDIENCE. Sai bất kỳ điều nào trả 401 CHUA_XAC_THUC.
   - Dùng thư viện PyJWT[crypto] (hỏi trước khi thêm thư viện theo AGENTS.md).
2. Ánh xạ nhóm sang NguoiDung, khai báo trong config/anh_xa_nhom.yaml, KHÔNG ghi cứng trong mã:
   - /vai-tro/quan_tri -> vai_tro quan_tri; /vai-tro/chi_doc -> chi_doc; mặc định nguoi_dung.
   - /phong-ban/X -> phong_ban X; pham_vi_doc = [X, CHUNG]; quan_tri được thêm toàn bộ phạm vi.
   - che_do_dinh_tuyen theo phòng ban: CHAM_SOC_KHACH_HANG và AN_TOAN -> chi_local; các phòng ban khác lấy CHE_DO_DINH_TUYEN.
   - Người thuộc nhiều phòng ban: pham_vi_doc là hợp các phạm vi; che_do_dinh_tuyen lấy chế độ CHẶT NHẤT
     (chi_local > local_truoc > dam_may_truoc).
   - Token không có nhóm phòng ban nào: từ chối 403 KHONG_CO_QUYEN, ghi nhật ký kiểm toán.
3. Đồng bộ bảng nguoi_dung: lần đầu thấy sub mới thì tạo bản ghi (id theo sub, ten_dang_nhap theo preferred_username,
   mat_khau_bam để rỗng); các lần sau cập nhật phong_ban, vai_tro. Thêm cột nguon_danh_tinh (local|oidc) qua Alembic.
4. Tài khoản local thành đường dự phòng: biến DANG_NHAP_LOCAL (mặc định false ở prod). Khi true, token JWT local của
   Giai đoạn 5 vẫn được chấp nhận; khi false, bốn endpoint local POST /dang-nhap, /lam-moi-token, /dang-xuat,
   /doi-mat-khau đều trả 404.
5. Thêm bảng phong_ban và anh_xa_nhom theo quy ước để bảng quản trị ở PROMPT 38 sửa được ánh xạ mà không cần triển
   khai lại; tệp YAML là giá trị khởi tạo.
6. tests/test_xac_thuc_oidc.py dùng khoá RSA sinh trong kiểm thử và JWKS giả lập, không gọi Keycloak thật:
   token hợp lệ -> đúng phong_ban và pham_vi_doc; sai aud -> 401; hết hạn -> 401; không nhóm phòng ban -> 403;
   người thuộc CHAM_SOC_KHACH_HANG và KINH_DOANH -> che_do_dinh_tuyen = chi_local;
   DANG_NHAP_LOCAL=false -> /dang-nhap, /lam-moi-token, /dang-xuat, /doi-mat-khau trả 404.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_xac_thuc_oidc.py -v -> kỳ vọng: tất cả đạt, không lời gọi mạng thật.
2. cd backend && pytest -q -> kỳ vọng: toàn bộ kiểm thử cũ vẫn đạt.
3. git diff --stat giai-doan-7 -- backend/app -> kỳ vọng: thay đổi trong app/ chỉ nằm ở core/xac_thuc.py, config.py và mô hình dữ liệu.
4. TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh) rồi curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/toi
   -> kỳ vọng: phong_ban KINH_DOANH, pham_vi_doc [KINH_DOANH, CHUNG].
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- lay_nguoi_dung_hien_tai giữ nguyên chữ ký, kiểm đủ chữ ký, exp, iss, aud
- Ánh xạ nhóm nằm trong config/anh_xa_nhom.yaml và bảng anh_xa_nhom, không ghi cứng
- Người nhiều phòng ban nhận chế độ định tuyến chặt nhất
- DANG_NHAP_LOCAL điều khiển đường dự phòng; 6 kiểm thử đạt không cần mạng

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_xac_thuc_oidc.py -v                     # kỳ vọng: 6 kiểm thử đạt
cd backend && pytest -q                                                 # kỳ vọng: không kiểm thử cũ nào hỏng
git diff --stat giai-doan-7 -- backend/app                # kỳ vọng: chỉ core/xac_thuc.py, config.py, mô hình dữ liệu
TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh)
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/toi   # kỳ vọng: đúng phong_ban, pham_vi_doc
```

```batbuoc
Phạm vi đọc tài liệu (pham_vi_doc) lấy từ token đã kiểm chữ ký, KHÔNG BAO GIỜ lấy từ tham số yêu cầu do trình duyệt gửi lên. Nếu không, bất kỳ ai cũng tự cấp cho mình quyền đọc tài liệu của phòng ban khác qua RAG.
```

```meo
Chọn chế độ định tuyến chặt nhất cho người thuộc nhiều phòng ban là cách an toàn mặc định: cùng một câu hỏi có thể mang dữ liệu khách hàng của phòng Chăm sóc khách hàng, và bạn không biết trước người đó đang hỏi với tư cách nào.
```

### PROMPT 37. Angular đăng nhập bằng Authorization Code + PKCE

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Trình duyệt đăng nhập qua Keycloak, giữ token an toàn, tự làm mới, và luồng SSE vẫn mang được token.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: token không bị lưu vào localStorage.

```prompt
Đọc AGENTS.md trước. Chuyển giao diện Angular sang đăng nhập OIDC.

1. Dùng thư viện angular-oauth2-oidc (hỏi trước khi thêm), cấu hình trong frontend/src/app/core/auth/:
   - Luồng Authorization Code + PKCE, client tro-ly-web, scope "openid profile email".
   - Cấu hình issuer đọc từ tệp frontend/src/assets/cau-hinh.json lúc khởi động (APP_INITIALIZER / provideAppInitializer),
     KHÔNG biên dịch cứng địa chỉ Keycloak vào bundle.
   - Lưu token trong bộ nhớ (hoặc sessionStorage nếu cần giữ qua F5); KHÔNG dùng localStorage.
   - Tự làm mới token trước khi hết hạn; làm mới thất bại thì chuyển về trang đăng nhập và giữ nguyên đường dẫn đang mở.
2. Interceptor HTTP gắn Authorization: Bearer cho mọi yêu cầu tới /api; nhận 401 thì thử làm mới một lần rồi mới đẩy ra đăng nhập.
3. sse.service.ts (fetch + ReadableStream) cũng phải gắn token và xử lý 401 như interceptor.
   Token hết hạn GIỮA một luồng đang phát: không cắt luồng; chỉ làm mới cho yêu cầu kế tiếp.
4. Guard: route /quan-tri chỉ mở khi vai trò quan_tri (đọc từ /api/v1/toi, không tự giải mã token để phân quyền).
5. Thanh trên cùng: hiển thị họ tên, phòng ban, nút Đăng xuất (end_session của Keycloak, xoá token trong bộ nhớ).
6. Khi DANG_NHAP_LOCAL=true ở backend (endpoint /api/v1/cau-hinh-dang-nhap trả che_do: local|oidc), giữ trang đăng nhập
   local của Giai đoạn 5 làm đường dự phòng; mặc định dùng OIDC.
7. Kiểm thử: đơn vị cho interceptor (401 -> làm mới -> thử lại một lần), guard quan_tri; Playwright đăng nhập bằng
   người dùng mẫu của realm, gửi một câu hỏi, thấy câu trả lời phát dần.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd frontend && npx ng test --watch=false -> kỳ vọng: tất cả đạt.
2. npx playwright test e2e/dang-nhap-oidc.spec.ts -> kỳ vọng: đăng nhập bằng nv_kinh_doanh qua trang Keycloak, gửi câu hỏi, nhận chữ phát dần.
3. grep -rn "localStorage" frontend/src/app/core/auth -> kỳ vọng: không có kết quả.
4. grep -rn "8180/realms" frontend/src/app -> kỳ vọng: không có địa chỉ Keycloak ghi cứng.
5. Kịch bản Playwright thứ hai đăng nhập bằng nv_kinh_doanh, mở /quan-tri -> kỳ vọng: bị chặn, về trang chính.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Đăng nhập Authorization Code + PKCE; địa chỉ issuer đọc lúc chạy từ cau-hinh.json
- Token không nằm trong localStorage; tự làm mới trước khi hết hạn
- Luồng SSE mang token, không bị cắt khi token hết hạn giữa chừng
- Guard /quan-tri dựa trên /api/v1/toi; kiểm thử đơn vị và Playwright đạt

**Tự đánh giá**

```danhgia
cd frontend && npx ng test --watch=false                  # kỳ vọng: tất cả đạt
npx playwright test e2e/dang-nhap-oidc.spec.ts            # kỳ vọng: đạt
grep -rn "localStorage" src/app/core/auth                 # kỳ vọng: không có kết quả
grep -rn "8180/realms" src/app                            # kỳ vọng: không có kết quả
```

```batbuoc
Phân quyền thật luôn nằm ở backend. Guard trên Angular chỉ để ẩn màn hình; mọi API quan_tri vẫn phải tự kiểm vai trò, vì người dùng sửa được mã JavaScript chạy trên máy họ.
```

### PROMPT 38. Bảng quản trị và API quan_tri

**Chế độ:** Manager Surface · **Đọc Plan:** Có

**Mục tiêu.** Người quản trị thấy được ai đang dùng, tốn bao nhiêu theo phòng ban, tài liệu nào đang hiệu lực, mà không phải chạy câu SQL.

**Làm trước.** Đọc Implementation Plan. Trong Manager Surface, tách thành hai việc song song: một agent làm API backend, một agent làm màn hình Angular, dùng chung hợp đồng API viết trước trong docs/api-quan-tri.md.

```prompt
Đọc AGENTS.md trước. Làm bảng quản trị. Bước đầu tiên: viết docs/api-quan-tri.md (hợp đồng API) rồi mới viết mã.

Đã có từ trước, KHÔNG tạo lại: trang Angular /quan-tri/bo-chay (PROMPT 21) và API /quan-tri/tai-lieu
(POST/GET/PATCH/DELETE, Giai đoạn 6) cùng màn hình tương ứng. Việc của prompt này là GỘP chúng vào một khung quản trị
chung (layout có sidebar mục "Quản trị") và bổ sung các phần còn thiếu dưới đây.

Backend - app/quan_tri/api.py, mọi route dưới /quan-tri, dependency bắt buộc vai_tro = quan_tri (403 nếu không):
1. GET /quan-tri/tong-quan?tu=&den= : số lượt, số người dùng hoạt động, chi phí USD, tỷ lệ phục vụ tại local,
   tỷ lệ rơi tầng, tỷ lệ bị cắt ngữ cảnh, tỷ lệ từ chối vì không đủ căn cứ - chia theo phòng ban.
2. GET /quan-tri/nguoi-dung (phân trang, lọc theo phòng ban) và PATCH /quan-tri/nguoi-dung/{id}:
   chỉ được sửa bac (free|pro), dang_hoat_dong, hạn mức riêng. KHÔNG sửa vai trò/phòng ban ở đây vì đó là việc của Keycloak.
3. GET/PUT /quan-tri/phong-ban/{ma}: hạn mức token ngày, ngân sách USD ngày, che_do_dinh_tuyen, mức ưu tiên.
   Đổi che_do_dinh_tuyen từ chi_local sang chế độ khác bắt buộc có trường ly_do, ghi vào nhật ký kiểm toán.
4. Mở rộng GET /quan-tri/tai-lieu đã có (không đổi hợp đồng cũ, chỉ thêm trường): cờ sap_het_hieu_luc cho tài liệu hết
   hiệu lực trong 30 ngày và cờ thieu_van_ban_thay_the cho tài liệu het_hieu_luc chưa có van_ban_thay_the. Mọi thao tác
   POST/PATCH/DELETE tài liệu phải ghi nhật ký kiểm toán (bổ sung nếu Giai đoạn 6 chưa ghi).
5. GET /quan-tri/nhat-ky-kiem-toan: lọc theo người thực hiện, loại hành động, khoảng thời gian; chỉ đọc, không có API xoá.
6. Mọi con số tổng hợp tính bằng SQL trên luot_goi và luot; KHÔNG trả nội dung tin nhắn ra bảng quản trị.

Frontend - features/quan-tri/, lazy-load, dùng token DESIGN.md:
7. Trang Tổng quan: hàng 4 thẻ KPI theo mục 6.3 DESIGN.md, bảng theo phòng ban, biểu đồ chi phí theo ngày.
8. Trang mới: Người dùng, Phòng ban (form có ô lý do bắt buộc khi nới chế độ định tuyến), Nhật ký kiểm toán. Hai trang
   đã có (/quan-tri/bo-chay, /quan-tri/tai-lieu) chuyển vào khung chung; trang Tài liệu thêm nhãn màu cho hai cờ mới.
9. Mọi số tiền hiển thị kèm đơn vị; thời gian theo dd/mm/yyyy - HH:mm.

Kiểm thử: tests/test_quan_tri.py (nguoi_dung gọi -> 403; đổi chi_local không có lý do -> 422; mọi PUT sinh một dòng
kiểm toán; phản hồi tổng quan không chứa trường noi_dung); Angular: kiểm thử đơn vị cho form phòng ban.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_quan_tri.py -v -> kỳ vọng: tất cả đạt.
2. Lấy TOKEN_NGUOI_DUNG (nv_kinh_doanh) và TOKEN_QUAN_TRI (qt_cntt) bằng scripts/lay_token_thu.py; curl với token
   nguoi_dung tới /api/v1/quan-tri/tong-quan -> kỳ vọng: 403 KHONG_CO_QUYEN.
3. curl với token quan_tri tới /api/v1/quan-tri/tong-quan | grep -c noi_dung -> kỳ vọng: 0.
4. cd frontend && npx ng test --watch=false && npx ng build -> kỳ vọng: đạt, route quan-tri là chunk tách riêng.
5. PUT đổi phòng ban CNTT sang dam_may_truoc có lý do, rồi GET nhật ký kiểm toán -> kỳ vọng: thấy dòng mới kèm lý do.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- docs/api-quan-tri.md viết trước mã, backend và frontend khớp hợp đồng
- Mọi route /quan-tri kiểm vai trò ở backend; không trả nội dung tin nhắn
- Nới chế độ định tuyến khỏi chi_local bắt buộc có lý do và được kiểm toán
- Một khung quản trị lazy-load gộp trang có sẵn (bộ chạy, tài liệu) với ba trang mới, theo token DESIGN.md

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_quan_tri.py -v                                           # kỳ vọng: tất cả đạt
TOKEN_NGUOI_DUNG=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh); TOKEN_QUAN_TRI=$(python scripts/lay_token_thu.py --nguoi qt_cntt)
curl -s -H "Authorization: Bearer $TOKEN_NGUOI_DUNG" localhost:8000/api/v1/quan-tri/tong-quan   # kỳ vọng: 403
curl -s -H "Authorization: Bearer $TOKEN_QUAN_TRI" localhost:8000/api/v1/quan-tri/tong-quan | grep -c noi_dung   # kỳ vọng: 0
cd frontend && npx ng test --watch=false && npx ng build                    # kỳ vọng: đạt, quan-tri là chunk riêng
```

```meo
Viết hợp đồng API trước rồi mới chia hai agent song song trong Manager Surface. Không có hợp đồng, hai agent sẽ tự đặt tên trường khác nhau và bạn mất thời gian ghép lại nhiều hơn thời gian tiết kiệm được.
```

### PROMPT 39. Nhật ký kiểm toán và rà soát tài khoản local

**Chế độ:** Editor View · **Đọc Plan:** Không

**Mục tiêu.** Nhật ký đủ để tái dựng một quyết định theo yêu cầu pháp lý (Module 1), và không còn cửa hậu đăng nhập nào ngoài Keycloak ở môi trường vận hành.

```prompt
Đọc AGENTS.md trước. Hoàn thiện nhật ký kiểm toán và đóng đường đăng nhập local ở môi trường chạy thật.

1. Bảng nhat_ky_kiem_toan (bổ sung nếu Giai đoạn 5 chưa đủ): thoi_diem, nguoi_thuc_hien_id, nguon_danh_tinh,
   hanh_dong, doi_tuong, gia_tri_cu (jsonb), gia_tri_moi (jsonb), ly_do, ma_yeu_cau, dia_chi_ip.
   Chỉ INSERT: tạo vai trò CSDL tro_ly_ung_dung (không phải superuser, không sở hữu bảng) và chuyển DATABASE_URL của
   backend sang vai trò này; vai trò chủ sở hữu (POSTGRES_USER) chỉ dùng để chạy Alembic qua DATABASE_URL_MIGRATION.
   Migration cấp cho tro_ly_ung_dung quyền SELECT/INSERT/UPDATE/DELETE trên các bảng nghiệp vụ, nhưng CHỈ SELECT và
   INSERT trên nhat_ky_kiem_toan. Lưu ý: superuser bỏ qua mọi quyền, nên kiểm thử phải chạy bằng tro_ly_ung_dung.
2. Ghi kiểm toán cho: đăng nhập thành công/thất bại (cả OIDC lẫn local), bị từ chối 403, mọi thao tác /quan-tri,
   nạp/xoá tài liệu RAG, đổi chế độ định tuyến, vượt hạn mức.
3. Mỗi lượt trả lời trong bảng luot phải tái dựng được: ai hỏi (nguoi_id), hỏi gì (đã che), tài liệu nào
   (nguon_tham_chieu, diem_cao_nhat, tu_choi), mô hình nào (nguon, tang, model_da_dung), công cụ đã gọi (nếu có),
   phiên bản lời nhắc (phien_ban_loi_nhac). Viết
   scripts/tai_dung_quyet_dinh.py --ma-yeu-cau <ma> in đủ các trường trên cho một lượt.
4. Môi trường prod: nếu DANG_NHAP_LOCAL=true thì ghi cảnh báo lúc khởi động và thêm dòng CHƯA ĐẠT trong
   scripts/kiem_tra_truoc_khi_mo.py. Nếu còn tài khoản local có vai trò quan_tri đang hoạt động, hoặc client
   tro-ly-thu còn bật trong realm, thì cũng CHƯA ĐẠT.
5. Cập nhật AGENTS.md: xoá "Đăng nhập một lần doanh nghiệp" khỏi mục "Không làm"; thêm quy tắc "phân quyền chỉ
   đọc từ token đã kiểm, không từ tham số yêu cầu". Cập nhật README mục đăng nhập và CHANGELOG.
6. tests/test_kiem_toan.py: ứng dụng không xoá được dòng kiểm toán (lỗi quyền); đăng nhập thất bại sinh một dòng;
   tai_dung_quyet_dinh.py in đủ 5 nhóm thông tin; prod + DANG_NHAP_LOCAL=true làm kiem_tra_truoc_khi_mo thoát mã 1.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_kiem_toan.py -v -> kỳ vọng: tất cả đạt.
2. docker compose exec -T db sh -c 'psql -U tro_ly_ung_dung -d "$POSTGRES_DB" -c "DELETE FROM nhat_ky_kiem_toan"'
   -> kỳ vọng: permission denied.
3. python scripts/tai_dung_quyet_dinh.py --ma-yeu-cau <ma của một lượt vừa hỏi> -> kỳ vọng: đủ người hỏi, câu hỏi đã che,
   tài liệu, mô hình, phiên bản lời nhắc.
4. MOI_TRUONG=prod DANG_NHAP_LOCAL=true python scripts/kiem_tra_truoc_khi_mo.py; echo $? -> kỳ vọng: 1.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Bảng kiểm toán chỉ cho INSERT ở mức quyền database
- Đủ các sự kiện kiểm toán đã liệt kê, kèm ma_yeu_cau
- scripts/tai_dung_quyet_dinh.py tái dựng được một lượt trả lời
- kiem_tra_truoc_khi_mo.py chặn prod khi còn đăng nhập local; AGENTS.md, README, CHANGELOG đã cập nhật

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_kiem_toan.py -v                                                  # kỳ vọng: tất cả đạt
docker compose exec -T db sh -c 'psql -U tro_ly_ung_dung -d "$POSTGRES_DB" -c "DELETE FROM nhat_ky_kiem_toan"'   # kỳ vọng: permission denied
python scripts/tai_dung_quyet_dinh.py --ma-yeu-cau <ma>                             # kỳ vọng: đủ 5 nhóm thông tin
MOI_TRUONG=prod DANG_NHAP_LOCAL=true python scripts/kiem_tra_truoc_khi_mo.py; echo $?   # kỳ vọng: 1
```

```batbuoc
Nhật ký kiểm toán mà chính ứng dụng xoá được thì không có giá trị chứng cứ. Chặn ở mức quyền database, không chỉ ở mức "mã không có hàm xoá".
```

## Giai đoạn 9: Cổng AI, bộ nhớ đệm và quan sát

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View. Chạy docker compose up -d và bảo đảm thẻ git giai-doan-8 đã có. Giai đoạn này thêm nhiều dịch vụ vào docker-compose nên mỗi prompt đều phải đọc Implementation Plan. Trên Windows, chạy mọi lệnh tự đánh giá trong Git Bash ở gốc repo, sau khi nạp biến môi trường: `set -a && source .env && set +a && export MSYS_NO_PATHCONV=1` (biến cuối để Git Bash không đổi đường dẫn dạng /api/... thành đường dẫn Windows). Lệnh `docker compose exec` luôn kèm `-T` để không lỗi "the input device is not a TTY". Các dịch vụ quan sát nằm trong compose profile riêng để laptop bật tắt từng nhóm: giam_sat (OTel, Prometheus, Grafana, Alertmanager, Tempo), nhat_ky (Loki, Alloy), quan_sat (Langfuse đầy đủ), bi_mat (OpenBao). Demo tối thiểu trên laptop chỉ cần dịch vụ mặc định (có Redis, LiteLLM) cộng profile giam_sat; ba profile còn lại bật khi làm đúng prompt cần chúng. Bật cả bốn nhóm tốn thêm khoảng 8-10 GB RAM.

Bảng cổng trên laptop sau Giai đoạn 9 (mọi cổng chỉ nghe 127.0.0.1; "nội bộ" là chỉ trong mạng docker):

| Dịch vụ | Cổng trên máy | Profile |
| --- | --- | --- |
| frontend (nginx) | 8080 | mặc định |
| backend | 8000 (8000-8001 khi chạy 2 bản sao) | mặc định |
| db (PostgreSQL) | 5432, chỉ dev qua docker-compose.override.yml | mặc định |
| keycloak | 8180 (container 8080; cổng quản trị 9000 nội bộ) | mặc định |
| redis | 6379, chỉ dev qua docker-compose.override.yml | mặc định |
| litellm | nội bộ 4000 (dev có thể mở 4000 để gỡ lỗi) | mặc định |
| Ollama / LM Studio trên Windows | 11434 / 1234 | ngoài docker |
| otel-collector | nội bộ 4317, 4318 | giam_sat |
| prometheus | 9090 | giam_sat |
| alertmanager | 9093 | giam_sat |
| grafana | 3000 | giam_sat |
| loki | 3100 | nhat_ky |
| tempo | nội bộ 3200 | giam_sat |
| alloy (gom log) | nội bộ 12345 | nhat_ky |
| langfuse-web | 3001 (container 3000, tránh trùng Grafana) | quan_sat |
| langfuse-worker, clickhouse, minio, redis-langfuse | nội bộ | quan_sat |
| openbao | 8200 | bi_mat |
| vllm (Giai đoạn 10, chạy thử) | 8002 (container 8000, tránh trùng backend) | tệp compose riêng |

**Mục tiêu giai đoạn.** Chuẩn bị cho nhiều bản sao backend và nhiều ứng dụng dùng chung model: trạng thái chia sẻ chuyển sang Redis, mọi lời gọi model đi qua một cổng AI có khoá ảo theo phòng ban, và có đủ quan sát để trả lời cả hai câu "hệ thống có chạy không" lẫn "chất lượng có đang xấu đi không".

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Redis cho hạn mức, semaphore hàng đợi và bộ nhớ đệm câu trả lời | Kubernetes, tự giãn theo tải → Giai đoạn 10 |
| LiteLLM Proxy làm cổng AI, khoá ảo và hạn mức theo phòng ban | vLLM thay Ollama ở môi trường thật → Giai đoạn 10 |
| Router thành client của cổng, alias tro-ly-chat và tro-ly-nhung | Nhiều GPU, cân bằng tải máy chủ model → Giai đoạn 10 |
| OpenTelemetry, Prometheus, Grafana, Loki | Tinh chỉnh model → Giai đoạn 11 |
| Langfuse theo dõi chất lượng; OpenBao giữ bí mật | Cảnh báo qua kênh nhắn tin nội bộ → ngoài phạm vi tài liệu |

**Điều kiện hoàn thành**

- Chạy hai bản sao backend cùng lúc: hạn mức "một yêu cầu đang chạy mỗi người" vẫn đúng.
- Backend không còn giữ khoá API nhà cung cấp; chỉ giữ khoá ảo của cổng.
- Yêu cầu NHAY_CAM bị chặn ra đám mây ở CẢ tầng ứng dụng lẫn tầng cổng.
- Grafana có bảng điều khiển với ba chỉ số sức khoẻ local, tỷ lệ rơi tầng và chi phí theo phòng ban; tìm được một ma_yeu_cau xuyên qua Loki, vết OpenTelemetry và Langfuse.
- Phát hành phiên bản `2.1.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v2.1.0` và `git tag giai-doan-9` trên cùng commit

### PROMPT 40. Redis cho trạng thái phân tán và bộ nhớ đệm

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Hạn mức và hàng đợi đang nằm trong bộ nhớ một tiến trình. Hai bản sao là hai bộ đếm riêng, và người dùng lách được hạn mức. Chuyển chúng sang Redis trước khi nghĩ tới mở rộng.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: có đường suy giảm khi Redis mất, và bộ nhớ đệm không bao giờ trả câu trả lời của người này cho người khác có phạm vi đọc khác.

```prompt
Đọc AGENTS.md trước. Thêm Redis. Đây là thêm dịch vụ và thêm thư viện nên phải trình Implementation Plan.

1. docker-compose: dịch vụ redis (ghim phiên bản), không mở cổng trong docker-compose.yml; chỉ dev mới mở
   127.0.0.1:6379 (và 127.0.0.1:5432 của db) qua docker-compose.override.yml để kiểm thử chạy từ máy host;
   bật mật khẩu (REDIS_URL trong .env),
   appendonly tắt (dữ liệu chỉ là trạng thái tạm), giới hạn maxmemory và chính sách allkeys-lru.
2. app/core/han_muc.py: chuyển cửa sổ trượt sang Redis (sorted set theo khoá han_muc:{loai}:{id}, thao tác nguyên tử bằng
   script Lua). Giữ nguyên thứ tự 4 lớp: IP -> giờ -> token/chi phí ngày -> một yêu cầu đang chạy mỗi người.
   Lớp "một yêu cầu đang chạy": khoá SET NX có TTL bằng TIMEOUT_GIAY + 30 giây, xoá khi xong hoặc khi client đóng.
3. app/hang_doi/dieu_phoi.py: semaphore phân tán cho tầng local (đếm số khe trong Redis, TTL mỗi khe để khe không bị
   kẹt khi một bản sao chết). Vị trí hàng đợi và thời gian chờ trung vị tính trên dữ liệu chung.
4. Bộ nhớ đệm câu trả lời, app/core/bo_nho_dem.py:
   - Chỉ cho câu hỏi KHÔNG có dữ liệu nhạy cảm, không có lịch sử hội thoại trước đó (lượt đầu), nhiệt độ 0 hoặc được đánh dấu cho phép.
   - Không đệm lượt có gọi công cụ (sự kiện cong_cu) vì kết quả tra cứu nghiệp vụ thay đổi theo thời điểm.
   - Khoá = băm(câu hỏi đã chuẩn hoá + che_do (tra_cuu|tro_chuyen) + phien_ban_loi_nhac + danh sách pham_vi_doc đã sắp
     xếp + phiên bản kho tri thức).
   - TTL mặc định 1 giờ (BO_NHO_DEM_GIAY); xoá toàn bộ khi nạp lại tài liệu RAG.
   - Lượt trả từ bộ nhớ đệm vẫn ghi luot và luot_goi với nguon = bo_nho_dem, chi phí 0.
5. Suy giảm khi Redis mất: hạn mức chuyển về bộ đếm trong tiến trình (ghi cảnh báo), bộ nhớ đệm tắt, /ready vẫn 200
   nhưng trả chi tiết redis: suy_giam. KHÔNG làm sập ứng dụng.
6. docker-compose cho phép chạy 2 bản sao backend (docker compose up --scale backend=2) sau nginx của frontend:
   đổi ánh xạ cổng backend thành "127.0.0.1:8000-8001:8000" (một cổng cố định sẽ làm lệnh scale lỗi trùng cổng),
   và nginx dùng resolver 127.0.0.11 valid=10s để thấy cả hai bản sao.
7. tests/test_redis_phan_tan.py dùng Redis thật trong compose (đánh dấu pytest -m redis): hai tiến trình cùng người
   dùng gửi đồng thời -> một bị 429; khe local không vượt SO_LUONG_DONG_THOI khi 2 bản sao; hai người khác pham_vi_doc
   hỏi cùng câu -> không dùng chung bộ nhớ đệm; tắt Redis -> ứng dụng vẫn trả lời.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest -m redis tests/test_redis_phan_tan.py -v -> kỳ vọng: 4 kiểm thử đạt.
2. docker compose up -d --scale backend=2; TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh); gửi hai
   yêu cầu cùng lúc qua nginx: for i in 1 2; do curl -s -o /dev/null -w "%{http_code}\n" -X POST
   localhost:8180/api/v1/chat -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
   -d '{"noi_dung":"Giải thích dài về giá điện bậc thang"}' & done; wait -> kỳ vọng: một 200 và một 429.
3. Hỏi cùng một câu hai lần -> kỳ vọng: lần hai có nguon = bo_nho_dem trong sự kiện xong, độ trễ dưới 100 ms.
4. docker compose stop redis && curl -s localhost:8000/ready -> kỳ vọng: 200, redis: suy_giam; gửi câu hỏi vẫn có trả lời.
5. cd backend && pytest -q -> kỳ vọng: toàn bộ kiểm thử cũ vẫn đạt.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Hạn mức 4 lớp và semaphore local chạy trên Redis, thao tác nguyên tử
- Bộ nhớ đệm có khoá gồm pham_vi_doc và phiên bản lời nhắc, không đệm dữ liệu nhạy cảm
- Mất Redis thì suy giảm, không sập
- Chạy được 2 bản sao backend; 4 kiểm thử phân tán đạt

**Tự đánh giá**

```danhgia
cd backend && pytest -m redis tests/test_redis_phan_tan.py -v          # kỳ vọng: 4 kiểm thử đạt
docker compose up -d --scale backend=2                   # kỳ vọng: 2 bản sao healthy
docker compose stop redis && curl -s localhost:8000/ready    # kỳ vọng: 200, redis: suy_giam
cd backend && pytest -q                                                # kỳ vọng: không kiểm thử cũ nào hỏng
```

```batbuoc
Khoá bộ nhớ đệm PHẢI chứa pham_vi_doc. Thiếu nó, câu trả lời dựa trên tài liệu của phòng Kỹ thuật sẽ được trả nguyên văn cho người phòng Kinh doanh hỏi cùng câu, tức là rò rỉ qua bộ nhớ đệm mà không đi qua bước lọc truy hồi nào.
```

```meo
Khoá "một yêu cầu đang chạy" luôn cần TTL. Không có TTL, một bản sao chết giữa chừng sẽ khoá người dùng đó vĩnh viễn cho tới khi có người xoá tay trong Redis.
```

### PROMPT 41. Cổng AI LiteLLM Proxy với khoá ảo theo phòng ban

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Theo Module 2: đo lường, kiểm soát, thu hồi quyền, thay model mà không sửa ứng dụng. Router chuyển thành client của cổng, API và chính sách định tuyến không đổi.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: chính sách chi_local vẫn được áp ở tầng ứng dụng TRƯỚC khi gọi cổng, và cổng cũng có lớp chặn riêng cho khoá của phòng ban chi_local.

```prompt
Đọc AGENTS.md trước. Đưa LiteLLM Proxy vào làm cổng AI. Trình Implementation Plan trước.

1. docker-compose: dịch vụ litellm (image ghim phiên bản), database riêng litellm trong db, cổng 4000 không mở ra ngoài,
   có extra_hosts "host.docker.internal:host-gateway" để gọi Ollama/LM Studio chạy trên máy Windows.
   Khoá API của bốn nhà cung cấp CHUYỂN từ backend sang litellm; backend chỉ còn LITELLM_URL và LITELLM_KEY.
2. deploy/litellm/config.yaml:
   - Alias tro-ly-chat-local: ollama_chat hoặc openai-compatible trỏ DIA_CHI_BO_CHAY, model theo HO_SO_GPU bậc 1;
     tro-ly-chat-local-nho: bậc 2.
   - Alias tro-ly-chat-dam-may-1..4: Gemini, OpenRouter/auto, Claude, OpenAI như config/models.yaml.
   - Alias tro-ly-nhung: model nhúng bge-m3 qua Ollama. CHỈ MỘT model nhúng, không có dự phòng sang model nhúng khác.
   - Giữ nguyên thông tin ho_tro_cong_cu theo tầng trong models.yaml: router vẫn đọc từ models.yaml, cổng chỉ là đường đi.
   - router_settings: num_retries, timeout theo tầng. KHÔNG khai fallbacks tự động của LiteLLM giữa local và đám mây:
     thứ tự chuỗi vẫn do app/llm/chinh_sach.py quyết định để giữ kiểm thử "chi_local không chạm đám mây".
3. Khoá ảo theo phòng ban (scripts/tao_khoa_ao.py gọi API quản trị của LiteLLM):
   - Mỗi phòng ban một khoá, metadata phong_ban, hạn mức token/ngày và ngân sách USD/ngày theo bảng phong_ban.
   - Phòng ban chi_local (CHAM_SOC_KHACH_HANG, AN_TOAN): khoá chỉ được phép gọi alias tro-ly-chat-local*, tro-ly-nhung.
     Đây là lớp chặn thứ hai, độc lập với tầng ứng dụng.
   - Khi config/chinh_sach_du_lieu.yaml có rag_duoc_ra_dam_may = false: lượt có ngữ cảnh RAG dùng một khoá ảo thứ hai
     của phòng ban, cũng chỉ được gọi alias local. Ứng dụng chọn khoá theo việc lượt đó có ngữ cảnh RAG hay không.
   - Lưu khoá ảo đã mã hoá trong bảng phong_ban; không in ra nhật ký. Chỉ ở dev, tham số --in-khoa <PHONG_BAN> in
     khoá một lần ra stdout để kiểm thử; từ chối khi MOI_TRUONG=prod.
4. app/llm/router.py, bo_chay_local.py, nha_cung_cap_dam_may.py: mọi lời gọi đi tới LITELLM_URL với alias và khoá ảo
   của phòng ban người dùng. Giữ nguyên goi_mo_hinh, goi_mo_hinh_theo_dong, goi_nhung và KetQuaGoi.
   Đọc model thực dùng từ phản hồi (quan trọng với openrouter/auto) như trước.
5. Cờ DUNG_CONG_AI (mặc định true): false thì quay về gọi trực tiếp như Giai đoạn 8 để có đường lùi.
6. Hàng đợi và semaphore local vẫn ở ứng dụng (Redis); ghi chú rõ lý do: cổng không biết vị trí hàng đợi để báo người dùng.
7. Bảng quản trị: thêm cột chi phí theo khoá ảo lấy từ API chi tiêu của LiteLLM, đối chiếu với luot_goi.
8. tests/test_cong_ai.py dùng LiteLLM giả lập bằng httpx MockTransport: đúng alias theo tầng; khoá ảo đúng phòng ban;
   yêu cầu NHAY_CAM không bao giờ gửi alias dam-may; khi cổng trả 403 vì khoá chi_local gọi alias đám mây thì ghi
   CẢNH BÁO "lớp chặn thứ hai kích hoạt" (nghĩa là lớp một đã lọt).

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_cong_ai.py -v -> kỳ vọng: tất cả đạt.
2. docker compose exec -T backend env | grep -E "GOOGLE_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY|OPENROUTER_API_KEY" -> kỳ vọng: không có.
3. KHOA_CSKH=$(python scripts/tao_khoa_ao.py --in-khoa CHAM_SOC_KHACH_HANG); gọi cổng từ bên trong mạng docker:
   docker compose exec -T -e KHOA="$KHOA_CSKH" backend python -c "import os,httpx;print(httpx.post('http://litellm:4000/v1/chat/completions',
   headers={'Authorization':'Bearer '+os.environ['KHOA']},json={'model':'tro-ly-chat-dam-may-1','messages':[{'role':'user','content':'xin chào'}]}).status_code)"
   -> kỳ vọng: 401 hoặc 403 (bị từ chối).
4. cd backend && python -m app.eval.runner --tang all --lan 1 (chạy cả eval/bo_cau_hoi.yaml, bo_cau_hoi_rag.yaml, bo_cau_hoi_cong_cu.yaml)
   -> kỳ vọng: tỷ lệ đạt không thấp hơn lần chạy trước khi thêm cổng.
5. DUNG_CONG_AI=false, khởi động lại, hỏi một câu -> kỳ vọng: vẫn trả lời.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Khoá nhà cung cấp chỉ còn ở cổng; backend dùng khoá ảo theo phòng ban
- Chính sách chi_local được áp hai lớp: ứng dụng và khoá ảo của cổng
- Chữ ký goi_mo_hinh, goi_nhung không đổi; có cờ DUNG_CONG_AI để lùi
- Một model nhúng duy nhất sau alias tro-ly-nhung; eval không giảm

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_cong_ai.py -v                                          # kỳ vọng: tất cả đạt
docker compose exec -T backend env | grep -E "GOOGLE_API_KEY|ANTHROPIC_API_KEY"   # kỳ vọng: không có
cd backend && python -m app.eval.runner --tang all --lan 1                             # kỳ vọng: không giảm so với trước
```

```batbuoc
Không dùng tính năng fallbacks tự động của LiteLLM để nối local với đám mây. Nếu cổng tự rơi từ local sang Gemini khi Ollama chậm, một câu hỏi chứa mã khách hàng sẽ ra khỏi hạ tầng doanh nghiệp mà ứng dụng không hề biết. Thứ tự chuỗi phải do chinh_sach.py quyết định.
```

```meo
Theo tài liệu gốc: cổng AI riêng chỉ đáng dựng khi có từ hai ứng dụng trở lên dùng chung hạn mức, hoặc cần khoá ảo theo nhóm. Giai đoạn này đáp ứng điều kiện thứ hai. Nếu doanh nghiệp chỉ có một ứng dụng và không cần chia chi phí theo phòng ban, có thể giữ DUNG_CONG_AI=false.
```

### PROMPT 42. OpenTelemetry, Prometheus, Grafana và Loki

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Khi có sự cố lúc 2 giờ sáng, lần theo một ma_yeu_cau xuyên qua nginx, backend, cổng AI và bộ chạy trong dưới một phút, và có biểu đồ cho ba chỉ số sức khoẻ của bản local.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: không trường nào chứa nội dung tin nhắn đi vào span, metric label hay log.

```prompt
Đọc AGENTS.md trước. Thêm quan sát tập trung. Các dịch vụ mới đặt trong tệp riêng deploy/giam_sat/docker-compose.giam-sat.yml,
được docker-compose.yml nạp bằng khoá include ở cấp cao nhất. OTel collector, Prometheus, Alertmanager, Grafana, Tempo
có profiles: [giam_sat]; Loki và Alloy có profiles: [nhat_ky], để bật riêng bằng docker compose --profile <ten> up -d. Cổng chỉ nghe 127.0.0.1: prometheus 9090, alertmanager 9093, grafana 3000,
loki 3100; otel-collector (4317, 4318), tempo (3200), alloy chỉ nội bộ. Đặt giới hạn bộ nhớ cho từng dịch vụ.

1. OpenTelemetry trong backend (hỏi trước khi thêm thư viện opentelemetry-*):
   - Tự động đo FastAPI, httpx, SQLAlchemy, Redis. Gắn ma_yeu_cau làm thuộc tính của span gốc; nhận traceparent từ nginx.
   - Span thủ công cho các chặng: kiem_tra_han_muc, dung_ngu_canh, truy_hoi, goi_mo_hinh (thuộc tính nguon, tang, model,
     token_vao, token_ra, chi_phi_usd, thoi_gian_nap_ms), luu_hoi_thoai.
   - Xuất qua OTLP tới otel-collector; collector chuyển vết sang Tempo (hoặc Jaeger), metric sang Prometheus.
2. Metric Prometheus tại /metrics (chỉ mở trong mạng nội bộ, không qua nginx công khai):
   tro_ly_luot_tong{nguon,tang,phong_ban,thanh_cong}, tro_ly_do_tre_giay (histogram), tro_ly_token_tong{chieu},
   tro_ly_chi_phi_usd_tong{phong_ban,tang}, tro_ly_toc_do_tok_s (histogram), tro_ly_thoi_gian_nap_ms (histogram),
   tro_ly_hang_doi_do_dai (gauge), tro_ly_roi_tang_tong, tro_ly_cat_ngu_canh_tong, tro_ly_tu_choi_can_cu_tong,
   tro_ly_cong_cu_tong{ten,trang_thai}.
   Label KHÔNG được chứa nguoi_id, ma_yeu_cau hay nội dung (tránh bùng nổ số chuỗi và rò rỉ).
3. Loki + Alloy gom nhật ký JSON của backend, litellm, nginx; nhãn theo dịch vụ, không theo người dùng. Trên Docker
   Desktop cho Windows, Alloy đọc log qua Docker API (discovery.docker với /var/run/docker.sock), không đọc đường dẫn
   /var/lib/docker/containers vì đường dẫn đó nằm trong máy ảo WSL2.
4. Grafana, provisioning bằng tệp trong deploy/giam_sat/grafana/:
   - Bảng "Sức khoẻ bộ chạy local": tok/s trung vị và p90, tỷ lệ phải chờ nạp model, độ dài hàng đợi, VRAM từ /giam-sat/bo-chay.
   - Bảng "Chuỗi định tuyến": tỷ lệ phục vụ theo tầng, tỷ lệ rơi tầng, lỗi theo nhà cung cấp.
   - Bảng "Chi phí theo phòng ban" theo ngày.
   - Liên kết từ một dòng log có ma_yeu_cau sang vết tương ứng.
5. Luật cảnh báo Prometheus: tỷ lệ rơi khỏi tầng đầu > 20% trong 1 giờ; chi phí ngày > 80% ngân sách; tỷ lệ chờ nạp
   model > 30%; /ready lỗi 3 lần liên tiếp. Chỉ cần gửi tới Alertmanager, chưa cấu hình kênh nhận.
6. docs/doc-chi-so.md: bổ sung cách đọc từng bảng điều khiển và hành động tương ứng (tăng keep_alive, giảm num_ctx,
   giảm số yêu cầu đồng thời, kiểm tra khoá nhà cung cấp).
7. tests/test_quan_sat.py: /metrics có đủ các metric trên; không label nào tên nguoi_id hay ma_yeu_cau; span goi_mo_hinh
   không có thuộc tính chứa nội dung tin nhắn (dùng in-memory exporter).

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_quan_sat.py -v -> kỳ vọng: tất cả đạt.
2. docker compose --profile giam_sat up -d, gửi 5 câu hỏi, curl -s "localhost:9090/api/v1/query?query=tro_ly_luot_tong"
   -> kỳ vọng: có dữ liệu.
3. docker compose --profile nhat_ky up -d; lấy X-Ma-Yeu-Cau của một phản hồi, rồi curl -s -G localhost:3100/loki/api/v1/query_range --data-urlencode
   'query={dich_vu=~"backend|litellm"} |= "<ma>"' -> kỳ vọng: thấy log backend và litellm cùng mã.
4. curl -s localhost:3000/api/search (tài khoản admin Grafana từ .env) -> kỳ vọng: có đủ 3 bảng điều khiển.
5. curl -s localhost:8000/metrics | grep -c "nguoi_id" -> kỳ vọng: 0.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Vết OpenTelemetry có ma_yeu_cau, đủ 5 span chặng, không chứa nội dung
- /metrics đủ 11 metric, label không có định danh người dùng
- Ba bảng điều khiển Grafana và 4 luật cảnh báo, tất cả provisioning bằng tệp
- docs/doc-chi-so.md cập nhật

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_quan_sat.py -v                                          # kỳ vọng: tất cả đạt
docker compose --profile giam_sat up -d && docker compose --profile giam_sat ps   # kỳ vọng: dịch vụ giám sát chạy
curl -s "localhost:9090/api/v1/query?query=tro_ly_luot_tong"              # kỳ vọng: có chuỗi dữ liệu
curl -s localhost:8000/metrics | grep -c "nguoi_id"                       # kỳ vọng: 0
curl -s -u admin:$GRAFANA_MAT_KHAU localhost:3000/api/search              # kỳ vọng: 3 bảng điều khiển
```

```batbuoc
Không đưa nguoi_id, ma_yeu_cau hay bất kỳ nội dung nào vào label của metric. Mỗi giá trị label là một chuỗi thời gian mới: đưa nguoi_id vào sẽ làm Prometheus phình theo số người dùng, còn nội dung trong label thì bị giữ lâu hơn cả nhật ký.
```

### PROMPT 43. Langfuse theo dõi chất lượng và OpenBao giữ bí mật

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Theo Module 1, lớp quan sát cần trả lời được câu "chất lượng có đang xấu đi không", ngoài câu "hệ thống có chạy không". Prompt này cũng đưa khoá API ra khỏi tệp .env ở môi trường vận hành.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: nội dung gửi sang Langfuse là bản đã che dữ liệu cá nhân, và ứng dụng vẫn khởi động được ở dev khi không có OpenBao.

```prompt
Đọc AGENTS.md trước. Thêm Langfuse và OpenBao, cả hai tự host trong hạ tầng doanh nghiệp.

Phần 1 - Langfuse, profile quan_sat trong deploy/giam_sat/docker-compose.giam-sat.yml:
0. Langfuse bản hiện hành gồm langfuse-web, langfuse-worker, ClickHouse, MinIO (lưu sự kiện) và một Redis riêng
   (redis-langfuse, không dùng chung Redis của ứng dụng); dữ liệu quan hệ dùng database langfuse riêng trong db.
   langfuse-web mở 127.0.0.1:3001 (container 3000) để không trùng Grafana; các thành phần còn lại chỉ nội bộ;
   ghim phiên bản mọi image; đặt giới hạn bộ nhớ ClickHouse (khoảng 2 GB) cho laptop.
1. Mỗi lượt trả lời tạo một trace Langfuse với: ma_yeu_cau làm trace id, phong_ban, nguon, tang, model, phien_ban_loi_nhac,
   token, chi phí, độ trễ, trich_dan (mã tài liệu), cờ da_cat_ngu_canh, cờ tu_choi_can_cu.
2. Nội dung câu hỏi và câu trả lời gửi sang Langfuse CHỈ LÀ BẢN ĐÃ CHE bằng che_du_lieu_ca_nhan; biến GUI_NOI_DUNG_LANGFUSE
   mặc định false - khi false chỉ gửi độ dài và số token.
3. Nút "hữu ích / không hữu ích" trên giao diện Angular dưới mỗi câu trả lời: gửi POST /phan-hoi {ma_yeu_cau, diem, ghi_chu}
   (ghi_chu cũng bị che), lưu bảng phan_hoi và đẩy thành score trong Langfuse.
4. Kết quả eval (app/eval/runner.py) đẩy thành dataset run trong Langfuse, gắn tên model và phien_ban_loi_nhac, để so sánh
   giữa các lần đổi lời nhắc hay đổi model.
5. Việc gửi Langfuse chạy nền, lỗi thì bỏ qua và ghi cảnh báo; KHÔNG làm chậm hay hỏng câu trả lời.

Phần 2 - OpenBao:
6. Dịch vụ openbao trong compose, profile bi_mat, cổng 127.0.0.1:8200 (chế độ dev chỉ cho môi trường dev; ghi rõ prod
   phải khởi tạo, unseal và sao lưu).
7. app/config.py: nếu có BAO_ADDR và BAO_ROLE_ID/BAO_SECRET_ID thì đọc APP_SECRET, POSTGRES_PASSWORD, LITELLM_KEY,
   khoá nhà cung cấp (cho dịch vụ litellm) từ đường dẫn kv/hybrid-assistant-chatbot/<moi_truong>; không có thì đọc .env như cũ.
   MOI_TRUONG=prod mà không có OpenBao -> ghi CHƯA ĐẠT trong kiem_tra_truoc_khi_mo.py (không chặn khởi động).
8. scripts/nap_bi_mat_openbao.py: đọc .env cục bộ, ghi vào OpenBao, in danh sách khoá đã nạp (không in giá trị).
9. Cập nhật AGENTS.md: mục "Không làm" bỏ "cổng AI riêng" nếu có; thêm quy tắc "nội dung gửi ra công cụ quan sát phải là
   bản đã che". Cập nhật README và CHANGELOG.
10. tests/test_langfuse_openbao.py: nội dung gửi Langfuse đã che số điện thoại và mã khách hàng; Langfuse lỗi không làm
    hỏng /chat; config đọc được bí mật từ OpenBao giả lập; không có OpenBao thì rơi về .env.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_langfuse_openbao.py -v -> kỳ vọng: tất cả đạt.
2. docker compose --profile quan_sat up -d; gửi câu hỏi có "0900000001" và "KH00012345" với GUI_NOI_DUNG_LANGFUSE=true;
   curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" "localhost:3001/api/public/traces?limit=1" -> kỳ vọng: chỉ thấy
   <SO_DIEN_THOAI_1>, <MA_KHACH_HANG_1>.
3. docker compose stop langfuse-web langfuse-worker && gửi câu hỏi -> kỳ vọng: vẫn trả lời bình thường, có dòng cảnh báo trong log.
4. cd backend && python -m app.eval.runner --tang local1 --lan 1 -> kỳ vọng: xuất hiện dataset run mới trong Langfuse.
5. docker compose --profile bi_mat up -d openbao; python scripts/nap_bi_mat_openbao.py rồi khởi động lại backend với
   BAO_ADDR=http://openbao:8200 -> kỳ vọng: /ready 200; log không có giá trị bí mật.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Mỗi lượt có một trace Langfuse theo ma_yeu_cau; nội dung gửi đi đã che hoặc chỉ gửi độ dài
- Nút phản hồi trên giao diện thành score Langfuse; eval thành dataset run
- Config đọc bí mật từ OpenBao, rơi về .env ở dev
- Langfuse hỏng không làm hỏng câu trả lời; AGENTS.md, README, CHANGELOG đã cập nhật

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_langfuse_openbao.py -v                  # kỳ vọng: tất cả đạt
TOKEN=$(python scripts/lay_token_thu.py --nguoi nv_kinh_doanh)
docker compose stop langfuse-web langfuse-worker && curl -s -X POST localhost:8000/api/v1/chat -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"noi_dung":"xin chào"}'   # kỳ vọng: vẫn có câu trả lời
python scripts/nap_bi_mat_openbao.py                      # kỳ vọng: in tên khoá, không in giá trị
```

```meo
Tỷ lệ "không hữu ích" theo phòng ban trên Langfuse thường báo hiệu kho tài liệu của phòng ban đó đã cũ trước khi bất kỳ chỉ số kỹ thuật nào đổi màu. Gửi báo cáo này hằng tháng cho chủ sở hữu nghiệp vụ của từng kho tri thức.
```

## Giai đoạn 10: Kubernetes và vLLM

Mở workspace hybrid-assistant-chatbot trong Antigravity. Dùng Editor View cho PROMPT 44-46 và Manager Surface cho PROMPT 47-49. Cài sẵn kubectl, helm, k3d trên máy phát triển (Windows: winget install Kubernetes.kubectl Helm.Helm k3d); kubeconform và trivy dùng qua image docker nên không cần cài. Bảo đảm thẻ git giai-doan-9 đã có. Trên Windows, chạy mọi lệnh tự đánh giá trong Git Bash ở gốc repo, sau khi nạp biến môi trường: `set -a && source .env && set +a && export MSYS_NO_PATHCONV=1` (biến cuối để Git Bash không đổi đường dẫn dạng /api/... thành đường dẫn Windows). Lệnh `docker compose exec` luôn kèm `-T` để không lỗi "the input device is not a TTY".

**Hai đường chạy của giai đoạn này.** Đường laptop (Windows 11, GPU 8 GB, Docker Desktop): cụm k3d chạy backend, frontend, worker, litellm, redis, postgres. Máy chủ model KHÔNG chạy trong cụm, vì k3d/kind trên Docker Desktop cho Windows không chuyển GPU vào pod được một cách thực tế. Thay vào đó, Ollama trên Windows hoặc container vLLM chạy bằng docker run --gpus all bên ngoài cụm, và cụm gọi tới qua Service ExternalName host.docker.internal. Đường máy chủ GPU (Linux, NVIDIA GPU Operator, từ 16 GB): chạy vLLM trong cụm, nhiều GPU, cân bằng tải. Các phần ghi "CHỈ TRÊN MÁY CHỦ GPU" được kiểm trên laptop bằng helm template và kubeconform thay vì GPU thật. Trước khi dựng k3d, chạy docker compose down (giữ volume) để giải phóng cổng và RAM.

**Mục tiêu giai đoạn.** Đưa hệ thống lên Kubernetes để chạy nhiều bản sao, tự giãn theo tải ở phần ứng dụng, và thay Ollama bằng vLLM ở môi trường thật để phục vụ nhiều người đồng thời trên GPU hữu hạn. Ứng dụng chỉ đổi địa chỉ bộ chạy, không đổi mã gọi model.

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| vLLM phục vụ model local ở môi trường thật, tương thích OpenAI | Tinh chỉnh model → Giai đoạn 11 |
| Helm chart cho backend, frontend, worker nạp tài liệu, cổng AI | Triển khai nhiều cụm, nhiều vùng → ngoài phạm vi tài liệu |
| NVIDIA GPU Operator, nhiều GPU, cân bằng tải máy chủ model (chỉ trên máy chủ GPU; laptop kiểm bằng máy chủ model giả lập) | Tự giãn số GPU theo tải → ngoài phạm vi tài liệu |
| Probes khớp /health và /ready, Ingress tắt đệm cho SSE, HPA cho backend | Service mesh → ngoài phạm vi tài liệu |
| NetworkPolicy, External Secrets, quét Trivy | |
| CI/CD với cổng đánh giá, chạy thử trên k3d/kind | |

**Điều kiện hoàn thành**

- helm install trên k3d dựng được toàn bộ hệ thống; /ready trả 200; giao diện đăng nhập và trò chuyện được.
- Luồng SSE qua Ingress phát chữ dần, không bị gom.
- Từ một pod bất kỳ ngoài backend và cổng AI, không gọi được cổng của vLLM/Ollama.
- Pipeline CI chặn được một thay đổi làm giảm tỷ lệ đạt của bộ eval.
- Demo trên laptop: vLLM hồ sơ vllm8 chạy bằng docker ngoài cụm và trả lời qua backend; phần GPU trong cụm chỉ kiểm
  bằng helm template và kubeconform.
- Phát hành phiên bản `2.2.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v2.2.0` và `git tag giai-doan-10` trên cùng commit

### PROMPT 44. vLLM thay Ollama ở môi trường thật

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Theo Module 2: Ollama cho phòng lab, vLLM cho sản xuất nhờ xử lý theo lô liên tục và PagedAttention. Ứng dụng không cần biết bên dưới là cái nào.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: mã chỉ đổi ở app/llm/bo_chay_local.py, app/llm/router.py (bỏ gọi
Ollama khi LOAI_BO_CHAY=vllm) và cấu hình; thêm scripts/doi_bo_chay.sh và tệp compose vLLM.

```prompt
Đọc AGENTS.md trước. Thêm vLLM làm loại bộ chạy thứ ba. Trình Implementation Plan trước.

1. LOAI_BO_CHAY nhận thêm giá trị vllm. Trong app/llm/bo_chay_local.py thêm lớp BoChayVLLM hiện thực giao diện BoChay:
   - Gọi {dia_chi}/chat/completions như Ollama; KHÔNG gửi keep_alive và options.num_ctx (vLLM không dùng, cửa sổ đặt lúc khởi động).
   - Chỉ một máy chủ model giữ GPU tại một thời điểm: khi LOAI_BO_CHAY=vllm, ham_nong và goi_nhung KHÔNG gọi Ollama;
     RAG tự lùi về BM25 nếu model nhúng không sẵn sàng (đường suy giảm đã có từ Giai đoạn 6).
   - doc_trang_thai_bo_chay: đọc /metrics của vLLM (vllm:num_requests_running, vllm:num_requests_waiting,
     vllm:gpu_cache_usage_perc) thay cho /api/ps.
   - doc_ngu_canh_thuc_te: đọc /v1/models (max_model_len) và so với cấu hình.
   - ham_nong vẫn gọi một câu ngắn lúc khởi động.
2. config/models.yaml: thêm hồ sơ vllm8 cho laptop và vllm16, vllm24 cho máy chủ GPU:
   - vllm8 (laptop, RTX A4000 Laptop 8 GB, kiến trúc Ampere): model ≤4B cùng dòng bậc local, bản AWQ hoặc GPTQ 4-bit;
     nếu chưa có bản lượng tử thì dùng model 2B bản gốc BF16. KHÔNG dùng FP8 vì Ampere không có hỗ trợ phần cứng cho
     FP8. max_model_len 8192, gpu_memory_utilization 0.85, max_num_seqs 4, enforce_eager bật để tiết kiệm VRAM.
   - vllm16: model bậc 1 bản lượng tử AWQ của dòng 9b (FP8 chỉ khi GPU từ thế hệ Ada/Hopper trở lên), max_model_len
     32768, gpu_memory_utilization 0.90.
   - vllm24: model bậc 1 dòng 27b bản AWQ (FP8 theo điều kiện như trên), max_model_len 16384.
   - Ghi chú: tên repo model trên Hugging Face phải đối chiếu lại; chỉ dùng model có giấy phép Apache-2.0 hoặc MIT (Module 2).
   - Bậc 2 trên vLLM: một model nhỏ chạy trên cùng GPU với gpu_memory_utilization thấp, hoặc giữ Ollama làm bậc 2 - ghi rõ lựa chọn.
3. Hàng đợi: với vLLM, SO_LUONG_DONG_THOI có thể lớn hơn (vLLM tự xếp lô); đặt mặc định theo max_num_seqs và ghi chú:
   semaphore của ứng dụng vẫn cần để báo vị trí hàng đợi cho người dùng và để chặn tràn bộ đệm KV.
4. deploy/vllm/docker-compose.vllm.yml để chạy thử trên một máy GPU (dùng chung mạng với docker-compose.yml qua -f):
   image vllm/vllm-openai ghim phiên bản, --api-key, --max-model-len, --gpu-memory-utilization, --served-model-name
   trùng alias; GPU xin bằng deploy.resources.reservations.devices (driver nvidia, count 1) - cú pháp chạy được trên
   Docker Desktop WSL2; cổng 127.0.0.1:8002:8000 (8000 đã là backend); thư mục bộ nhớ đệm Hugging Face gắn volume
   có tên để không tải lại trọng số. Backend gọi http://vllm:8000/v1 trong mạng docker.
   Kịch bản scripts/doi_bo_chay.sh ollama|vllm: trước khi bật vLLM thì dừng Ollama để giải phóng VRAM (Windows:
   powershell -Command "Stop-Process -Name 'ollama app','ollama' -Force -ErrorAction SilentlyContinue"; Linux:
   systemctl stop ollama), kiểm nvidia-smi còn ít nhất 7 GB trống, rồi mới up vllm; chiều ngược lại dừng vllm rồi mở Ollama.
5. docs/uoc-luong-vram.md: công thức (trọng số + bộ đệm KV) ÷ 0,9; bảng ví dụ cho 16GB và 24GB; cách tính số phiên
   đồng thời từ max_model_len và dung lượng KV mỗi token; nhắc con số chính thức phải đến từ thử tải.
6. scripts/do_toc_do.py: thêm tham số --dong-thoi N để đo thông lượng khi N yêu cầu cùng lúc (so Ollama với vLLM).
7. tests/test_bo_chay_vllm.py dùng MockTransport: thân yêu cầu không có keep_alive; đọc đúng metric running/waiting;
   phát hiện lệch max_model_len.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_bo_chay_vllm.py -v -> kỳ vọng: tất cả đạt.
2. git diff --stat giai-doan-9 -- backend/app -> kỳ vọng: chỉ app/llm/bo_chay_local.py, app/llm/router.py và config.py thay đổi.
3. Trên laptop (hồ sơ vllm8): bash scripts/doi_bo_chay.sh vllm; docker compose -f docker-compose.yml -f
   deploy/vllm/docker-compose.vllm.yml up -d vllm; chờ log "Application startup complete"; đặt LOAI_BO_CHAY=vllm,
   HO_SO_GPU=vllm8, khởi động lại backend, hỏi một câu qua /chat/stream -> kỳ vọng: chữ phát dần, bat_dau ghi model vLLM.
4. python scripts/do_toc_do.py --dong-thoi 4 lần lượt với vLLM rồi (sau bash scripts/doi_bo_chay.sh ollama) với Ollama
   -> kỳ vọng: in bảng so sánh thông lượng.
5. cd backend && pytest -q -> kỳ vọng: toàn bộ kiểm thử cũ vẫn đạt.
6. bash scripts/doi_bo_chay.sh ollama && ollama ps -> kỳ vọng: laptop trở về Ollama, vllm đã dừng.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Lớp BoChayVLLM sau giao diện BoChay; không sửa nơi gọi
- Hồ sơ vllm8 (laptop, AWQ/GPTQ, không FP8), vllm16, vllm24, model có giấy phép phù hợp
- scripts/doi_bo_chay.sh bảo đảm chỉ một máy chủ model giữ GPU tại một thời điểm
- Tệp compose chạy thử vLLM, cổng chỉ nghe loopback, có api-key
- docs/uoc-luong-vram.md và số đo thông lượng Ollama so với vLLM

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_bo_chay_vllm.py -v                     # kỳ vọng: tất cả đạt
git diff --stat giai-doan-9 -- backend/app               # kỳ vọng: chỉ bo_chay_local.py, router.py, config.py
bash scripts/doi_bo_chay.sh vllm && docker compose -f docker-compose.yml -f deploy/vllm/docker-compose.vllm.yml up -d vllm   # kỳ vọng: vllm chạy
python scripts/do_toc_do.py --dong-thoi 4                # kỳ vọng: bảng thông lượng
bash scripts/doi_bo_chay.sh ollama                       # kỳ vọng: trả GPU lại cho Ollama
cd backend && pytest -q                                                # kỳ vọng: không kiểm thử cũ nào hỏng
```

```batbuoc
Tiêu chí chọn model quan trọng nhất ở doanh nghiệp là giấy phép (Module 2). Chỉ đưa vào models.yaml model có giấy phép Apache-2.0 hoặc MIT; model có giấy phép cộng đồng riêng phải qua rà soát pháp lý; không dùng model giấy phép phi thương mại.
```

```meo
Chạy do_toc_do.py với 1 yêu cầu và với 4 (laptop) hoặc 8 (máy chủ) yêu cầu đồng thời. Với 1 người dùng, vLLM và Ollama gần như ngang nhau; khác biệt chỉ lộ ra khi nhiều người cùng hỏi. Hãy dùng số đo khi có nhiều yêu cầu đồng thời để quyết định có cần vLLM hay không.
```

### PROMPT 45. Helm chart cho toàn hệ thống

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Một lệnh helm install dựng lại toàn bộ hệ thống trên cụm trống, cấu hình dev và prod khác nhau đúng chỗ cần khác.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: không có bí mật nào trong values.yaml, và migration cơ sở dữ liệu chạy một lần bằng Job chứ không chạy trong mỗi pod backend.

```prompt
Đọc AGENTS.md trước. Viết Helm chart tại deploy/helm/hybrid-assistant-chatbot/.

1. Thành phần (mỗi thành phần một Deployment/StatefulSet và Service riêng, bật tắt bằng values):
   backend, frontend (nginx phục vụ bản build Angular), worker-nap-tai-lieu (chạy scripts/nap_tai_lieu.py theo hàng đợi
   hoặc CronJob), litellm, redis, bo-chay (máy chủ model, values boChay.cheDo: vllm | ollama | gia_lap | ngoai),
   keycloak (tuỳ chọn - thường dùng IdP có sẵn),
   postgres (tuỳ chọn - khuyến nghị dùng dịch vụ ngoài hoặc operator như CloudNativePG, ghi rõ trong README chart).
2. Migration: Job helm hook pre-install/pre-upgrade chạy alembic upgrade head; backend KHÔNG tự migrate lúc khởi động.
3. ConfigMap từ config/models.yaml, config/anh_xa_nhom.yaml, config/rag.yaml, prompts/*.md; đổi nội dung thì pod
   khởi động lại nhờ annotation checksum.
4. Bí mật: chart chỉ tham chiếu Secret theo tên (existingSecret); KHÔNG có giá trị bí mật trong values.yaml. Việc tạo
   Secret làm ở PROMPT 48.
   Về máy chủ model (bo-chay), chế độ ngoai: Service tro-ly-bo-chay kiểu ExternalName trỏ host.docker.internal (cổng 11434 Ollama hoặc 8002 vLLM
   chạy ngoài cụm). Nếu CoreDNS của k3d không phân giải được tên này, dùng Service không selector kèm Endpoints với IP
   lấy từ docker run --rm alpine getent hosts host.docker.internal. Chế độ gia_lap: máy chủ model giả lập nhỏ
   (backend/tests/tien_ich/bo_chay_gia.py đóng thành image), trả luồng chữ cố định và /metrics kiểu vLLM, dùng để kiểm
   cân bằng tải và NetworkPolicy trên laptop không cần GPU.
5. Bốn tệp values: values.yaml (mặc định an toàn), values-k3d.yaml (laptop: boChay.cheDo=ngoai, 1 bản sao mỗi thành
   phần, requests nhỏ), values-k3d-gia-lap.yaml (chồng lên values-k3d: boChay.cheDo=gia_lap, 2 bản sao),
   values-prod.yaml (vLLM, 2 bản sao backend trở lên, resources requests/limits, PodDisruptionBudget, anti-affinity).
6. securityContext cho mọi container: runAsNonRoot, uid 10001, readOnlyRootFilesystem (thêm emptyDir cho /tmp),
   allowPrivilegeEscalation false, drop ALL capabilities.
7. Chuyển biến MOI_TRUONG, CHE_DO_DINH_TUYEN, HO_SO_GPU, LOAI_BO_CHAY vào values; DIA_CHI_BO_CHAY trỏ Service nội bộ của vllm.
8. deploy/helm/README.md: cài trên k3d từng bước, nâng cấp, quay lui (helm rollback), gỡ.
9. Kiểm thử chart: helm lint; helm template với cả ba tệp values rồi kiểm bằng kubeconform; thêm backend/tests/helm/test_values.py
   quét kết quả template khẳng định không có chuỗi giống khoá API và mọi container có runAsNonRoot.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. helm lint deploy/helm/hybrid-assistant-chatbot -> kỳ vọng: 0 lỗi.
2. helm template t deploy/helm/hybrid-assistant-chatbot -f values-prod.yaml | docker run --rm -i ghcr.io/yannh/kubeconform:latest
   -strict -summary -ignore-missing-schemas -> kỳ vọng: 0 lỗi (lặp lại với values-k3d.yaml).
3. cd backend && pytest tests/helm/test_values.py -v -> kỳ vọng: đạt.
4. k3d cluster create tro-ly -p "8443:443@loadbalancer" -p "8081:80@loadbalancer"; k3d image import (các image vừa
   build) -c tro-ly; helm install tro-ly deploy/helm/hybrid-assistant-chatbot -f values-k3d.yaml --wait --timeout 15m
   -> kỳ vọng: mọi pod Ready, Job migration Completed.
5. kubectl port-forward svc/tro-ly-backend 8000:8000 và curl -s localhost:8000/ready -> kỳ vọng: 200.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Chart đủ thành phần, bật tắt bằng values; ba tệp values dev, k3d, prod
- Migration chạy bằng Job hook, không trong pod backend
- Không bí mật trong values; mọi container chạy không phải root
- helm lint, kubeconform, cài thử trên k3d đều đạt

**Tự đánh giá**

```danhgia
helm lint deploy/helm/hybrid-assistant-chatbot                                             # kỳ vọng: 0 lỗi
helm template t deploy/helm/hybrid-assistant-chatbot -f values-prod.yaml | docker run --rm -i ghcr.io/yannh/kubeconform:latest -strict -summary -ignore-missing-schemas   # kỳ vọng: 0 lỗi
k3d cluster create tro-ly -p "8443:443@loadbalancer" -p "8081:80@loadbalancer"             # kỳ vọng: cụm 1 nút
helm install tro-ly deploy/helm/hybrid-assistant-chatbot -f values-k3d.yaml --wait --timeout 15m   # kỳ vọng: mọi pod Ready
kubectl port-forward svc/tro-ly-backend 8000:8000 & sleep 3; curl -s localhost:8000/ready   # kỳ vọng: 200
```

```batbuoc
Không chạy alembic upgrade trong lệnh khởi động của pod backend. Với nhiều bản sao, vài pod sẽ cùng migrate một lúc và làm hỏng lược đồ. Migration phải là một Job chạy đúng một lần trước khi các pod mới lên.
```

### PROMPT 46. GPU Operator, nhiều GPU và cân bằng tải máy chủ model

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Phục vụ model trên nhiều GPU hoặc nhiều nút GPU, và chia tải hợp lý cho các luồng phát dài để một máy chủ model không bị dồn hết bộ đệm KV trong khi máy khác còn trống.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: cách chia tải có tính tới việc một yêu cầu SSE giữ kết nối lâu.

```prompt
Đọc AGENTS.md trước. Thêm hỗ trợ nhiều GPU cho máy chủ model trong Helm chart.

1. docs/gpu-operator.md (CHỈ TRÊN MÁY CHỦ GPU Linux): cài NVIDIA GPU Operator bằng Helm, kiểm nút có nhãn
   nvidia.com/gpu.present và tài nguyên nvidia.com/gpu. Ghi rõ: trên laptop Windows với Docker Desktop, k3d/kind không
   chuyển GPU vào pod một cách thực tế; laptop kiểm phần GPU bằng helm template, còn cân bằng tải kiểm bằng
   values-k3d-gia-lap.yaml (hai bản sao máy chủ model giả lập).
2. Hai chiến lược, chọn bằng values vllm.cheDo:
   a) nhan_ban (mặc định): mỗi pod vLLM một GPU, cùng một model, N bản sao. Service phía trước.
   b) chia_tensor: một pod dùng nhiều GPU trên cùng nút (--tensor-parallel-size = số GPU) cho model không vừa một GPU.
   Ghi trong values-prod.yaml ví dụ 2 bản sao x 1 GPU 24GB.
3. Cân bằng tải: Service Kubernetes mặc định chia theo kết nối nên không đều với luồng dài. Hai lựa chọn, ghi rõ trong tài liệu:
   - Đơn giản: để LiteLLM (cổng AI) giữ danh sách nhiều api_base cho cùng alias với routing_strategy least-busy.
   - Nâng cao: dùng một bộ định tuyến hiểu tải của vLLM (dựa trên vllm:num_requests_waiting). Chỉ ghi hướng dẫn, chưa triển khai.
   Hiện thực lựa chọn đơn giản: headless Service để LiteLLM thấy từng pod, cấu hình litellm nhiều deployment cùng
   model_name tro-ly-chat-local.
4. app/giam_sat/suc_khoe.py: /giam-sat/bo-chay trả trạng thái TỪNG bản sao (running, waiting, gpu_cache_usage);
   bảng điều khiển Grafana thêm biểu đồ theo pod.
5. Hàng đợi ứng dụng: SO_LUONG_DONG_THOI tính theo tổng khe của mọi bản sao (đọc từ values), ghi chú công thức.
6. Không thêm tự giãn số pod vLLM theo tải: ghi rõ lý do trong tài liệu (khởi động một pod vLLM mất vài phút nạp trọng
   số, GPU là tài nguyên cố định); thay vào đó cảnh báo khi waiting kéo dài để người vận hành quyết định.
7. tests/test_nhieu_ban_sao.py: /giam-sat/bo-chay gộp đúng trạng thái 2 bản sao giả lập; SO_LUONG_DONG_THOI bằng tổng khe.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_nhieu_ban_sao.py -v -> kỳ vọng: tất cả đạt.
2. helm template t deploy/helm/hybrid-assistant-chatbot -f values-prod.yaml | grep -A3 "nvidia.com/gpu" -> kỳ vọng: mỗi pod
   vLLM xin đúng số GPU theo chiến lược (kiểm trên laptop, không cần GPU).
3. Trên k3d: helm upgrade tro-ly ... -f values-k3d.yaml -f values-k3d-gia-lap.yaml --wait; gửi 10 câu hỏi đồng thời,
   xem /api/v1/giam-sat/bo-chay -> kỳ vọng: cả hai bản sao giả lập đều có yêu cầu.
4. helm lint -> kỳ vọng: 0 lỗi.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Hai chiến lược nhan_ban và chia_tensor chọn bằng values
- Cân bằng tải qua cổng AI least-busy, headless Service
- /giam-sat/bo-chay theo từng bản sao; SO_LUONG_DONG_THOI theo tổng khe
- Tài liệu GPU Operator và lý do không tự giãn pod GPU

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_nhieu_ban_sao.py -v                                         # kỳ vọng: tất cả đạt
helm template t deploy/helm/hybrid-assistant-chatbot -f values-prod.yaml | grep -A3 "nvidia.com/gpu"   # kỳ vọng: đúng số GPU
helm upgrade tro-ly deploy/helm/hybrid-assistant-chatbot -f values-k3d.yaml -f values-k3d-gia-lap.yaml --wait   # kỳ vọng: 2 bản sao giả lập Ready
curl -s -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/giam-sat/bo-chay | python -m json.tool   # kỳ vọng: có từng bản sao
```

```meo
Nhân bản (mỗi pod một GPU) gần như luôn tốt hơn chia tensor khi model vừa một GPU: hỏng một GPU chỉ mất một nửa năng lực thay vì mất cả model, và không tốn băng thông giữa các GPU.
```

### PROMPT 47. Probes, Ingress cho SSE và tự giãn backend

**Chế độ:** Manager Surface · **Đọc Plan:** Có

**Mục tiêu.** Lưu lượng chỉ đổ vào pod đã sẵn sàng, luồng SSE không bị proxy gom lại, và phần ứng dụng tự giãn theo tải mà không kéo GPU theo.

**Làm trước.** Đọc Implementation Plan. Trong Manager Surface, giao song song: một agent làm probes và HPA, một agent làm Ingress và kiểm thử SSE.

```prompt
Đọc AGENTS.md trước. Hoàn thiện đường vào và độ sẵn sàng trên Kubernetes.

1. Probes cho backend: livenessProbe gọi /health (không chạm phụ thuộc); readinessProbe gọi /ready (db, redis, cổng AI,
   ít nhất một tầng model); startupProbe cho phép tới 120 giây để ham_nong chạy xong. Frontend và litellm có probes riêng.
   vLLM: startupProbe dài (tới 15 phút nạp trọng số), readiness gọi /health của vLLM.
2. Ingress (nginx ingress controller), host tro-ly.vidu.com, TLS bằng Secret:
   - /api -> backend; / -> frontend.
   - Annotation cho SSE trên đường /api/v1/chat/stream: proxy-buffering off, proxy-read-timeout 600, proxy-send-timeout 600.
   - Giới hạn kích thước thân yêu cầu; KHÔNG đưa /metrics ra Ingress.
   - Header bảo mật cơ bản: HSTS, X-Content-Type-Options, frame-ancestors.
3. Tắt luồng êm: backend xử lý SIGTERM - ngừng nhận yêu cầu mới, chờ các luồng SSE đang chạy tối đa 60 giây rồi mới thoát;
   terminationGracePeriodSeconds 75; preStop sleep 5 để Ingress kịp gỡ pod.
4. HPA cho backend theo CPU và theo metric tùy biến tro_ly_hang_doi_do_dai (qua Prometheus Adapter - ghi hướng dẫn cài,
   nếu chưa có adapter thì chỉ dùng CPU). minReplicas 2, maxReplicas 6. Frontend HPA theo CPU. KHÔNG có HPA cho vLLM.
5. PodDisruptionBudget: backend minAvailable 1; vLLM maxUnavailable 1.
6. backend/tests/e2e/test_sse_ingress.py (đánh dấu pytest -m k3d): gửi yêu cầu /api/v1/chat/stream qua Ingress trên k3d, đo thời điểm nhận từng mảnh -
   khẳng định mảnh đầu tới trước khi câu trả lời xong ít nhất 1 giây (chứng minh không bị gom); xoá một pod backend giữa
   luồng thì luồng đang chạy trên pod khác không bị ảnh hưởng.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. helm upgrade tro-ly ... -f values-k3d.yaml --wait -> kỳ vọng: thành công.
2. curl -N -k --resolve tro-ly.vidu.com:8443:127.0.0.1 https://tro-ly.vidu.com:8443/api/v1/chat/stream (cổng 8443 của
   load balancer k3d) -> kỳ vọng: chữ hiện dần.
3. cd backend && pytest -m k3d tests/e2e/test_sse_ingress.py -v -> kỳ vọng: đạt.
4. kubectl get hpa -> kỳ vọng: backend min 2, có mục tiêu CPU; không có HPA cho vllm.
5. curl -k --resolve tro-ly.vidu.com:8443:127.0.0.1 https://tro-ly.vidu.com:8443/metrics -> kỳ vọng: 404.
Ghi chú: k3s có sẵn metrics-server cho HPA theo CPU; k3s đi kèm Traefik - tắt Traefik khi tạo cụm
(--k3s-arg "--disable=traefik@server:0") rồi cài ingress-nginx, hoặc viết annotation tương đương cho Traefik.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- liveness /health, readiness /ready, startupProbe đủ dài cho hâm nóng và nạp trọng số
- Ingress tắt đệm cho SSE, không lộ /metrics
- Tắt pod êm, không cắt luồng đang phát
- HPA cho backend và frontend, không cho vLLM; kiểm thử SSE qua Ingress đạt

**Tự đánh giá**

```danhgia
curl -N -k --resolve tro-ly.vidu.com:8443:127.0.0.1 https://tro-ly.vidu.com:8443/api/v1/chat/stream -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"noi_dung":"Giải thích ngắn gọn cách tính tiền điện bậc thang"}'   # kỳ vọng: chữ hiện dần
cd backend && pytest -m k3d tests/e2e/test_sse_ingress.py -v       # kỳ vọng: đạt
kubectl get hpa                                      # kỳ vọng: backend, frontend; không có vllm
```

```batbuoc
Readiness phải là /ready, liveness phải là /health. Nếu đặt liveness vào /ready, mỗi lần cơ sở dữ liệu chậm vài giây Kubernetes sẽ khởi động lại toàn bộ pod backend cùng lúc, và một sự cố nhỏ trở thành mất dịch vụ.
```

### PROMPT 48. NetworkPolicy, External Secrets và quét Trivy

**Chế độ:** Manager Surface · **Đọc Plan:** Có

**Mục tiêu.** Chặn đúng lớp rủi ro lớn nhất của kiến trúc local trên cụm: máy chủ model không có xác thực quản trị, nên chỉ backend và cổng AI được phép chạm vào nó.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: chính sách mặc định là từ chối, rồi mới mở từng đường.

```prompt
Đọc AGENTS.md trước. Siết an ninh trên cụm.

1. NetworkPolicy trong chart (bật mặc định):
   - Mặc định từ chối mọi ingress trong namespace.
   - frontend: nhận từ ingress controller.
   - backend: nhận từ ingress controller và frontend; được gọi ra db, redis, litellm, keycloak, OTel collector, Langfuse.
   - litellm: nhận chỉ từ backend; được gọi ra vllm/ollama, và ra Internet (egress 443) CHỈ khi values.choPhepDamMay=true.
   - bo-chay (vllm/ollama/gia_lap): nhận CHỈ từ litellm và backend (cho /giam-sat); không egress ra Internet sau khi
     đã có trọng số. Với chế độ ngoai (laptop), máy chủ model nằm ngoài cụm: mở egress của litellm và backend tới IP
     của host.docker.internal, và bảo vệ Ollama trên Windows bằng cách giữ OLLAMA_HOST=127.0.0.1 như Giai đoạn 5.
   - db, redis: nhận chỉ từ các thành phần cần.
2. Với Ollama trên cụm lab: thêm sidecar nginx chặn /api/pull, /api/create, /api/delete, /api/push, /api/copy như mẫu
   ở Giai đoạn 5; vLLM chạy với --api-key lấy từ Secret.
3. External Secrets Operator: ExternalSecret đọc từ OpenBao (ClusterSecretStore trỏ tới OpenBao của Giai đoạn 9; trên
   laptop là OpenBao dev chạy bằng docker compose --profile bi_mat, địa chỉ http://host.docker.internal:8200), tạo
   Secret cho backend (gồm DATABASE_URL và DATABASE_URL_CHI_DOC của vai trò CSDL tro_ly_chi_doc dùng cho công cụ tra cứu
   nghiệp vụ), litellm, keycloak, db. docs/bi-mat-tren-cum.md hướng dẫn cài ESO và thêm khoá mới.
4. Quét Trivy:
   - scripts/quet_trivy.sh quét image backend, frontend, worker và cấu hình chart (trivy config). Mức HIGH/CRITICAL có bản
     vá thì thoát mã 1. Dùng lệnh trivy nếu đã cài, không thì chạy image aquasec/trivy ghim phiên bản với
     -v /var/run/docker.sock:/var/run/docker.sock (chạy được trên Docker Desktop cho Windows).
   - .trivyignore chỉ được chứa mục có ghi lý do và ngày hết hạn.
5. Cập nhật kiem_tra_truoc_khi_mo.py thêm các dòng: NetworkPolicy đang bật; không Secret nào tạo từ values; quét Trivy không
   có lỗi HIGH/CRITICAL chưa xử lý; choPhepDamMay khớp CHE_DO_DINH_TUYEN (chi_local thì phải false).
6. backend/tests/e2e/test_network_policy.py (đánh dấu pytest -m k3d) trên k3d (k3s có sẵn bộ điều khiển NetworkPolicy),
   dùng values-k3d-gia-lap.yaml để máy chủ model nằm trong cụm: pod thử nghiệm gọi tro-ly-bo-chay -> bị chặn; backend
   gọi -> được; litellm với choPhepDamMay=false gọi ra Internet -> bị chặn.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. kubectl run thu --rm -i --restart=Never --image=curlimages/curl -- curl -m 3 http://tro-ly-bo-chay:8000/v1/models -> kỳ vọng: hết thời gian (bị chặn).
2. kubectl exec deploy/tro-ly-backend -- python -c "import httpx;print(httpx.get('http://tro-ly-bo-chay:8000/health').status_code)"
   -> kỳ vọng: 200.
3. cd backend && pytest -m k3d tests/e2e/test_network_policy.py -v -> kỳ vọng: đạt.
4. bash scripts/quet_trivy.sh; echo $? -> kỳ vọng: 0, hoặc danh sách lỗ hổng cần xử lý kèm mã 1.
5. kubectl get externalsecret -> kỳ vọng: mọi mục SecretSynced.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- NetworkPolicy mặc định từ chối; máy chủ model chỉ nhận từ litellm và backend
- Egress Internet của cổng AI phụ thuộc choPhepDamMay
- Bí mật đến từ OpenBao qua External Secrets, không từ values
- scripts/quet_trivy.sh có mã thoát; kiem_tra_truoc_khi_mo.py thêm 4 dòng

**Tự đánh giá**

```danhgia
kubectl run thu --rm -i --restart=Never --image=curlimages/curl -- curl -m 3 http://tro-ly-bo-chay:8000/v1/models   # kỳ vọng: bị chặn
cd backend && pytest -m k3d tests/e2e/test_network_policy.py -v                # kỳ vọng: đạt
bash scripts/quet_trivy.sh; echo $?                              # kỳ vọng: 0
kubectl get externalsecret                                       # kỳ vọng: SecretSynced
```

```batbuoc
Khi phòng ban hay toàn hệ thống đặt chi_local, chặn egress Internet của cổng AI ở mức mạng. Đây là lớp chặn thứ ba sau chính sách trong ứng dụng và khoá ảo của cổng: kể cả khi có lỗi cấu hình ở hai lớp trên, dữ liệu vẫn không ra được khỏi cụm.
```

### PROMPT 49. CI/CD với cổng đánh giá và chạy thử trên k3d

**Chế độ:** Manager Surface · **Đọc Plan:** Có

**Mục tiêu.** Mỗi thay đổi lời nhắc, model hay mã đều phải qua bộ đánh giá trước khi lên môi trường thật. Khi chất lượng xấu đi, pipeline dừng lại trước khi người dùng gặp phải.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: pipeline không cần khoá API thật của nhà cung cấp đám mây để chạy các bước bắt buộc.

```prompt
Đọc AGENTS.md trước. Viết pipeline CI/CD trong .github/workflows/ (hoặc .gitlab-ci.yml nếu kho mã dùng GitLab - hỏi trước).

1. Bước kiem-tra (mọi pull request): ruff + mypy backend; pytest (không gọi mạng thật); ng lint + ng test frontend;
   helm lint + kubeconform; quét bí mật trong mã (gitleaks); grep khẳng định không có lời gọi httpx/litellm tới model
   ngoài app/llm/.
2. Bước build: image backend, frontend, worker; gắn thẻ theo commit; quét Trivy (PROMPT 48); đẩy lên registry nội bộ.
3. Bước danh-gia (cổng chất lượng), chạy khi có thay đổi trong prompts/, config/models.yaml, config/rag.yaml, app/llm/, app/rag/:
   - Dựng hệ thống trên k3d trong runner (values-k3d.yaml, model local nhỏ nhất để chạy được không cần GPU).
   - Chạy python -m app.eval.runner --tang local1 --lan 3 trên ba bộ eval/bo_cau_hoi.yaml, eval/bo_cau_hoi_rag.yaml,
     eval/bo_cau_hoi_cong_cu.yaml; so với kết quả của nhánh chính lưu dưới dạng artifact.
   - Chặn merge nếu: tỷ lệ đạt giảm quá 3 điểm phần trăm ở bất kỳ loại nào; có bất kỳ vi phạm từ cấm; độ chính xác
     truy hồi dưới 90%; tỷ lệ trả lời có trích dẫn dưới 95% (bốn chỉ số của Module 3).
   - Đánh giá các tầng đám mây chỉ chạy thủ công (workflow_dispatch) với khoá của môi trường thử, không chạy mỗi PR.
4. Bước trien-khai: nhánh chính -> helm upgrade môi trường thử tự động; môi trường thật cần phê duyệt thủ công của
   người có thẩm quyền; helm upgrade --atomic để tự quay lui khi pod không Ready.
5. scripts/chay_thu_k3d.sh: một lệnh dựng cụm k3d (cổng như PROMPT 45), import image, cài chart với values-k3d.yaml,
   nạp tài liệu mẫu data/mau/, chạy smoke test (token lấy bằng scripts/lay_token_thu.py, gửi một câu hỏi, nhận trích
   dẫn), in kết quả, rồi xoá cụm nếu có --xoa. Chạy được trong Git Bash trên Windows: không dùng sudo, dùng
   python thay cho python3, kiểm trước Docker Desktop đang chạy và Ollama nghe ở cổng 11434.
6. docs/quy-trinh-phat-hanh.md: luồng từ PR tới môi trường thật, ai phê duyệt, cách quay lui bằng helm rollback.
7. Cập nhật AGENTS.md: xoá "Kubernetes" khỏi mục "Không làm"; thêm quy tắc "đổi lời nhắc hoặc model phải qua cổng đánh giá".
   Cập nhật README và CHANGELOG.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. bash scripts/chay_thu_k3d.sh --xoa -> kỳ vọng: smoke test đạt, cụm bị xoá sau khi xong.
2. Chạy thử workflow cục bộ bằng act (nếu có; Windows: winget install nektos.act) cho bước kiem-tra -> kỳ vọng: đạt.
3. Tạo nhánh thử sửa prompts/he_thong.md cho câu trả lời luôn chen tiếng Anh, chạy bước danh-gia -> kỳ vọng: pipeline báo CHẶN.
4. grep -rn "OPENAI_API_KEY\|ANTHROPIC_API_KEY" .github/workflows -> kỳ vọng: chỉ xuất hiện trong job workflow_dispatch.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Pipeline 4 bước: kiem-tra, build, danh-gia, trien-khai
- Cổng đánh giá chặn khi tỷ lệ đạt giảm, có từ cấm, hoặc hai chỉ số RAG dưới ngưỡng
- Môi trường thật cần phê duyệt thủ công; helm upgrade --atomic
- scripts/chay_thu_k3d.sh một lệnh; AGENTS.md, README, CHANGELOG đã cập nhật

**Tự đánh giá**

```danhgia
bash scripts/chay_thu_k3d.sh --xoa                         # kỳ vọng: smoke test đạt, cụm bị xoá
act -j kiem-tra                                            # kỳ vọng: đạt (nếu cài act)
grep -rn "ANTHROPIC_API_KEY" .github/workflows             # kỳ vọng: chỉ trong job workflow_dispatch
```

```meo
Cố ý làm hỏng một lời nhắc rồi xem pipeline có chặn lại không. Đây là cách chắc chắn nhất để biết cổng đánh giá đang hoạt động, vì một cổng chưa từng chặn thay đổi nào thì chưa có bằng chứng là nó chạy đúng.
```

## Giai đoạn 11: Tinh chỉnh model

Mở workspace hybrid-assistant-chatbot trong Antigravity, chọn Editor View. Chuẩn bị một máy GPU NVIDIA (6-24GB tuỳ hồ sơ), tách khỏi máy đang phục vụ người dùng; bảo đảm thẻ git giai-doan-10 đã có và bộ eval Giai đoạn 5, Giai đoạn 6 đang chạy ổn định. Trên Windows, chạy mọi lệnh tự đánh giá trong Git Bash ở gốc repo, sau khi nạp biến môi trường: `set -a && source .env && set +a && export MSYS_NO_PATHCONV=1` (biến cuối để Git Bash không đổi đường dẫn dạng /api/... thành đường dẫn Windows). Lệnh `docker compose exec` luôn kèm `-T` để không lỗi "the input device is not a TTY".

**Trên laptop (RTX A4000 Laptop 8 GB, hồ sơ gpu8).** Huấn luyện chạy trong container qua Docker Desktop WSL2 với --gpus all (không cài Unsloth trực tiếp trên Windows). Demo trên laptop: model 2B, nạp 4-bit, batch 1, gradient checkpointing, max_seq_len 1024, tập dữ liệu vài trăm mẫu, 1 epoch (model 4B chạy được nhưng chậm hơn). Model 7-9B chỉ tinh chỉnh trên GPU từ 16 GB. Trước khi huấn luyện phải dừng Ollama/LM Studio và vLLM để giải phóng VRAM (bash scripts/doi_bo_chay.sh dung). Thời gian ước lượng cho demo khoảng 300 mẫu, 1 epoch, model 2B: 15-30 phút; đo thật ở lần chạy --so-buoc 20. Phần dành cho máy chủ GPU (model 7-9B, vLLM phục vụ LoRA) đánh dấu CHỈ TRÊN MÁY CHỦ GPU, không bắt buộc tự đánh giá trên laptop. Chạy khi laptop cắm sạc và đặt chế độ hiệu năng cao, vì GPU laptop bị hạ xung khi dùng pin.

**Mục tiêu giai đoạn.** Tinh chỉnh một model local nhỏ để trả lời đúng văn phong và định dạng của doanh nghiệp: xưng hô, cách trình bày số tiền, kWh, thời gian, cấu trúc câu trả lời. Không dạy model nội dung quy định, vì nội dung phải đến từ RAG để truy nguyên và cập nhật được (Module 3).

| LÀM GÌ | CHƯA LÀM GÌ |
| --- | --- |
| Nguyên tắc và tập dữ liệu văn phong từ hội thoại đã che, có đồng ý, có người chấm | Tiền huấn luyện model từ đầu → ngoài phạm vi tài liệu |
| QLoRA bằng Unsloth/PEFT theo hồ sơ GPU 6-24GB | Huấn luyện đa nút, nhiều máy → ngoài phạm vi tài liệu |
| Container huấn luyện tách riêng khỏi hệ thống phục vụ | Dạy model nội dung quy định, số liệu nghiệp vụ → ngoài phạm vi tài liệu |
| Cổng đánh giá không hồi quy so với model gốc | Học tăng cường từ phản hồi người dùng (RLHF/DPO) → ngoài phạm vi tài liệu |
| Xuất GGUF cho Ollama hoặc LoRA adapter cho vLLM | Tinh chỉnh model đám mây qua API nhà cung cấp → ngoài phạm vi tài liệu |
| Đăng ký thành bậc trong models.yaml, triển khai dần, quay lui | |

**Điều kiện hoàn thành**

- Có tập dữ liệu văn phong tối thiểu 300 mẫu đạt, đã che dữ liệu cá nhân, mỗi mẫu có người chấm và nguồn đồng ý.
- Model tinh chỉnh vượt model gốc ở nhóm định dạng và văn phong, không giảm quá 2 điểm phần trăm ở mọi nhóm khác và ở bộ RAG.
- Model tinh chỉnh chạy được như một bậc trong models.yaml, bật cho một phần người dùng, quay lui bằng một thay đổi cấu hình.
- Phát hành phiên bản `2.3.0` theo `.agents/rules/versioning.md`: nâng số ở backend/pyproject.toml và frontend/package.json, ghi CHANGELOG.md, gắn thẻ `git tag v2.3.0` và `git tag giai-doan-11` trên cùng commit

### PROMPT 50. Nguyên tắc tinh chỉnh và phạm vi dữ liệu

**Chế độ:** Editor View · **Đọc Plan:** Không

**Mục tiêu.** Viết rõ điều được và không được dạy model trước khi thu thập mẫu dữ liệu đầu tiên. Tệp nguyên tắc này đóng vai trò như AGENTS.md ở Giai đoạn 1: mọi prompt sau của giai đoạn đều dựa vào nó.

```prompt
Đọc AGENTS.md trước. Tạo training/NGUYEN_TAC.md và cập nhật AGENTS.md. Chưa viết mã huấn luyện.

training/NGUYEN_TAC.md gồm các mục sau, viết tiếng Việt:
1. Mục đích: tinh chỉnh VĂN PHONG và ĐỊNH DẠNG đầu ra của trợ lý nội bộ doanh nghiệp kinh doanh điện năng: xưng
   "Trợ lý nội bộ", gọi "Anh/Chị"; số tiền dạng 1.450.000 đ; điện năng dạng 320 kWh; thời gian dd/mm/yyyy - HH:mm;
   cấu trúc câu trả lời (tóm tắt một câu, các bước đánh số, nguồn ở cuối); cách nói "không đủ căn cứ"; cách hướng dẫn
   liên hệ bộ phận phụ trách khi vượt thẩm quyền.
2. Điều CẤM dạy, kèm lý do từ Module 3: nội dung quy định, biểu giá, khoảng cách an toàn, thời hạn thủ tục, số hiệu văn bản,
   bất kỳ con số nghiệp vụ nào. Lý do: khi văn bản bị thay thế, kiến thức cũ nằm trong trọng số và không gỡ ra được; nội
   dung phải đến từ RAG để trích dẫn và cập nhật bằng cách thay tệp.
3. Quy tắc với mẫu dữ liệu: phần trả lời trong mẫu được phép chứa CHỖ GIỮ CHỖ dạng <SO_TIEN>, <DIEU_KHOAN>, <NGAY> thay
   cho con số thật khi con số đó thuộc nội dung quy định; hoặc chứa ngữ cảnh RAG trong lời nhắc để mô hình học CÁCH DÙNG
   ngữ cảnh chứ không học thuộc con số.
4. Nguồn dữ liệu được phép: hội thoại trong bảng luot mà người dùng đã đồng ý (cột dong_y_huan_luyen), đã qua
   che_du_lieu_ca_nhan, được người chấm duyệt; mẫu do phòng ban nghiệp vụ tự viết. Nguồn CẤM: hội thoại chưa đồng ý,
   dữ liệu khách hàng chưa che, câu trả lời của model đám mây khi điều khoản nhà cung cấp cấm dùng đầu ra để huấn luyện
   (ghi rõ phải kiểm điều khoản từng nhà cung cấp).
5. Tiêu chí dừng: model tinh chỉnh bịa một con số quy định không có trong ngữ cảnh ở bất kỳ câu eval nào -> không triển khai.
6. Người có thẩm quyền: chủ sở hữu nghiệp vụ duyệt tập dữ liệu; Ban CNTT chịu trách nhiệm quy trình huấn luyện.
7. Giấy phép: model gốc phải cho phép tinh chỉnh và dùng thương mại (Apache-2.0 hoặc MIT); ghi tên model gốc và giấy phép.

Cập nhật AGENTS.md: xoá "Tinh chỉnh mô hình" khỏi mục "Không làm"; thêm quy tắc tuyệt đối "không đưa nội dung quy định
hay con số nghiệp vụ vào dữ liệu huấn luyện"; thêm training/ vào phạm vi làm việc.

Thêm cột dong_y_huan_luyen (bool, mặc định false) vào bảng luot bằng migration Alembic, và công tắc trên giao diện Angular
trong phần cài đặt cá nhân "Cho phép dùng hội thoại của tôi (đã che thông tin cá nhân) để cải thiện văn phong trợ lý".

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. grep -c "^## " training/NGUYEN_TAC.md -> kỳ vọng: ít nhất 7 mục.
2. grep -n "Tinh chỉnh mô hình" AGENTS.md -> kỳ vọng: không còn trong mục "Không làm"; có quy tắc cấm nội dung quy định.
3. cd backend && alembic upgrade head && docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d luot"'
   | grep dong_y_huan_luyen -> kỳ vọng: có cột, mặc định false.
4. cd backend && pytest -q && cd ../frontend && npx ng test --watch=false -> kỳ vọng: đạt.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- training/NGUYEN_TAC.md đủ 7 mục, có danh sách CẤM và tiêu chí dừng
- AGENTS.md có quy tắc tuyệt đối về dữ liệu huấn luyện
- Cột dong_y_huan_luyen mặc định false và công tắc đồng ý trên giao diện

**Tự đánh giá**

```danhgia
grep -c "^## " training/NGUYEN_TAC.md                               # kỳ vọng: >= 7
grep -n "Tinh chỉnh mô hình" AGENTS.md                              # kỳ vọng: không nằm trong mục "Không làm"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d luot"' | grep dong_y_huan_luyen   # kỳ vọng: có cột
```

```batbuoc
Mặc định KHÔNG đồng ý. Chỉ hội thoại có dong_y_huan_luyen = true mới được đưa vào tập dữ liệu. Dùng dữ liệu hội thoại của cán bộ, công nhân viên để huấn luyện mà không có đồng ý là xử lý dữ liệu cá nhân ngoài mục đích đã thông báo.
```

```meo
Tinh chỉnh văn phong trên model nhỏ thường cho lợi ích lớn nhất khi model nhỏ là bậc 2 hoặc là model chính trên máy 6-8GB như laptop RTX A4000 8 GB: đó là nơi model gốc hay lệch định dạng và chen tiếng Anh nhất.
```

### PROMPT 51. Xây tập dữ liệu văn phong

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Có tập dữ liệu nhỏ nhưng sạch: đã che, có đồng ý, có người chấm, không chứa nội dung quy định. Tập dữ liệu bẩn thì tinh chỉnh bao nhiêu cũng không bù được.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: bộ lọc con số nghiệp vụ chạy trước khi mẫu tới tay người chấm, và tập kiểm tra được tách ra trước mọi bước huấn luyện.

```prompt
Đọc AGENTS.md và training/NGUYEN_TAC.md trước. Viết công cụ tạo tập dữ liệu trong training/du_lieu/.

1. training/du_lieu/trich_xuat.py: đọc bảng luot các cặp hỏi - đáp có dong_y_huan_luyen = true, có phản hồi "hữu ích"
   hoặc chưa có phản hồi, không phải lượt từ chối lỗi. Chạy lại che_du_lieu_ca_nhan (không tin vào việc đã che trước đó).
   Ghi ra JSONL định dạng hội thoại: messages [system, user, assistant], kèm siêu dữ liệu ma_yeu_cau, phong_ban, nguon, model.
   Đọc CSDL qua DATABASE_URL trỏ 127.0.0.1:5432 (cổng dev mở bằng docker-compose.override.yml ở Giai đoạn 9). Các công cụ
   dữ liệu chạy bằng môi trường Python của backend (import app.core.bao_mat), không cần GPU; tệp tạm ghi vào
   training/tam/ (có trong .gitignore), không dùng /tmp vì Python trên Windows không hiểu đường dẫn đó.
2. training/du_lieu/loc_noi_dung.py: đánh dấu mẫu có nguy cơ chứa nội dung quy định bằng luật tất định: số tiền, số kWh cụ
   thể, số hiệu văn bản (dạng 62/2025), khoảng cách (m, kV), điều khoản. Mẫu bị đánh dấu thì thay con số bằng chỗ giữ chỗ
   (<SO_TIEN>, <DIEU_KHOAN>...) HOẶC loại bỏ; ghi lý do.
3. Mẫu viết tay: training/du_lieu/mau_viet_tay.yaml để phòng ban nghiệp vụ bổ sung, khuôn giống mẫu trích xuất; viết sẵn
   20 mẫu minh hoạ dùng dữ liệu giả cho 5 phòng ban.
4. Công cụ chấm: training/du_lieu/cham.py chạy ở dòng lệnh, hiện từng mẫu, người chấm chọn dat / sua / loai và ghi chú;
   lưu người chấm và thời điểm. Chỉ mẫu "dat" hoặc đã "sua" mới vào tập cuối.
5. Chia tập: huấn luyện 80%, kiểm định 10%, kiểm tra 10%, chia theo hoi_thoai_id để các lượt của cùng một hội thoại không
   rơi vào hai tập. Tập kiểm tra ghi một lần, có tệp băm (sha256) để phát hiện ai sửa về sau.
6. Thống kê (training/du_lieu/thong_ke.py): in số mẫu theo phòng ban, độ dài trung bình, tỷ lệ bị loại vì nội dung quy định, tỷ lệ bị loại khi chấm.
   Dưới 300 mẫu đạt thì in cảnh báo "chưa đủ dữ liệu, chưa nên huấn luyện".
7. training/du_lieu/ và mọi tệp .jsonl nằm trong .gitignore; chỉ commit mã và mẫu viết tay giả.
8. backend/tests/test_du_lieu_huan_luyen.py (pytest.ini của backend thêm thư mục gốc repo vào pythonpath để import
   training): mẫu không đồng ý không bị trích; số điện thoại sót lại bị che; câu có "62/2025" và
   "1.806 đ/kWh" bị đánh dấu; chia tập không làm một hội thoại nằm ở hai tập; tập kiểm tra bị sửa thì kiểm băm báo lỗi.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_du_lieu_huan_luyen.py -v -> kỳ vọng: tất cả đạt.
2. python training/du_lieu/trich_xuat.py --ra training/tam/tho.jsonl trên dữ liệu thử -> kỳ vọng: chỉ có hội thoại đã đồng ý.
3. grep -E "09[0-9]{8}|KH[0-9]{8}" training/tam/tho.jsonl -> kỳ vọng: không có kết quả.
4. python training/du_lieu/thong_ke.py -> kỳ vọng: in bảng thống kê và cảnh báo nếu dưới 300 mẫu.
5. git status --short | grep -c "\.jsonl" -> kỳ vọng: 0.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Trích xuất chỉ hội thoại có đồng ý, che lại dữ liệu cá nhân
- Bộ lọc tất định đánh dấu nội dung quy định trước khi chấm
- Công cụ chấm lưu người chấm; chia tập theo hội thoại; tập kiểm tra có băm
- Dữ liệu không vào Git; 5 kiểm thử đạt

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_du_lieu_huan_luyen.py -v                   # kỳ vọng: tất cả đạt
python training/du_lieu/trich_xuat.py --ra training/tam/tho.jsonl   # kỳ vọng: chỉ hội thoại đã đồng ý
grep -E "09[0-9]{8}|KH[0-9]{8}" training/tam/tho.jsonl       # kỳ vọng: không có kết quả
git status --short | grep -c "\.jsonl"                       # kỳ vọng: 0
```

```batbuoc
Tập kiểm tra được cắt ra và khoá bằng băm TRƯỚC khi huấn luyện lần đầu, và không bao giờ dùng để chọn tham số. Dùng tập kiểm tra để chỉnh tham số thì con số cuối cùng chỉ đo mức độ bạn đã khớp với chính tập đó.
```

### PROMPT 52. Huấn luyện QLoRA theo hồ sơ GPU

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Huấn luyện được trên GPU từ 6GB tới 24GB với cấu hình phù hợp từng mức, lặp lại được, ghi lại đủ để biết adapter nào sinh từ dữ liệu nào.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: model gốc được chọn đúng theo HO_SO_GPU, và mọi tham số nằm trong tệp cấu hình chứ không trong mã.

```prompt
Đọc AGENTS.md và training/NGUYEN_TAC.md trước. Viết mã huấn luyện trong training/huan_luyen/.

1. training/cau_hinh/qlora.yaml, một khối cho mỗi hồ sơ GPU:
   - gpu6, gpu8 (gồm laptop RTX A4000 8 GB): model gốc 2B hoặc 4B (cùng dòng với bậc local tương ứng trong models.yaml,
     bản gốc chưa lượng tử), nạp 4-bit, lora_r 16, max_seq_len 1024 (gpu6) hoặc 2048 (gpu8), batch 1,
     gradient_accumulation 16, gradient_checkpointing bật, optimizer paged_adamw_8bit. KHÔNG cho phép model 7–9B ở hai
     hồ sơ này; chay.py từ chối với thông điệp "model 7–9B cần GPU từ 16 GB".
   - gpu12: model ≤4B với max_seq_len 4096 (7–9B chỉ khi có GPU từ 16 GB).
   - gpu16, gpu24: model 7–9B, lora_r 16–32, max_seq_len 4096.
   - Chung: learning_rate, số epoch (1–3), warmup, seed cố định, chỉ huấn luyện trên phần trả lời của assistant.
2. training/huan_luyen/chay.py dùng Unsloth (ưu tiên, tiết kiệm VRAM) hoặc Transformers + PEFT + TRL (dự phòng khi
   Unsloth không hỗ trợ model), chọn bằng cấu hình. Thư viện nặng (torch, unsloth, peft, trl) chỉ import bên trong hàm
   huấn luyện, để chế độ khô --kho và kiểm thử chạy được bằng môi trường Python của backend trên Windows không cần GPU. Hỏi trước khi thêm thư viện; ghim phiên bản trong training/requirements.txt,
   tách khỏi requirements của backend.
3. Mỗi lần chạy tạo thư mục training/ket_qua/<ngay>_<model_goc>_<ho_so>/ chứa: adapter, bản sao cấu hình, sha256 của ba
   tập dữ liệu, commit git, đường cong loss, VRAM đỉnh đo được, thời gian huấn luyện.
4. Dừng sớm theo loss của tập kiểm định; lưu checkpoint tốt nhất theo tập kiểm định, KHÔNG theo tập kiểm tra.
5. Kiểm trước khi chạy: đo VRAM trống, so với ước lượng của hồ sơ; không đủ thì dừng với thông điệp gợi ý hồ sơ nhỏ hơn.
   Không chạy khi tập huấn luyện dưới 300 mẫu (trừ khi có cờ --thu-nghiem, và kết quả khi đó bị đánh dấu không được triển khai).
6. Không bao giờ chạy trên máy đang phục vụ người dùng: nếu phát hiện Ollama/vLLM đang giữ model trên cùng GPU (đọc
   nvidia-smi --query-compute-apps) thì dừng và báo, gợi ý chạy bash scripts/doi_bo_chay.sh dung.
   Thêm nhánh dung vào scripts/doi_bo_chay.sh (PROMPT 44): dừng cả Ollama/LM Studio và vllm.
7. backend/tests/test_huan_luyen.py (không cần GPU): chọn đúng khối cấu hình theo hồ sơ; từ chối tập dưới 300 mẫu; thư mục kết quả
   có đủ 6 tệp siêu dữ liệu (dùng chế độ khô --kho chỉ tạo cấu trúc, không huấn luyện).

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_huan_luyen.py -v -> kỳ vọng: tất cả đạt, không cần GPU.
2. python training/huan_luyen/chay.py --ho-so gpu8 --kho -> kỳ vọng: in cấu hình được chọn và ước lượng VRAM, tạo thư mục kết quả rỗng có siêu dữ liệu.
3. Trên máy GPU (laptop: sau PROMPT 53, chạy trong container): bash scripts/doi_bo_chay.sh dung && bash
   scripts/huan_luyen.sh huan-luyen HO_SO=gpu8 THU_NGHIEM=1 SO_BUOC=20 -> kỳ vọng: loss giảm, VRAM đỉnh dưới 7,5 GB,
   in thời gian mỗi bước để ước lượng tổng thời gian.
4. grep -rn "learning_rate\s*=" training/huan_luyen -> kỳ vọng: không có giá trị ghi cứng.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- qlora.yaml có đủ 5 hồ sơ gpu6 tới gpu24, mọi tham số ở cấu hình
- Mỗi lần chạy lưu adapter kèm băm dữ liệu, commit, loss, VRAM đỉnh
- Chọn checkpoint theo tập kiểm định; từ chối dữ liệu dưới 300 mẫu
- Không chạy chung GPU với hệ thống phục vụ; kiểm thử chạy không cần GPU

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_huan_luyen.py -v                                   # kỳ vọng: tất cả đạt
python training/huan_luyen/chay.py --ho-so gpu8 --kho                # kỳ vọng: in cấu hình, ước lượng VRAM
grep -rn "learning_rate\s*=" training/huan_luyen                     # kỳ vọng: không có kết quả
```

```meo
Trên GPU 6-8GB, giảm max_seq_len là cách tiết kiệm VRAM hiệu quả nhất, vì dữ liệu văn phong chủ yếu là câu trả lời ngắn. Kiểm độ dài thực tế của tập dữ liệu trước khi đặt con số này.
```

### PROMPT 53. Container huấn luyện tách riêng

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Môi trường huấn luyện dựng lại được trên bất kỳ máy GPU nào, không lẫn thư viện với hệ thống phục vụ, và không có đường ra Internet khi đang đọc dữ liệu nội bộ.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: container huấn luyện không gắn vào mạng của docker-compose chính và không có quyền đọc database thật.

```prompt
Đọc AGENTS.md trước. Đóng gói huấn luyện thành container riêng.

1. training/Dockerfile: image nền CUDA có ghim phiên bản (khớp phiên bản PyTorch trong training/requirements.txt),
   người dùng không phải root uid 10001, cài training/requirements.txt, sao chép training/ (không sao chép backend/).
2. training/docker-compose.huan-luyen.yml, TÁCH khỏi docker-compose.yml chính:
   - Một dịch vụ huan-luyen xin GPU bằng deploy.resources.reservations.devices (driver nvidia, count 1) - cú pháp chạy
     được trên Docker Desktop WSL2 của Windows lẫn Linux có NVIDIA Container Toolkit; shm_size 8gb.
   - Gắn thư mục dữ liệu chỉ đọc (training/du_lieu/ đã chuẩn bị ở PROMPT 51), thư mục kết quả ghi được, và volume có
     tên cho bộ nhớ đệm model gốc (volume trong WSL2 nhanh hơn nhiều so với gắn thư mục ổ C: của Windows).
   - Mạng: network_mode none khi huấn luyện. Việc tải trọng số model gốc là bước riêng (lệnh tai_model_goc) chạy trước,
     có mạng, không gắn dữ liệu.
   - KHÔNG có biến DATABASE_URL hay khoá API nào.
3. scripts/huan_luyen.sh (bash, chạy được trong Git Bash; không dùng Makefile vì Windows thường không có make):
   tai-model-goc, huan-luyen HO_SO=gpu8 [KHO=1] [THU_NGHIEM=1 SO_BUOC=20], danh-gia, xuat (PROMPT 54, 55 sẽ dùng).
   Lệnh huan-luyen tự gọi scripts/doi_bo_chay.sh dung trước khi chạy.
4. Ghi vào thư mục kết quả tệp moi_truong.txt: phiên bản CUDA, driver, PyTorch, Unsloth/PEFT, image digest.
5. Trên Kubernetes (tuỳ chọn): deploy/helm/.../templates/job-huan-luyen.yaml, tắt mặc định, chạy trên nút GPU có nhãn
   dành riêng huấn luyện, NetworkPolicy cấm mọi egress, PVC cho dữ liệu và kết quả.
6. docs/huan-luyen.md: quy trình chạy từ đầu tới cuối trên một máy GPU, và cách xoá sạch dữ liệu huấn luyện sau khi xong.
7. Quét Trivy image huấn luyện bằng scripts/quet_trivy.sh.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. docker build -t tro-ly-huan-luyen training/ -> kỳ vọng: build thành công.
2. docker run --rm tro-ly-huan-luyen id -u -> kỳ vọng: 10001.
3. docker compose -f training/docker-compose.huan-luyen.yml config | grep -n "network_mode" -> kỳ vọng: none cho dịch vụ huan-luyen.
4. docker compose -f training/docker-compose.huan-luyen.yml config | grep -cE "DATABASE_URL|API_KEY" -> kỳ vọng: 0.
5. docker run --rm --gpus all tro-ly-huan-luyen nvidia-smi -> kỳ vọng: thấy RTX A4000 Laptop GPU (WSL2 chuyển GPU được).
6. bash scripts/huan_luyen.sh huan-luyen HO_SO=gpu8 KHO=1 -> kỳ vọng: chạy chế độ khô trong container, tạo moi_truong.txt.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Image huấn luyện riêng, không root, ghim phiên bản CUDA và thư viện
- Compose huấn luyện tách riêng, network_mode none, dữ liệu chỉ đọc
- Không có chuỗi kết nối database hay khoá API trong môi trường huấn luyện
- Job Kubernetes tuỳ chọn cấm egress; docs/huan-luyen.md

**Tự đánh giá**

```danhgia
docker build -t tro-ly-huan-luyen training/                                              # kỳ vọng: thành công
docker run --rm tro-ly-huan-luyen id -u                                                  # kỳ vọng: 10001
docker compose -f training/docker-compose.huan-luyen.yml config | grep -n network_mode   # kỳ vọng: none
docker compose -f training/docker-compose.huan-luyen.yml config | grep -cE "DATABASE_URL|API_KEY"   # kỳ vọng: 0
docker run --rm --gpus all tro-ly-huan-luyen nvidia-smi                                  # kỳ vọng: thấy GPU
```

```batbuoc
Container huấn luyện không bao giờ có quyền đọc database thật. Dữ liệu vào huấn luyện chỉ là tệp đã trích xuất, đã che và đã chấm ở PROMPT 51. Nhờ ranh giới này, bạn chứng minh được chính xác model đã được huấn luyện trên dữ liệu nào.
```

### PROMPT 54. Cổng đánh giá không hồi quy

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Chỉ triển khai model tinh chỉnh khi nó tốt hơn ở đúng thứ cần tốt hơn, và không tệ hơn ở mọi thứ khác, đặc biệt là không bịa con số quy định.

**Làm trước.** Đọc Implementation Plan. Kiểm một điều: so sánh chạy trên cùng bộ câu hỏi, cùng lời nhắc, cùng số lần lặp cho model gốc và model tinh chỉnh.

```prompt
Đọc AGENTS.md và training/NGUYEN_TAC.md trước. Viết training/danh_gia/cong_danh_gia.py.

1. Phục vụ tạm model tinh chỉnh để đánh giá: nạp adapter vào vLLM (--enable-lora) hoặc tạo model Ollama tạm từ GGUF
   (PROMPT 55 sẽ chuẩn hoá bước xuất; ở đây cho phép gọi hàm xuất nội bộ). Trên GPU 8 GB, model gốc và model tinh
   chỉnh chạy TUẦN TỰ qua Ollama (không nạp cùng lúc): đánh giá xong model này mới ollama stop rồi nạp model kia.
2. Chạy trên CẢ HAI model, mỗi câu N = 3 lần, cùng prompts/he_thong.md:
   a) Tập kiểm tra văn phong (từ PROMPT 51): chấm tất định định dạng số tiền, kWh, thời gian, xưng hô "Anh/Chị", tỷ lệ ký tự
      tiếng Việt; phần còn lại chấm bằng model bậc 1 gốc với prompts/cham.md. Chạy qua app.eval.runner --tang local1
      (model gốc) và một tầng tạm cho model tinh chỉnh.
   b) eval/bo_cau_hoi.yaml (Giai đoạn 5) đủ năm loại.
   c) eval/bo_cau_hoi_rag.yaml (Giai đoạn 6) với prompts/he_thong_rag.md: bốn chỉ số - độ chính xác truy hồi, tỷ lệ có
      trích dẫn, tỷ lệ đủ từ bắt buộc, số vi phạm từ cấm; và eval/bo_cau_hoi_cong_cu.yaml (Giai đoạn 7) nếu model được
      khai ho_tro_cong_cu.
   d) Bộ kiểm "bịa con số": 30 câu hỏi về quy định mà ngữ cảnh RAG KHÔNG chứa con số; đạt khi model nói không đủ căn cứ,
      trượt khi trả ra một con số cụ thể.
3. Luật quyết định, ghi trong training/cau_hinh/cong.yaml (không ghi cứng):
   - Văn phong: tinh chỉnh phải cao hơn gốc ít nhất 10 điểm phần trăm.
   - Mọi loại khác và bốn chỉ số RAG: không thấp hơn gốc quá 2 điểm phần trăm.
   - Vi phạm từ cấm: 0. Bịa con số: 0 lần trên tất cả các lần chạy. Một lần bịa là trượt, không cân nhắc.
   - Tốc độ tok/s không giảm quá 10%.
4. In bảng so sánh hai cột (gốc | tinh chỉnh) theo từng nhóm, đánh dấu dòng trượt; ghi training/ket_qua/<lan_chay>/cong.json
   kèm chi tiết từng câu; mã thoát 0 khi ĐẠT, 1 khi TRƯỢT.
5. Đẩy kết quả thành dataset run trong Langfuse (Giai đoạn 9) gắn tên adapter.
6. tests/test_cong_danh_gia.py với kết quả giả lập: một lần bịa con số -> trượt dù mọi thứ khác tốt; văn phong tăng
   8 điểm -> trượt; RAG giảm 3 điểm -> trượt; đủ điều kiện -> đạt.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_cong_danh_gia.py -v -> kỳ vọng: 4 kiểm thử đạt.
2. python training/danh_gia/cong_danh_gia.py --adapter <thu_muc_ket_qua> --lan 3; echo $? -> kỳ vọng: in bảng hai cột, mã thoát khớp kết luận.
3. Kiểm training/ket_qua/<lan_chay>/cong.json -> kỳ vọng: có chi tiết từng câu và mục bia_con_so.
4. grep -rn "0.02\|10.0" training/danh_gia/*.py -> kỳ vọng: ngưỡng không ghi cứng trong mã.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- So sánh gốc và tinh chỉnh trên 4 bộ câu hỏi, N = 3 lần, cùng lời nhắc
- Bộ kiểm "bịa con số" 30 câu; một lần bịa là trượt
- Ngưỡng nằm trong cong.yaml; mã thoát 0/1; kết quả lên Langfuse
- 4 kiểm thử luật quyết định đạt

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_cong_danh_gia.py -v                                             # kỳ vọng: 4 kiểm thử đạt
python training/danh_gia/cong_danh_gia.py --adapter <thu_muc_ket_qua> --lan 3; echo $?   # kỳ vọng: bảng hai cột, mã thoát đúng
```

```batbuoc
Bịa một con số quy định là trượt ngay, không lấy trung bình với điểm văn phong. Một câu trả lời trình bày đẹp hơn mà nói sai khoảng cách an toàn hay biểu giá thì gây hại nhiều hơn lợi ích văn phong mang lại.
```

### PROMPT 55. Xuất model, đăng ký bậc và triển khai dần

**Chế độ:** Editor View · **Đọc Plan:** Có

**Mục tiêu.** Đưa model đã qua cổng đánh giá vào chuỗi định tuyến như một bậc bình thường, bật cho một phần người dùng trước, và quay lui chỉ bằng một thay đổi cấu hình.

**Làm trước.** Đọc Implementation Plan. Kiểm hai điều: không thể đăng ký một adapter chưa có cong.json ĐẠT, và quay lui không cần build lại image.

```prompt
Đọc AGENTS.md trước. Viết bước xuất và triển khai model tinh chỉnh.

1. training/xuat/xuat.py với hai đích, chọn bằng tham số:
   - ollama: gộp adapter vào model gốc, chuyển sang GGUF (chạy trong container huấn luyện, dùng llama.cpp ghim phiên bản;
     gpu8 dùng q8_0 cho model 2B/4B như hồ sơ local), sinh Modelfile (FROM tệp
     GGUF, TEMPLATE đúng của dòng model gốc, PARAMETER num_ctx theo bậc), rồi ollama create tro-ly-van-phong:<ngay>-<ho_so>-q4_K_M.
   - vllm: giữ LoRA adapter riêng, sinh đoạn cấu hình --lora-modules tro-ly-van-phong=<duong_dan> cho Helm values.
   - TỪ CHỐI xuất khi thư mục kết quả không có cong.json với ket_luan = DAT.
2. Tên model luôn ghi đầy đủ ngày, hồ sơ, lượng tử (quy tắc 6 của AGENTS.md); ghi vào training/so_dang_ky.yaml:
   ten, model_goc, giay_phep, adapter, sha256 dữ liệu, cong.json, người duyệt, ngày.
3. config/models.yaml: cho phép một bậc có trường thu_nghiem gồm model_thay_the và ty_le_nguoi_dung (0–100).
   app/llm/chinh_sach.py: người dùng rơi vào nhóm thử theo băm ổn định của nguoi_id (một người luôn cùng nhóm);
   KetQuaGoi và sự kiện bat_dau ghi model thực dùng; bảng quản trị hiển thị so sánh tỷ lệ "hữu ích" giữa hai nhóm.
4. Kế hoạch triển khai dần trong docs/trien-khai-model-tinh-chinh.md: 5% trong 3 ngày -> 25% -> 100%; điều kiện tăng:
   tỷ lệ hữu ích không thấp hơn nhóm gốc, không có báo cáo bịa con số; người có thẩm quyền quyết định từng bước.
5. Quay lui: đặt ty_le_nguoi_dung = 0 (hoặc xoá khối thu_nghiem) và tải lại cấu hình không cần build image; viết
   scripts/quay_lui_model.py thực hiện và ghi nhật ký kiểm toán.
6. Sự kiện bat_dau và huy hiệu trên giao diện Angular hiện đúng tên model đã trả lời, theo nguyên tắc người dùng có quyền
   biết câu trả lời do model nào sinh ra; nhãn "Nội dung do AI tạo" giữ nguyên.
7. Cập nhật AGENTS.md (quy tắc: chỉ model có trong training/so_dang_ky.yaml mới được khai trong models.yaml), README mục
   "Tinh chỉnh mô hình", CHANGELOG.
8. tests/test_trien_khai_tinh_chinh.py: xuất bị từ chối khi không có cong.json ĐẠT; cùng một nguoi_id luôn cùng nhóm;
   ty_le 0 thì không ai dùng model mới; model chưa có trong sổ đăng ký thì config từ chối khởi động.

Đọc Implementation Plan cho tôi duyệt trước khi ghi tệp.

TỰ ĐÁNH GIÁ - làm xong thì tự chạy các bước sau, KHÔNG báo hoàn thành trước khi chạy:
1. cd backend && pytest tests/test_trien_khai_tinh_chinh.py -v -> kỳ vọng: tất cả đạt.
2. python training/xuat/xuat.py --dich ollama --ket-qua <thu_muc_truot> -> kỳ vọng: bị từ chối với thông điệp rõ.
3. Với thư mục ĐẠT: bash scripts/doi_bo_chay.sh ollama && python training/xuat/xuat.py --dich ollama --ket-qua <thu_muc_dat>
   && ollama list -> kỳ vọng: có tro-ly-van-phong:<ngay>-<ho_so>-<luong_tu>.
4. Đặt ty_le_nguoi_dung 5; kịch bản kiểm thử tạo 40 nguoi_id giả và gọi chinh_sach trực tiếp (không cần 40 tài khoản
   Keycloak) -> kỳ vọng: khoảng 2 nguoi_id rơi vào nhóm model mới; một câu hỏi thật qua /chat/stream của người thuộc
   nhóm thử có sự kiện bat_dau ghi đúng model.
5. python scripts/quay_lui_model.py && gửi lại -> kỳ vọng: không tài khoản nào dùng model mới, có dòng kiểm toán.
Trả về bảng: Hạng mục | Lệnh | Kết quả | ĐẠT/CHƯA ĐẠT. Nếu có dòng CHƯA ĐẠT: tự sửa và chạy lại, tối đa 2 vòng; sau
đó vẫn chưa đạt thì dừng lại, nêu nguyên nhân, không báo hoàn thành.
```

**Agent phải trả về**

- Xuất được sang Ollama (GGUF + Modelfile) và vLLM (LoRA adapter); từ chối khi cổng đánh giá chưa ĐẠT
- Sổ đăng ký model có model gốc, giấy phép, băm dữ liệu, người duyệt
- Thử nghiệm theo tỷ lệ người dùng, nhóm ổn định theo nguoi_id
- Quay lui bằng cấu hình, có kiểm toán; AGENTS.md, README, CHANGELOG đã cập nhật

**Tự đánh giá**

```danhgia
cd backend && pytest tests/test_trien_khai_tinh_chinh.py -v                                      # kỳ vọng: tất cả đạt
python training/xuat/xuat.py --dich ollama --ket-qua <thu_muc_truot>               # kỳ vọng: bị từ chối
ollama list | grep tro-ly-van-phong                                                # kỳ vọng: có model mới, tên đủ ngày-hồ sơ-lượng tử
python scripts/quay_lui_model.py                                                   # kỳ vọng: tỷ lệ về 0, có dòng kiểm toán
```

```batbuoc
Model tinh chỉnh chỉ được bật khi có đủ ba thứ: cong.json ĐẠT, mục trong sổ đăng ký có người duyệt, và đường quay lui đã được thử. Thiếu một trong ba thì giữ model gốc.
```

```meo
Đo tỷ lệ "hữu ích" giữa hai nhóm ít nhất vài trăm lượt trước khi tăng tỷ lệ. Với vài chục lượt, chênh lệch nhỏ phần lớn là nhiễu; hãy để chủ sở hữu nghiệp vụ đọc thêm một mẫu câu trả lời của cả hai nhóm trước khi quyết định.
```
