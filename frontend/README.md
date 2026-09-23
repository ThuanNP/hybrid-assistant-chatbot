# Ứng dụng Frontend Trợ lý AI Nội bộ (hybrid-assistant-chatbot-frontend)

Ứng dụng web Single Page Application (SPA) xây dựng trên nền tảng **Angular 22** phục vụ cán bộ,
công nhân viên ngành Điện lực tương tác với hệ thống Trợ lý AI nội bộ.

## 1. Thông số kỹ thuật

| Thông số | Phiên bản / Cấu hình |
| :--- | :--- |
| **Phiên bản ứng dụng** | `0.3.0` (đồng bộ với `backend/pyproject.toml`) |
| **Angular CLI / Core** | `22.1.8` |
| **Node.js** | `v24.19.0` (npm `11.17.0`) |
| **Change Detection** | Zoneless (`provideZonelessChangeDetection()`) |
| **Kiến trúc Component** | Standalone Components & Angular Signals |
| **Bộ chạy kiểm thử** | Vitest (`@angular/build:unit-test`) |
| **Ngôn ngữ định dạng** | SCSS với Design Tokens chuẩn hóa từ `DESIGN.md` |
| **Phông chữ tự host** | `@fontsource/lexend` (400, 500, 600, 700), `@fontsource/source-code-pro` (400) |

## 2. Cấu trúc thư mục

```text
frontend/
├── proxy.conf.json              # Cấu hình proxy cho /api, /health, /ready tới http://localhost:8000
├── THIRD_PARTY.md               # Ghi nhận giấy phép SIL OFL của các bộ phông chữ cục bộ
├── src/
│   ├── environments/            # Cấu hình apiGoc = "/api/v1"
│   ├── styles/
│   │   ├── _tokens.scss         # Khối :root chép từ mục 12 của DESIGN.md
│   │   ├── _typography.scss     # Thang chữ phân cấp theo mục 4.2 DESIGN.md
│   │   └── _base.scss           # Reset CSS và thiết lập toàn cục
│   ├── styles.scss              # Điểm nhúng toàn bộ phông chữ cục bộ và styles
│   └── app/
│       ├── core/                # api.service, sse.service, mo-hinh, cau-hinh và trạng thái dùng chung
│       │                        # (kho-hoi-thoai, bo-cuc-trang, thong-bao, dinh-dang, tac-vu-nhanh)
│       ├── features/
│       │   ├── trang-chu/       # Trang chủ: bốn thẻ KPI, tác vụ nhanh, ô hỏi, hội thoại gần đây
│       │   ├── chat/            # Màn Trò chuyện (/tro-chuyen/moi, /tro-chuyen/:id)
│       │   └── hoi-thoai/       # Màn Lịch sử hội thoại: tìm, lọc, sắp xếp ở máy chủ
│       ├── shared/
│       │   ├── thanh-dau-trang/ # Thanh đầu trang 60px: breadcrumb, trạng thái, thông báo
│       │   ├── o-soan-cau-hoi/  # Ô soạn câu hỏi dùng chung
│       │   ├── huy-hieu-mo-hinh/# Huy hiệu đo lường mô hình, cảnh báo theo cờ ha_cap
│       │   └── bieu-tuong/      # Bộ biểu tượng SVG nội tuyến
│       ├── app.ts               # App Shell component với Signals và Responsive Drawer
│       ├── app.html             # Sidebar 214px/72px, thân trang, footer 32px
│       ├── app.scss             # Định kiểu App Shell bằng Design Tokens
│       └── app.spec.ts          # Bộ kiểm thử đơn vị cho App Shell
```

## 3. Khởi chạy và kiểm thử

### Cài đặt phụ thuộc

```bash
cd frontend
npm install
```

### Khởi chạy môi trường phát triển (kèm proxy tới backend)

```bash
npx ng serve
```

Ứng dụng khởi chạy tại <http://localhost:4200>. Các yêu cầu tới `/api`, `/health`, `/ready` sẽ tự
động chuyển tiếp tới `http://localhost:8000`.

### Biên dịch dự án (Production Build)

```bash
npx ng build
```

Bản dựng hoàn chỉnh sẽ được lưu tại thư mục `dist/`.

### Chạy kiểm thử đơn vị

```bash
npx ng test --watch=false
```
