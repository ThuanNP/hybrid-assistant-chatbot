# Ứng dụng Frontend Trợ lý AI Nội bộ (hybrid-assistant-chatbot-frontend)

Ứng dụng web Single Page Application (SPA) xây dựng trên nền tảng **Angular 22** phục vụ cán bộ, công nhân viên ngành Điện lực tương tác với hệ thống Trợ lý AI nội bộ.

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
│   │   ├── _tokens.scss         # Khối :root chép nguyên văn Mục 9 của DESIGN.md
│   │   ├── _typography.scss     # Thang chữ phân cấp theo Mục 4.2 DESIGN.md
│   │   └── _base.scss           # Reset CSS và thiết lập toàn cục
│   ├── styles.scss              # Điểm nhúng toàn bộ phông chữ cục bộ và styles
│   └── app/
│       ├── core/                # Dịch vụ nền tảng: api.service.ts, sse.service.ts, mo-hinh.ts, cau-hinh.ts
│       ├── features/
│       │   ├── chat/            # Giao diện khung chat và bong bóng tin nhắn
│       │   └── hoi-thoai/       # Quản lý danh sách lịch sử hội thoại
│       ├── shared/
│       │   ├── huy-hieu-mo-hinh/# Component hiển thị huy hiệu đo lường mô hình AI
│       │   └── dong-thong-bao/  # Component thanh thông báo / alert
│       ├── app.ts               # App Shell component với Signals và Responsive Drawer
│       ├── app.html             # Khung Header 64px, Sidebar 240px/72px, Main area
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

Ứng dụng khởi chạy tại <http://localhost:4200>. Các yêu cầu tới `/api`, `/health`, `/ready` sẽ tự động chuyển tiếp tới `http://localhost:8000`.

### Biên dịch dự án (Production Build)

```bash
npx ng build
```

Bản dựng hoàn chỉnh sẽ được lưu tại thư mục `dist/`.

### Chạy kiểm thử đơn vị

```bash
npx ng test --watch=false
```
