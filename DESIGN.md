---
name: Trợ lý AI nội bộ
version: alpha
colors:
  primary: "#016BF8"
  primary-dark-1: "#1254B7"
  primary-dark-2: "#083C90"
  primary-dark-3: "#0C2657"
  primary-light-1: "#0498EC"
  primary-light-2: "#C3E7FE"
  primary-light-3: "#E1F7FF"
  navy-start: "#031863"
  navy-end: "#0630C9"
  success: "#00ED64"
  success-dark-1: "#00A35C"
  success-dark-2: "#00684A"
  success-dark-3: "#023430"
  success-light-1: "#71F6BA"
  success-light-2: "#C0FAE6"
  success-light-3: "#E3FCF7"
  warning: "#FFC010"
  warning-dark-2: "#944F01"
  warning-dark-3: "#4C2100"
  warning-light-2: "#FFEC9E"
  warning-light-3: "#FEF7D8"
  danger: "#DB3030"
  danger-dark-2: "#970606"
  danger-dark-3: "#5B0000"
  danger-light-1: "#FF6960"
  danger-light-2: "#FFCDC7"
  danger-light-3: "#FFEAE5"
  purple: "#B45AF2"
  purple-dark-2: "#5E0C9E"
  purple-dark-3: "#2D0B59"
  purple-light-2: "#F1D4FD"
  purple-light-3: "#F9EBFF"
  black: "#001E2B"
  white: "#FFFFFF"
  gray-dark-4: "#112733"
  gray-dark-3: "#1C2D38"
  gray-dark-2: "#3D4F58"
  gray-dark-1: "#5C6C75"
  gray-base: "#889397"
  gray-light-1: "#C1C7C6"
  gray-light-2: "#E8EDEB"
  gray-light-3: "#F9FBFA"
  canvas: "#F9FBFC"
  canvas-mobile: "#F2F7FD"
typography:
  h1:
    fontFamily: "Lexend"
    fontSize: "48px"
    fontWeight: 400
    lineHeight: "72px"
    letterSpacing: "-0.02em"
  h2:
    fontFamily: "Lexend"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: "42px"
    letterSpacing: "-0.02em"
  h3:
    fontFamily: "Lexend"
    fontSize: "24px"
    fontWeight: 500
    lineHeight: "42px"
    letterSpacing: "-0.02em"
  subtitle:
    fontFamily: "Lexend"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: "30px"
    letterSpacing: "-0.02em"
  body-2:
    fontFamily: "Lexend"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "30px"
    letterSpacing: "-0.02em"
  body-1:
    fontFamily: "Lexend"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: "24px"
    letterSpacing: "-0.02em"
  overline:
    fontFamily: "Lexend"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "22px"
    letterSpacing: "0.4px"
  disclaimer:
    fontFamily: "Lexend"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: "22px"
    letterSpacing: "0.2px"
  code-2:
    fontFamily: "Source Code Pro"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: "22px"
  code-1:
    fontFamily: "Source Code Pro"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: "22px"
spacing:
  base: "12px"
  xxs: "4px"
  xs: "6px"
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "16px"
  xxl: "20px"
  xxxl: "24px"
rounded:
  xs: "3px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
omitted:
  - components
---

# Chuẩn thiết kế giao diện Trợ lý AI nội bộ

Tài liệu chuẩn thiết kế (design system) cho giao diện web và di động của Trợ lý AI nội bộ
dành cho cán bộ, công nhân viên **Doanh nghiệp Kinh doanh Điện năng**.

| Mục | Giá trị |
| --- | --- |
| Phiên bản | 2.0 |
| Ngày cập nhật | 2026-09-23 |
| Phạm vi | Ứng dụng web (Angular), bản di động và các màn hình trợ lý ảo |
| Trạng thái | Bản nháp, chờ phê duyệt |

---

## 0. Nguyên tắc trung lập thương hiệu (bắt buộc)

Giao diện chỉ dùng khối nhận diện trung tính của sản phẩm, **không** mang nhận diện
thương hiệu của bất kỳ tổ chức thật nào:

| Không được dùng | Thay thế bằng |
| --- | --- |
| Logo, biểu tượng, tên gọi hoặc tên viết tắt của tổ chức, doanh nghiệp có thật | Khối nhận diện trung tính tại mục 2 |
| Khẩu hiệu, tên miền thư điện tử, ảnh chụp sản phẩm của tổ chức thật | Nội dung mô tả sản phẩm tự soạn |
| Họ tên, chức danh cán bộ có thật | Dữ liệu giả lập rõ ràng (`Nguyễn Văn A`, `Chuyên viên`) |
| Minh hoạ, biểu tượng của phần mềm bên thứ ba | Bộ biểu tượng nét mảnh mã nguồn mở, cùng một phong cách |

Mọi màn hình, ảnh chụp và tài liệu phát hành phải được rà soát theo bảng trên trước khi duyệt.

---

## 1. Tinh thần thiết kế

Ngôn ngữ thiết kế là **"văn phòng số tinh gọn"**: nền sáng gần trắng, thẻ trắng viền mảnh,
nhấn màu xanh dương ở tương tác chính, dải xanh thẫm chuyển sắc cho vùng nhận diện và
số liệu cỡ lớn dễ đọc lướt.

| Nguyên tắc | Biểu hiện trên giao diện |
| --- | --- |
| **Phẳng, nhiều khoảng thở** | Thẻ trắng trên nền `canvas`, viền `gray-light-2` 1px, bóng đổ rất nhẹ |
| **Nhấn màu có kiểm soát** | Xanh `primary` chỉ dùng cho nút chính, liên kết, mục đang chọn và biểu tượng tương tác |
| **Số liệu nói trước** | Chỉ số hiển thị cỡ 32px, nhãn nhỏ 13px màu xám phía trên |
| **Trạng thái bằng huy hiệu** | Mọi trạng thái công việc dùng huy hiệu nền nhạt, viền và chữ cùng tông |
| **Nhất quán web và di động** | Cùng token màu, cùng bo góc; di động thêm thanh điều hướng đáy có nút nổi trung tâm |

---

## 2. Khối nhận diện trung tính

Khối nhận diện thay cho logo, gồm hai thành phần đặt ngang, cao 36px trên web:

1. **Biểu tượng "tia chớp hội thoại"** (tệp nguồn `frontend/public/logo.svg`, lưới 28 × 28):
   - Nền: ô vuông 28px, bo góc `radius-md` (8px), chuyển sắc 135° từ `navy-start` sang `navy-end`.
   - Bong bóng trò chuyện đặc màu trắng, rộng 16px, cao 11,5px, bo góc 4px, đuôi nhọn chếch
     xuống bên trái.
   - Tia chớp đặc màu `blue-base` nằm giữa bong bóng: năng lượng đi qua lời hỏi đáp.
2. **Chữ nhận diện:** `Trợ lý nội bộ`, Lexend SemiBold 16px, màu `black` (`#001E2B`).

| Tiêu chí | Quy định |
| --- | --- |
| Vùng an toàn | Tối thiểu 8px quanh khối |
| Nền đặt | Trắng, `canvas` hoặc dải xanh thẫm (chữ chuyển sang trắng) |
| Cỡ tối thiểu | 16px (favicon); dưới cỡ này chỉ giữ nền và bong bóng |
| Favicon | `frontend/public/favicon.ico` (16, 32, 48, 64px) dựng từ `logo.svg`, kèm `logo.svg` cho trình duyệt hỗ trợ SVG |
| Dùng lại | Biểu tượng làm favicon, avatar trợ lý 28px (mục 8.1) và nút nổi di động |
| Điều cấm | Không ghép thêm tên, logo hay màu nhận diện của tổ chức thật; không đổi hình dạng hay màu của biểu tượng |

---

## 3. Hệ thống màu

### 3.1. Dải xanh chủ đạo

| Token | HEX | Vai trò |
| --- | --- | --- |
| `blue-dark-3` | `#0C2657` | Chữ trên chip xanh, liên kết trên banner thông tin |
| `blue-dark-2` | `#083C90` | Hover của viền nút chính, chữ banner thông tin, nền focus trên nền đảo |
| `blue-dark-1` | `#1254B7` | Viền và chữ nút `primaryOutline`, chữ huy hiệu xanh, ghi chú |
| `blue-base` | `#016BF8` | **Primary:** nút chính, liên kết, mục đang chọn, biểu tượng thông tin |
| `blue-light-1` | `#0498EC` | Điểm nhấn phụ trong biểu đồ |
| `blue-light-2` | `#C3E7FE` | Viền huy hiệu và banner thông tin, bóng focus của nút chính |
| `blue-light-3` | `#E1F7FF` | Nền focus, nền huy hiệu và banner thông tin |

### 3.2. Dải xanh thẫm nhận diện (gradient)

| Token | Giá trị | Ứng dụng |
| --- | --- | --- |
| `gradient-navy` | `linear-gradient(135deg, #031863, #0630C9)` | Nút nổi (FAB) di động, thẻ hồ sơ, bảng giới thiệu ở màn đăng nhập |
| `gradient-border` | `linear-gradient(135deg, #0032E9, #8FBFFA)` | Viền 1px của thẻ nằm trên nền xanh thẫm |

Nền xanh thẫm có thể phủ họa tiết hạt sáng trừu tượng, tự thiết kế, độ mờ không quá 20%.

### 3.3. Màu trạng thái

| Nhóm | Đậm 3 | Đậm 2 | Đậm 1 | Cơ sở | Nhạt 1 | Nhạt 2 | Nhạt 3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Xanh lá (thành công) | `#023430` | `#00684A` | `#00A35C` | `#00ED64` | `#71F6BA` | `#C0FAE6` | `#E3FCF7` |
| Vàng (cảnh báo) | `#4C2100` | `#944F01` | | `#FFC010` | | `#FFEC9E` | `#FEF7D8` |
| Đỏ (lỗi, nguy hiểm) | `#5B0000` | `#970606` | | `#DB3030` | `#FF6960` | `#FFCDC7` | `#FFEAE5` |
| Tím (ghi chú, mẹo) | `#2D0B59` | `#5E0C9E` | | `#B45AF2` | | `#F1D4FD` | `#F9EBFF` |

### 3.4. Dải trung tính

| Token | HEX | Ứng dụng |
| --- | --- | --- |
| `black` | `#001E2B` | Chữ chính, tiêu đề, nền đảo (inverse) |
| `gray-dark-4` | `#112733` | Nền bề mặt ở chế độ tối |
| `gray-dark-3` | `#1C2D38` | Chữ trong thẻ, hover trên nền đảo |
| `gray-dark-2` | `#3D4F58` | Biểu tượng chip xám, viền trên nền đảo |
| `gray-dark-1` | `#5C6C75` | Chữ phụ, nhãn thẻ, biểu tượng mặc định |
| `gray-base` | `#889397` | Placeholder, viền ô nhập, biểu tượng phụ, chữ vô hiệu |
| `gray-light-1` | `#C1C7C6` | Viền vô hiệu, chữ phụ trên nền đảo |
| `gray-light-2` | `#E8EDEB` | Viền thẻ, đường phân cách, nền hover, nền vô hiệu |
| `gray-light-3` | `#F9FBFA` | Nền phụ (secondary) |
| `canvas` | `#F9FBFC` | Nền tổng thể và nền sidebar trên web |
| `canvas-mobile` | `#F2F7FD` | Nền tổng thể trên di động |

### 3.5. Token ngữ nghĩa (chế độ sáng)

| Nhóm | Token | Giá trị |
| --- | --- | --- |
| Nền | `bg-primary` / `-hover` / `-focus` | `#FFFFFF` / `#E8EDEB` / `#E1F7FF` |
| Nền | `bg-secondary` / `-hover` / `-focus` | `#F9FBFA` / `#E8EDEB` / `#E1F7FF` |
| Nền | `bg-inverse` / `-hover` / `-focus` | `#001E2B` / `#1C2D38` / `#083C90` |
| Nền | `bg-info` / `bg-warning` / `bg-success` / `bg-error` | `#E1F7FF` / `#FEF7D8` / `#E3FCF7` / `#FFEAE5` |
| Nền | `bg-disabled` | `#E8EDEB` |
| Chữ | `text-primary` / `text-secondary` / `text-card` | `#001E2B` / `#5C6C75` / `#1C2D38` |
| Chữ | `text-inverse-primary` / `text-inverse-secondary` | `#FFFFFF` / `#C1C7C6` |
| Chữ | `text-link` / `text-error` / `text-disabled` | `#016BF8` / `#DB3030` / `#889397` |
| Biểu tượng | `icon-primary` / `icon-secondary` / `icon-inverse` | `#5C6C75` / `#889397` / `#FFFFFF` |
| Biểu tượng | `icon-info` / `icon-warning` / `icon-success` / `icon-error` | `#016BF8` / `#944F01` / `#00A35C` / `#DB3030` |
| Viền | `border-primary` / `border-secondary` / `border-inverse` | `#889397` / `#E8EDEB` / `#3D4F58` |
| Viền | `border-success` / `border-error` / `border-disabled` | `#00A35C` / `#DB3030` / `#C1C7C6` |

Chế độ tối dùng cùng tập token; giá trị chế độ tối sẽ được bổ sung khi triển khai giao diện
tối, chỉ đổi giá trị, không đổi tên token.

### 3.6. Độ tương phản (WCAG 2.1)

- Chữ `black` trên nền trắng: khoảng **17,4:1** (AAA).
- Chữ `gray-dark-1` trên nền trắng: khoảng **5,4:1** (AA).
- Chữ trắng trên nền `blue-base`: khoảng **4,7:1** (AA).
- Chữ `danger` trên nền trắng: khoảng **4,7:1** (AA).
- `gray-base` chỉ khoảng **3,2:1**: chỉ dùng cho placeholder, chữ vô hiệu và biểu tượng phụ.
- Nhãn nhóm menu dùng `gray-base`, không dùng `gray-light-1` (chỉ khoảng 1,7:1).
- Nền vàng `warning` luôn đi với chữ `warning-dark-2` hoặc `warning-dark-3`, không dùng chữ trắng.

---

## 4. Kiểu chữ

### 4.1. Họ phông

```css
--font-sans: "Lexend", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-mono: "Source Code Pro", "SFMono-Regular", Consolas, monospace;
```

Lexend là phông duy nhất cho toàn bộ văn bản giao diện; Source Code Pro chỉ dùng cho mã
và thông số kỹ thuật.

### 4.2. Thang chữ

| Cấp | Cỡ | Dòng | Độ đậm | Giãn chữ | Ứng dụng |
| --- | --- | --- | --- | --- | --- |
| `H1` | 48px | 72px | 400 | -2% | Tiêu đề màn đăng nhập, trang giới thiệu |
| `H2` | 32px | 42px | 400 | -2% | Giá trị chỉ số trong thẻ KPI |
| `H3` | 24px | 42px | 500 | -2% | Tiêu đề trang trong thanh đầu (`Dashboard`, `Trò chuyện`) |
| `Subtitle` | 18px | 30px | 600 | -2% | Tiêu đề khối thẻ (`Ứng dụng tiện ích`) |
| `Body 2` | 16px | 30px | 400 / 600 | -2% | Nội dung tin nhắn, ô nhập chính, nhãn ô tiện ích |
| `Body 1` | 13px | 24px | 400 / 600 | -2% | Chữ mặc định của thành phần, menu, nút, thẻ công việc |
| `Overline` | 12px | 22px | 600 | 0,4px | Nhãn nhóm menu viết hoa (`DANH MỤC`) |
| `Disclaimer` | 11px | 22px | 400 | 0,2px | Chữ trong huy hiệu, mốc thời gian, chú thích |
| `Code 2` | 15px | 22px | 400 | 0 | Khối mã trong câu trả lời |
| `Code 1` | 13px | 22px | 400 | 0 | Thông số đo lường mô hình, mã yêu cầu |

### 4.3. Quy định cho tiếng Việt

- Chiều cao dòng văn bản đoạn tối thiểu 1,5 để dấu thanh không chạm dòng trên.
- Chỉ viết hoa toàn bộ với nhãn nhóm menu và nhãn ngắn dưới 4 từ.
- Kiểm tra hiển thị đầy đủ các ký tự `ă, â, đ, ê, ô, ơ, ư` ở mọi cỡ chữ, nhất là 11px.

---

## 5. Khoảng cách, lưới, bo góc và bóng đổ

### 5.1. Thang khoảng cách

Token gốc: `0, 4, 6, 8, 10, 12, 16, 20, 24, 32, 36, 40, 48, 56, 64, 88` (px).
Giá trị phổ biến nhất là **khoảng cách giữa phần tử 10px** và **đệm trong thẻ 12px**.

### 5.2. Lưới bố cục

| Khung | Kích thước | Lưới cột |
| --- | --- | --- |
| Desktop | 1440 × 1024 | Sidebar 184px cố định bên trái; vùng nội dung 12 cột, rãnh 20px, lề 32px |
| Laptop | 1024 × 1024 | Sidebar 184px; vùng nội dung 12 cột, rãnh 20px |
| Tablet | 768 × 1024 | 8 cột, rãnh 16px, lề 10px |
| Mobile | 393 × 852 | 4 cột, rãnh 11px, lề 12px; thanh trạng thái 54px, vạch Home 21px |

### 5.3. Bo góc

| Token | Giá trị | Ứng dụng |
| --- | --- | --- |
| `radius-xs` | 3px | Huy hiệu dạng `radius`, ô ngày trong lịch |
| `radius-sm` | 6px | **Mặc định:** nút, ô nhập, combobox, mục sidebar, ô tiện ích ngang |
| `radius-md` | 8px | Thẻ số liệu di động, ô nhận diện, thẻ công việc |
| `radius-lg` | 12px | Ô biểu tượng ứng dụng 51px, thẻ KPI web, khối nội dung trong thân trang |
| `radius-xl` | 16px | Khung thân trang (Body container) trên web |
| `radius-full` | 9999px | Avatar, huy hiệu dạng `round`, nút nổi, nút biểu tượng tròn |

### 5.4. Bóng đổ

```css
--shadow-card: 0 1px 20px -1px rgba(0, 0, 0, 0.20), 0 1px 3px 0 rgba(0, 0, 0, 0.40);
--shadow-card-dark: 0 4px 20px -4px #01121A;
--shadow-modal: 0 8px 20px -8px rgba(0, 30, 43, 0.60);
--shadow-surface: 0 2px 0 0 rgba(189, 204, 213, 0.15);
--shadow-focus-primary: 0 0 0 3px #C3E7FE;
--shadow-focus-danger: 0 0 0 3px #FFEAE5;
--shadow-focus-default: 0 0 0 3px #E8EDEB;
```

Thẻ trên web chủ yếu dùng `--shadow-surface` kèm viền `gray-light-2`; `--shadow-card` dành cho
ô biểu tượng ứng dụng và thẻ nổi trên di động.

---

## 6. Bố cục ứng dụng web

```text
+----------------+---------------------------------------------------------------+
| SIDEBAR 214px  |  THÂN TRANG (thẻ trắng, bo 16px, viền #E8EDEB, lề 12px)       |
| nền #F9FBFC    |  +---------------------------------------------------------+  |
| [Khối nhận     |  | [<>] | Trang chủ / Lịch sử hội thoại    (Q) (Chuông) | (A) |  |
|  diện]         |  +---------------------------------------------------------+  |
| [+ Cuộc trò    |  | Tiêu đề trang (H1) [Huy hiệu]                           |  |
|  chuyện mới]   |  | Dòng mô tả ngắn                                         |  |
|  Trang chủ     |  |                                                         |  |
|  Lịch sử       |  |  Nội dung của đúng MỘT màn hình theo tuyến đường:       |  |
| -------------  |  |  Trang chủ | Trò chuyện | Lịch sử hội thoại             |  |
| GẦN ĐÂY        |  |                                                         |  |
|  Hội thoại 1   |  |                                                         |  |
|  Hội thoại 2   |  |                                                         |  |
|  Xem tất cả    |  +---------------------------------------------------------+  |
+----------------+---------------------------------------------------------------+
```

### 6.0. Luồng màn hình

Mỗi màn hình có đúng một chức năng; không trộn bảng thông tin với khung trò chuyện.

| Tuyến | Màn hình | Chức năng | Đi tiếp |
| --- | --- | --- | --- |
| `/` | Trang chủ | Chỉ số vận hành, tác vụ nhanh, ô hỏi, hội thoại gần đây | Gửi câu hỏi hoặc chọn tác vụ: sang `/tro-chuyen/moi` và gửi ngay |
| `/tro-chuyen/moi` | Trò chuyện (trống) | Màn chào, ô hỏi ở giữa, chip gợi ý | Khi máy chủ cấp mã: đổi địa chỉ sang `/tro-chuyen/:id`, không tải lại |
| `/tro-chuyen/:id` | Trò chuyện | Cột đọc 768px, ô hỏi cố định ở đáy | Sidebar: mở hội thoại khác hoặc tạo mới |
| `/lich-su` | Lịch sử hội thoại | Tìm, nhóm theo thời gian, xoá có xác nhận | Bấm một mục: sang `/tro-chuyen/:id` |

Nút `Cuộc trò chuyện mới` chỉ đặt ở sidebar (và nút nổi trên di động), không lặp lại ở thanh đầu
trang hay trong từng màn hình; luôn đưa về `/tro-chuyen/moi`.

### 6.1. Sidebar

- Rộng 214px (đệm 12px, nội dung 190px), nền `canvas`, **không** có viền phải: tách khỏi thân
  trang bằng khoảng trống và viền của thẻ thân trang.
- Đầu sidebar: chỉ có khối nhận diện cao 36px; nút đóng mở sidebar đặt cố định ở thanh đầu trang.
- Tiếp theo: nút `primary` `Cuộc trò chuyện mới` rộng 100%, hai mục `Trang chủ`, `Lịch sử hội thoại`,
  rồi nhóm `GẦN ĐÂY` liệt kê tối đa 8 hội thoại (một dòng, cắt bằng dấu ba chấm) và liên kết
  `Xem tất cả`.
- Nhóm menu phân cách bằng đường kẻ 1px `gray-light-2`, tiêu đề nhóm dùng `Overline` viết hoa.
- Mục menu: cao 40px, đệm `8px 6px`, khoảng cách biểu tượng và chữ 8px, biểu tượng 16px nét mảnh,
  chữ `Body 1` màu `gray-dark-1`.
- **Mục đang chọn:** nền trắng, viền 1px `gray-light-2`, bo 6px, bóng `--shadow-surface`,
  chữ và biểu tượng `blue-base`. Không tô nền xanh đặc.
- Hover: nền `gray-light-2`. Thu gọn còn 72px (chỉ biểu tượng), mặc định thu gọn khi màn hình
  rộng 768–1099px (laptop nhỏ); dưới 768px chuyển thành ngăn kéo.

### 6.2. Thanh đầu trang

- Nằm trong thẻ thân trang, cao 60px, ngăn với nội dung bằng đường kẻ `gray-light-2`; dùng chung
  cho mọi màn hình. Mọi nút trên thanh là nút `ghost` 36px: không viền, nền `gray-light-2` khi rê
  chuột, nền `blue-light-3` và biểu tượng `blue-base` khi bảng thả xuống đang mở.
- Trái: nút đóng mở sidebar cố định (biểu tượng khung có mũi tên trái khi sidebar đang mở, mũi tên
  phải khi đang thu gọn; `aria-expanded` theo trạng thái), vạch ngăn dọc, rồi breadcrumb (mục 6.3).
- Phải: tìm kiếm (mở `Lịch sử hội thoại`), thông báo, nhãn trạng thái hệ thống, vạch ngăn, rồi
  avatar 36px kèm họ tên và chức danh; dưới 1280px chỉ giữ avatar.
- Nhãn trạng thái hệ thống: viên thuốc cao 28px, viền `gray-light-2`, chữ 12px, chấm 8px
  (`success-dark-1` khi `Đang hoạt động`, `danger` khi `Mất kết nối`, `gray-base` khi `Đang kiểm tra`).
  Bấm để mở bảng `Tình trạng hệ thống`: chế độ định tuyến, hồ sơ GPU, mô hình nội bộ theo bậc,
  tỷ lệ rơi tầng 1 giờ; chỉ dùng nhãn tiếng Việt (`Ưu tiên mô hình nội bộ`, `GPU 6 GB`, `Bậc chính`),
  không lộ mã cấu hình.
- Chấm thông báo: tròn 8px màu `danger`, chỉ hiện khi có thông báo.
- Bảng thông báo (rộng 320px, bóng `--shadow-modal`) chỉ suy ra từ số liệu thật: mất kết nối máy chủ
  (`red`), chi phí đám mây đạt ngưỡng ngân sách ngày hoặc tỷ lệ rơi tầng vượt ngưỡng (`yellow`; hai
  ngưỡng do `/api/v1/chi-phi` trả, mặc định 80% và 20%), yêu cầu đang chờ ở hàng đợi nội bộ
  (`blue`). Không có thông báo thì ghi `Không có thông báo mới.`
- Menu tài khoản: thẻ hồ sơ gồm avatar 44px và ba dòng: họ tên (13px, độ đậm 600),
  `Chức danh · Phòng ban` (11px `gray-dark-3`), `Công ty/Đơn vị` (11px `gray-base`); tiếp theo là
  liên kết `Trang chủ`, `Lịch sử hội thoại`. Đóng bảng khi bấm ra ngoài hoặc nhấn `Esc`.
- **Hàng tiêu đề trang** nằm ngay dưới thanh đầu trang, tách riêng khỏi breadcrumb: `H1` 22px độ đậm
  600 (kèm huy hiệu nếu có, ví dụ chế độ định tuyến ở màn Trò chuyện) và dòng mô tả 13px
  `gray-dark-1` (lời chào kèm ngày ở Trang chủ, câu hướng dẫn hoặc số kết quả khi lọc ở Lịch sử).

### 6.3. Breadcrumb

- Một hàng 14px trong thanh đầu trang: mục đầu `Trang chủ` có biểu tượng nhà; mục cha là liên kết
  `gray-dark-1`, nền `gray-light-2` khi rê chuột; mục hiện tại màu `black` độ đậm 500, gắn
  `aria-current="page"`, cắt bằng dấu ba chấm khi quá dài; phân tách bằng dấu `/` màu `gray-light-1`.
- **Quá dài thì rút gọn ở giữa:** khi breadcrumb đầy đủ vượt bề ngang cho phép, các mục cha ở giữa
  gộp thành một mục `…` (liên kết tới mục cha gần nhất, tooltip và `aria-label` ghi đủ tên các mục bị
  ẩn); luôn ưu tiên giữ `Trang chủ` và mục hiện tại. Mục hiện tại vẫn quá dài thì cắt bằng dấu ba chấm.
- Breadcrumb thay cho nút quay lại: không đặt thêm nút mũi tên quay lại.
- **Dưới 768px (di động):** không hiển thị breadcrumb; thanh đầu trang chỉ hiện tiêu đề trang hiện
  tại (16px độ đậm 600, cắt bằng dấu ba chấm). Tiêu đề `H1` ở hàng tiêu đề trang được ẩn khỏi mắt
  nhìn nhưng vẫn giữ cho trình đọc màn hình, để không lặp tiêu đề hai lần.

| Màn hình | Breadcrumb |
| --- | --- |
| Trang chủ | `Trang chủ` |
| Lịch sử hội thoại | `Trang chủ / Lịch sử hội thoại` |
| Trò chuyện mới | `Trang chủ / Cuộc trò chuyện mới` |
| Trò chuyện đã có | `Trang chủ / Lịch sử hội thoại / Tiêu đề hội thoại` |

### 6.4. Bố cục Trang chủ và hàng thẻ chỉ số (KPI)

- Thứ tự từ trên xuống: hàng KPI; hai cột tỷ lệ 3:2 gồm khối `Hỏi trợ lý` (tác vụ nhanh ở trên,
  ô hỏi ở đáy khối) và khối `Hội thoại gần đây` (7 mục, cao bằng cột trái). Trạng thái hệ thống
  nằm ở thanh đầu trang, không đặt trong nội dung Trang chủ.
- Ở khung 1280 × 680 (laptop nhỏ), hàng KPI, tác vụ nhanh và phần đầu ô hỏi thấy được ngay.
- Bốn thẻ KPI cùng cỡ, khoảng cách 12px, nền trắng, viền `gray-light-2`, bo 12px, đệm `14px 16px`.
- Mọi thẻ dùng chung một khung ba tầng để nhãn, giá trị và chú thích thẳng hàng giữa các thẻ:
  1. Nhãn: biểu tượng 16px `blue-base` + nhãn 13px màu `gray-dark-1`, sát mép trên.
  2. Giá trị: 26px màu `black`; chỉ báo phụ (vòng tiến độ 36px, cung `success`, nền cung
     `gray-light-2`) đặt bên phải cùng hàng, không chứa chữ.
  3. Chân thẻ đẩy xuống đáy: thanh tiến độ (nếu có) rồi chú thích 11px `gray-dark-1`.
- Góc phải trên: chấm đỏ nhấp nháy (pulsing dot) khi có mục mới.
- Nội dung bốn thẻ:
  - `Lượt hỏi hôm nay`: giá trị `tổng/đám mây` (ví dụ `128/60`), biểu đồ tròn hai phần (nội bộ
    `blue-base`, đám mây `purple-base`), chú giải có chấm màu `Nội bộ 68 · Đám mây 60` với số in
    đậm màu `blue-dark-1` và `purple-dark-2`. Số liệu là `so_cau_hoi_hom_nay`,
    `so_cau_hoi_noi_bo`, `so_cau_hoi_dam_may` của `/api/v1/chi-phi`: máy chủ đếm câu hỏi theo ngày
    giờ Việt Nam, không tính lời gọi nền đặt tiêu đề.
  - `Phục vụ nội bộ`: tỷ lệ phần trăm kèm vòng tiến độ `success` (máy chủ trả phân số 0–1).
  - `Chi phí đám mây`: chi phí hôm nay, thanh tiến độ so với ngân sách ngày; chuyển `warning` khi
    vượt `nguong_canh_bao_ngan_sach` do máy chủ trả.
  - `Hàng đợi nội bộ`: giá trị `đang chờ/sức chứa tối đa` (ví dụ `2/20`), thanh ngang mức lấp đầy;
    sức chứa lấy từ trường `do_dai_toi_da` của `/api/v1/hang-doi/tinh-trang`, không ghi cứng. Chú
    thích ghi số đang chạy và `xử lý trung vị N giây`.
- Thanh ngang dùng chung: `blue-base`, chuyển `warning` từ 80%, `danger` khi đầy 100%.
- Mọi con số do máy chủ tính, không do model; số thập phân dùng dấu phẩy (`53,1%`).
- Dưới 960px: KPI 2 cột, hai khối nội dung xếp dọc.

### 6.4a. Màn Lịch sử hội thoại

- **Thanh lọc** dính ở đầu vùng cuộn (nền trắng, viền dưới `gray-light-2`), gồm một ô tìm rộng
  100%, cao 40px. Mọi nút là nút biểu tượng 32px **nằm trong ô**, bên phải, có tooltip
  (`data-goi-y`) và `aria-label`: `Xoá từ khoá` (chỉ hiện khi có chữ), `Tìm` (tải lại dữ liệu mới
  nhất; nhấn `Enter` tương đương), vạch ngăn, `Tìm kiếm nâng cao` (biểu tượng thanh trượt; nền
  `blue-light-3` khi mở, chấm xanh 7px khi đang có điều kiện nâng cao).
- Máy chủ lọc và sắp xếp (`tu_khoa`, `tu_ngay`, `den_ngay`, `sap_xep` của
  `GET /api/v1/hoi-thoai`), nên kết quả đúng ngay từ trang đầu. Từ khoá được gửi sau khi ngừng gõ
  300 ms (`Enter` gửi ngay); đổi ngày hoặc sắp xếp thì tải lại ngay; không cần bấm nút.
- **Tìm kiếm nâng cao** ẩn mặc định, mở thành hàng dưới ô tìm: `Từ ngày` – `Đến ngày` (không cho
  chọn ngược), `Sắp xếp` (`Mới nhất`, `Cũ nhất`, `Tên A → Z`, `Tên Z → A`; so sánh tên theo tiếng
  Việt) căn phải, và nút `Xoá lọc` khi đang lọc.
- `Từ ngày` và `Đến ngày` mặc định để trống (`null`): không giới hạn, hiển thị toàn bộ lịch sử. Mỗi
  ô ngày khi có giá trị thì có nút `×` 24px `gray-base` nằm trong ô (`Xoá ngày bắt đầu`,
  `Xoá ngày kết thúc`); bấm nút hoặc xoá trắng ô thì đầu đó trở lại `null`.
- **Dòng hội thoại** (danh sách phẳng, không khung bao; mỗi dòng cao tối thiểu 52px, kẻ dưới
  `gray-light-2`, rê chuột nền `gray-light-3`): biểu tượng trò chuyện 16px `gray-base`, tiêu đề 14px
  một dòng cắt bằng dấu ba chấm, dòng phụ 11px `gray-dark-1` dạng `8 lượt · cập nhật 14:30` (số lượt
  là số câu hỏi, trường `so_luot` của `GET /api/v1/hoi-thoai`; hôm nay, hôm qua ghi giờ `HH:mm`, cũ
  hơn ghi `dd/mm`, khác năm ghi `dd/mm/yyyy`); cuối dòng là nút `Xoá hội thoại` dạng nút biểu tượng
  thùng rác 28px, **luôn hiển thị** (không
  chỉ hiện khi rê chuột, để dùng được trên màn hình cảm ứng), màu `gray-base`, rê chuột nền
  `red-light-3` và biểu tượng `danger`. Bấm nút mở hộp thoại xác nhận của ứng dụng, không dùng
  `window.confirm`.
- Sắp theo ngày thì nhóm `HÔM NAY`, `HÔM QUA`, `CŨ HƠN` (đảo thứ tự khi `Cũ nhất`);
  sắp theo tên thì một danh sách phẳng.
- **Cuộn vô hạn:** tải 30 hội thoại mỗi trang; mốc cuối danh sách còn cách đáy khung nhìn 300px thì
  tải trang kế, bỏ mục trùng theo `id`; trang đầu chưa lấp đầy khung nhìn thì tự tải tiếp. Đang tải
  thêm thì hiện vòng xoay; hết danh sách thì ghi `Đã hiển thị toàn bộ`.
- **Không hiển thị tổng số hội thoại** (dòng mô tả, sidebar, cuối danh sách): con số này không giúp
  người dùng tìm lại hội thoại, lại dễ gây nhầm khi đang lọc. Dòng mô tả bình thường là câu cố định
  `Tìm và mở lại các cuộc trò chuyện trước đây`; chỉ khi đang tìm hoặc lọc mới ghi
  `Tìm thấy 12 cuộc trò chuyện` (lấy `tong_so` do máy chủ đếm theo bộ lọc). Liên kết sidebar chỉ ghi
  `Xem tất cả`. Số liệu
  tổng hợp phục vụ quản lý thuộc bảng quản trị (Giai đoạn 8).
- **Không có kết quả:** minh hoạ SVG tự vẽ (trang tài liệu trống và kính lúp, màu `blue-light-2`,
  `blue-base`), tiêu đề `Không tìm thấy hội thoại phù hợp`, gợi ý và nút `Xoá lọc`.

### 6.5. Khối nội dung

- Thẻ trắng, viền `gray-light-2`, bo 12px, đệm `12px 14px 14px`; tiêu đề 16px độ đậm 600.
- Góc phải tiêu đề: nút biểu tượng vuông 32px (lọc, sắp xếp, sửa, mở rộng).
- Nội dung cuộn trong khối, không cuộn toàn trang; thanh cuộn mảnh 4px, bo `radius-xs`.

### 6.6. Footer

- Cố định ở chân thẻ thân trang, cao 32px, viền trên `gray-light-2`, chữ 11px `gray-dark-1`;
  không cuộn theo nội dung, có mặt ở mọi màn hình.
- Trái: `© <năm hiện tại> <tác giả>. Bảo lưu mọi quyền.` rồi `Trợ lý nội bộ · Phiên bản <x.y.z>`
  (phiên bản lấy từ `/health`). Tên tác giả khai báo tại `CAU_HINH_APP.TAC_GIA` trong
  `frontend/src/app/core/cau-hinh.ts`; đây là ghi nhận bản quyền của tác giả phần mềm, không phải
  nhận diện tổ chức nên không trái mục 0. Không ghi tên tổ chức thật hay email.
- Phải: `Trợ lý có thể sai. Hãy kiểm tra lại số liệu quan trọng.`; dưới 1100px lời nhắc này
  chuyển xuống dưới ô hỏi của màn Trò chuyện. Ẩn footer dưới 768px.

---

## 7. Thư viện thành phần

### 7.1. Nút (`btn`)

| Thuộc tính | Giá trị |
| --- | --- |
| Kích thước | `xsmall` 22px, `small` 28px, `default` 36px, `large` 46px |
| Biến thể | `default`, `primary`, `primaryOutline`, `danger`, `dangerOutline`, `baseBlue`, `disabled`, `isLoading` |
| Trạng thái | `default`, `hover` |
| Tuỳ chọn | Biểu tượng trái, biểu tượng phải, vòng xoay chờ |

- `primary`: nền `blue-base`, chữ trắng, viền `blue-dark-1`; hover viền `blue-dark-2`, bóng focus
  `--shadow-focus-primary`.
- `primaryOutline`: nền trắng, viền và chữ `blue-dark-1`.
- `default`: nền trắng, viền `gray-base`, chữ `black`, bóng `--shadow-focus-default` khi hover.
- `danger` / `dangerOutline`: nền `danger` chữ trắng / viền và chữ `danger`, hover `#C82222`.
- `disabled`: nền `gray-light-2`, viền `gray-light-1`, chữ `gray-base`.
- Bo góc 6px, chữ `Body 1` (13px) ở cỡ nhỏ và `Body 2` (16px) ở cỡ `large`.

### 7.2. Huy hiệu (`Badge`)

- Cao 20px, đệm `2px 6px`, chữ `Disclaimer` 11px, viền 1px; dạng `round` (bo tròn) hoặc
  `radius` (bo 3px).

| Màu | Nền | Viền | Chữ | Dùng cho |
| --- | --- | --- | --- | --- |
| `darkgray` | `#3D4F58` | `#1C2D38` | `#FFFFFF` | Nhãn nhấn trung tính |
| `lightgray` | `#F9FBFA` | `#E8EDEB` | `#5C6C75` | Nhãn phụ, tầng mô hình |
| `red` | `#FFEAE5` | `#FFCDC7` | `#970606` | `Cần thực hiện`, lỗi |
| `yellow` | `#FEF7DB` | `#FFEC9E` | `#944F01` | `Chờ thực hiện`, cảnh báo |
| `blue` | `#E1F7FF` | `#C3E7FE` | `#1254B7` | `Đang thực hiện`, thông tin |
| `green` | `#E3FCF7` | `#C0FAE6` | `#00684A` | `Hoàn thành`, thành công |

### 7.3. Ô nhập, combobox và chọn ngày

- Nhãn (`label`): tiêu đề `Body 1` SemiBold màu `black`, mô tả `Body 1` màu `gray-dark-1`;
  biến thể `large` dùng 16px.
- Ô nhập: nền trắng, viền 1px `gray-base`, bo 6px, đệm `5px 8px 5px 12px`, biểu tượng phải 16px.
  Cỡ `xsmall`, `small`, `default`, `large` tương ứng với nút.
- Trạng thái: `hover` viền `gray-dark-1`; `focus` viền `blue-base` kèm `--shadow-focus-primary`;
  `error` viền `danger` và dòng lỗi 13px có biểu tượng cảnh báo; `valid` viền `success-dark-1`;
  `disabled` nền `gray-light-2`.
- Combobox: danh sách thả xuống là thẻ trắng bo 6px, bóng `--shadow-card`; tiêu đề nhóm màu
  `blue-dark-1`; có trạng thái `đang tải` và `không có kết quả`.
- Chọn ngày: định dạng `DD/MM/YYYY`; lịch có nút tháng trước/sau, ba ô chọn ngày/tháng/năm,
  tuần bắt đầu từ thứ Hai; ngày chọn có nền `blue-light-3`, ngày ngoài tháng màu `gray-light-1`.

### 7.4. Avatar

- Cỡ `default` 28px, `large` 36px, `xlarge` 52px; dạng biểu tượng người, chữ viết tắt hoặc ảnh.
- Nhóm avatar xếp chồng lệch 8px, viền trắng 2px, kèm chữ `+100 thành viên` cỡ 11px.

### 7.5. Ô tiện ích (`feature`)

| Biến thể | Kích thước | Mô tả |
| --- | --- | --- |
| `feature` | 51 × 51 | Ô biểu tượng ứng dụng di động: nền trắng, bo 12px, `--shadow-card` |
| `feature_apps` | 179–206 × 54–56 | Ô ngang: biểu tượng 36px + nhãn `Body 2`, viền `gray-light-2`, bo 6px |
| `feature_HRMS` | 179 × 95 | Ô dọc: biểu tượng trên, nhãn dưới, dùng cho lưới chức năng con |
| `feature_sidebar` | 188 × 40 | Mục menu sidebar (mục 6.1) |
| `feature_surfaceCard` | 455 × 82 | Thẻ số liệu ngang có chấm nhấp nháy |

Hover mọi ô tiện ích: viền `blue-light-2`, nền `blue-light-3`.

### 7.6. Thẻ công việc và dòng danh mục

- **Thẻ công việc** (lưới 2 cột): tiêu đề `Body 1` SemiBold, mô tả 11px `gray-dark-1`, dòng thời gian
  có biểu tượng đồng hồ, nhóm avatar, huy hiệu trạng thái ở góc phải dưới, nút ba chấm góc phải trên.
- **Dòng danh mục** (danh sách dọc): biểu tượng tệp 48px có nhãn loại tệp (`DOC`) nền `blue-base`,
  tiêu đề hai dòng `Body 1`, dòng phụ `gray-dark-1`, huy hiệu trạng thái ở góc phải dưới.
- Cả hai: nền trắng, viền `gray-light-2`, bo 8px, đệm 10–12px.

### 7.7. Chỉ báo

- `spinner`: vòng xoay 14px, bốn khung hình.
- `pulsing dot`: chấm đỏ 8px trong quầng lan toả 30px (di động) hoặc 40px (web), bốn khung hình,
  dùng cho mục có dữ liệu mới.

---

## 8. Thành phần riêng của trợ lý AI

Phần này ánh xạ ngôn ngữ thiết kế ở trên vào màn Trò chuyện, theo kiểu khung trò chuyện toàn
màn hình: một cột đọc rộng tối đa 768px ở giữa, ô hỏi cố định ở đáy, không có thẻ KPI hay danh sách
phụ trong màn này.

- **Cuộc trò chuyện trống** (`/tro-chuyen/moi`): biểu tượng 48px, tiêu đề 24px
  `Anh/Chị cần hỗ trợ việc gì?`, ô hỏi và chip gợi ý cùng nằm giữa màn hình.
- **Đã có tin nhắn:** tin nhắn cuộn trong cột đọc; ô hỏi dính đáy, phía trên có dải mờ trắng.

### 8.1. Tin nhắn

| Vai trò | Nền | Chữ | Căn | Bo góc |
| --- | --- | --- | --- | --- |
| Người dùng | `gray-light-2` | `black`, 16px | Phải, tối đa 80% chiều rộng | `18px 18px 4px 18px` |
| Trợ lý | Không có bong bóng, chữ trực tiếp trên nền trắng | `black`, 16px, dòng 28px | Trái, toàn cột | Không |
| Thông báo hệ thống | Theo banner mục 8.4 | Theo banner | Giữa | 6px |

- Avatar trợ lý 28px dùng biểu tượng của khối nhận diện trung tính.
- Câu hỏi dài hơn 6 dòng (hoặc 360 ký tự) được thu gọn còn 6 dòng, mờ dần ở đáy, kèm nút
  `Xem thêm ▾` / `Thu gọn ▴` (12px, `blue-dark-1`, `aria-expanded`). Mở rộng bằng **bấm**, không dùng
  rê chuột, để tránh bung ngoài ý muốn và dùng được trên màn hình cảm ứng.
- Khoảng cách giữa hai lượt hỏi đáp 24px.
- Đang phát theo dòng (SSE): con trỏ nhấp nháy màu `blue-base` ở cuối văn bản; trước khi có token
  đầu tiên hiển thị `spinner` kèm chữ `Đang soạn câu trả lời...`.

### 8.2. Huy hiệu đo lường mô hình

Theo quy tắc kỹ thuật số 7 trong `AGENTS.md`, dưới mỗi câu trả lời hiển thị một hàng huy hiệu:

- Hiển thị là **một dòng chữ phụ** 11px màu `gray-dark-1`, không nền, không viền, để không cạnh tranh
  với nội dung câu trả lời; các mục ngăn bằng dấu `·` màu `gray-light-1`.
- Mục đầu là nguồn kèm chấm tròn 6px: `Nội bộ · chính` (chấm `success-dark-1`), `Đám mây · tầng 1`
  (chấm `gray-base`). Khi máy chủ báo `ha_cap` (tầng phục vụ khác tầng đầu của chuỗi định tuyến
  thực tế, hoặc bậc nhỏ trả lời) thì chấm `warning` và chữ `warning-dark-2`; tầng 1 ở chế độ ưu tiên
  đám mây không bị coi là hạ cấp. Cờ này có cả khi mở lại hội thoại.
- Tiếp theo: tên model (`Code 1` 11px), token vào/ra, chi phí (chỉ khi lớn hơn 0), tốc độ và độ trễ
  (ẩn khi bằng 0). Rê chuột vào dòng để xem đủ mọi thông số (tooltip, đồng thời là `aria-label`).
- Nút sao chép câu trả lời dạng nút biểu tượng 28px, đặt **cuối** hàng và căn mép phải cột đọc
  (thứ tự đọc trái sang phải, trên xuống dưới: nội dung, thông số, thao tác); sau khi sao chép,
  biểu tượng đổi thành dấu tích trong 2 giây.

### 8.3. Ô nhập câu hỏi

- Một thành phần dùng chung cho Trang chủ và Trò chuyện: thẻ trắng, viền 1px `gray-light-1`, bo 16px,
  bóng nhẹ; khi focus viền `blue-base` kèm `--shadow-focus-primary`.
- Vùng văn bản tự giãn tối đa khoảng 6 dòng, 16px; placeholder màu `gray-base`. `Enter` để gửi,
  `Shift + Enter` để xuống dòng (có dòng gợi ý `Disclaimer` bên trái nút gửi).
- Nút gửi: tròn 36px nền `blue-base`, biểu tượng mũi tên lên; vô hiệu khi ô trống; trong lúc phát
  chuyển thành nút dừng viền `gray-base`.
- Ở Trang chủ, gửi câu hỏi **không** trò chuyện tại chỗ mà mở `/tro-chuyen/moi` và gửi ngay.
- Lời nhắc `Trợ lý có thể sai. Hãy kiểm tra lại số liệu quan trọng.` nằm ở footer (mục 6.6);
  dưới 1100px hiển thị dạng `Disclaimer` ngay dưới ô hỏi của màn Trò chuyện.

### 8.4. Banner trạng thái

Banner bo 6px, viền 1px, biểu tượng trái 16px, có thể có nút đóng:

| Loại | Nền | Viền | Chữ | Biểu tượng | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| Thông tin | `#E1F7FF` | `#C3E7FE` | `#083C90` | `#016BF8` | Đang dùng mô hình local |
| Cảnh báo | `#FEF7D8` | `#FFEC9E` | `#944F01` | `#FFC010` | Dữ liệu nhạy cảm chỉ xử lý local |
| Thành công | `#E3FCF7` | `#C0FAE6` | `#00684A` | `#00A35C` | Đã lưu hội thoại |
| Lỗi | `#FFEAE5` | `#FFCDC7` | `#970606` | `#DB3030` | Dịch vụ tạm ngưng, kèm `ma_yeu_cau` |

### 8.5. Gợi ý tác vụ nhanh

Bốn tác vụ mẫu dùng chung một danh mục, hiển thị ở hai nơi:

- **Trang chủ:** lưới 2 cột các ô `feature_apps` (biểu tượng 36px, tên, mô tả một dòng, mũi tên phải).
- **Màn Trò chuyện trống:** hàng chip bo tròn cao 36px dưới ô hỏi.

| Tác vụ | Biểu tượng | Mô tả |
| --- | --- | --- |
| `Tra cứu quy trình` | Hồ sơ | Quy trình cấp điện mới cho hộ gia đình |
| `Soạn công văn` | Bút | Công văn trả lời kiến nghị của khách hàng |
| `Diễn giải biểu giá` | Biểu đồ | Biểu giá bán lẻ điện sinh hoạt bậc thang |
| `Tóm tắt văn bản` | Tài liệu | Điểm chính của văn bản quy định mới |

Chọn một tác vụ sẽ mở cuộc trò chuyện mới và gửi ngay câu hỏi mẫu tương ứng.

---

## 9. Màn hình đăng nhập

- Bố cục hai cột trên 1440px: cột trái nền trắng chứa biểu mẫu rộng 342px căn giữa; cột phải là
  bảng `gradient-navy` bo 32px, cách mép 20px, chứa câu giới thiệu `H3` màu trắng
  (`Trợ lý AI nội bộ cho cán bộ, công nhân viên`) và ảnh xem trước giao diện của chính sản phẩm này.
- Biểu mẫu: khối nhận diện, câu định vị `Subtitle` màu `gray-dark-2`, tiêu đề `Đăng nhập` cỡ `H3`
  SemiBold; hai ô nhập cỡ `large` (`Tài khoản`, `Mật khẩu` có nút ẩn/hiện); liên kết `Quên mật khẩu?`
  màu `blue-base`; nút `primary` cỡ `large` rộng 100%; dòng phiên bản `Disclaimer` màu `gray-dark-1`.
- Trạng thái vô hiệu: nút `disabled` khi chưa nhập đủ hai trường.
- Dưới 1024px ẩn cột phải; trên di động, nền trên là dải xanh thẫm, biểu mẫu nằm trên nền trắng.
- Đăng nhập một lần (SSO) thuộc Giai đoạn 8; ở giai đoạn này màn hình chỉ là thiết kế.

---

## 10. Bản di động

- Khung 393 × 852, nền `canvas-mobile`, đệm ngang 12px.
- **Đầu trang** cao khoảng 259px: nền `gradient-navy` có họa tiết hạt sáng; hàng trên gồm nút menu,
  khối nhận diện (chữ trắng), nút thông báo; tiếp theo là avatar 52px, chức danh (`blue-light-1`,
  13px) và họ tên (trắng, 18px); cuối cùng là thẻ hồ sơ `gradient-navy` viền `gradient-border`
  chứa ba chỉ số và vòng tiến độ.
- **Thẻ số liệu**: lưới 2 cột, nền trắng, bo 8px, `--shadow-card`, chấm nhấp nháy góc phải.
- **Ô tìm kiếm**: bo 6px, viền `blue-base`, biểu tượng kính lúp màu `blue-base`.
- **Lưới ứng dụng**: 4 cột, ô `feature` 51px, nhãn 13px căn giữa tối đa ba dòng.
- **Thanh điều hướng đáy** cao 80px: nền trắng có khuyết cong ở giữa chứa nút nổi 56px tròn
  `gradient-navy` biểu tượng trắng; các mục (biểu tượng 20px + nhãn 13px), mục chọn màu `blue-base`,
  còn lại `gray-dark-1`. Với trợ lý: `Trang chủ`, nút nổi `Hỏi mới`, `Lịch sử` (mỗi mục đúng một
  chức năng đã có; ẩn thanh trong màn Trò chuyện để ô soạn không bị che).

---

## 11. Giọng điệu và định dạng dữ liệu

1. **Trang trọng, tôn trọng:** xưng `Trợ lý`, gọi người dùng là `Anh/Chị`; không dùng khẩu ngữ.
2. **Chính xác và minh bạch:** nêu rõ nguồn và giới hạn; khi vượt thẩm quyền, hướng dẫn liên hệ
   đơn vị phụ trách thay vì tự kết luận.
3. **Định dạng dữ liệu:**
   - Tiền: dấu chấm phân tách hàng nghìn, kèm đơn vị (`1.450.000 đ`).
   - Điện năng: số kèm `kWh` (`320 kWh`).
   - Ngày giờ: `dd/mm/yyyy - HH:mm` (`18/09/2026 - 14:30`); ô chọn ngày dùng `DD/MM/YYYY`.
   - Kỳ báo cáo: `09 - Tháng 9`.

---

## 12. Biến CSS toàn cục

Bộ token dưới đây là nguồn chuẩn để khai báo trong `frontend/src/styles.scss`:

```css
:root {
  /* 1. Dải xanh chủ đạo */
  --blue-dark-3: #0C2657;
  --blue-dark-2: #083C90;
  --blue-dark-1: #1254B7;
  --blue-base: #016BF8;
  --blue-light-1: #0498EC;
  --blue-light-2: #C3E7FE;
  --blue-light-3: #E1F7FF;
  --gradient-navy: linear-gradient(135deg, #031863 0%, #0630C9 100%);
  --gradient-border: linear-gradient(135deg, #0032E9 0%, #8FBFFA 100%);

  /* 2. Màu trạng thái */
  --green-dark-3: #023430;
  --green-dark-2: #00684A;
  --green-dark-1: #00A35C;
  --green-base: #00ED64;
  --green-light-1: #71F6BA;
  --green-light-2: #C0FAE6;
  --green-light-3: #E3FCF7;
  --yellow-dark-3: #4C2100;
  --yellow-dark-2: #944F01;
  --yellow-base: #FFC010;
  --yellow-light-2: #FFEC9E;
  --yellow-light-3: #FEF7D8;
  --red-dark-3: #5B0000;
  --red-dark-2: #970606;
  --red-base: #DB3030;
  --red-light-1: #FF6960;
  --red-light-2: #FFCDC7;
  --red-light-3: #FFEAE5;
  --purple-dark-3: #2D0B59;
  --purple-dark-2: #5E0C9E;
  --purple-base: #B45AF2;
  --purple-light-2: #F1D4FD;
  --purple-light-3: #F9EBFF;

  /* 3. Trung tính */
  --black: #001E2B;
  --white: #FFFFFF;
  --gray-dark-4: #112733;
  --gray-dark-3: #1C2D38;
  --gray-dark-2: #3D4F58;
  --gray-dark-1: #5C6C75;
  --gray-base: #889397;
  --gray-light-1: #C1C7C6;
  --gray-light-2: #E8EDEB;
  --gray-light-3: #F9FBFA;
  --canvas: #F9FBFC;
  --canvas-mobile: #F2F7FD;

  /* 4. Token ngữ nghĩa */
  --bg-primary: var(--white);
  --bg-primary-hover: var(--gray-light-2);
  --bg-primary-focus: var(--blue-light-3);
  --bg-secondary: var(--gray-light-3);
  --bg-inverse: var(--black);
  --bg-disabled: var(--gray-light-2);
  --bg-info: var(--blue-light-3);
  --bg-warning: var(--yellow-light-3);
  --bg-success: var(--green-light-3);
  --bg-error: var(--red-light-3);
  --text-primary: var(--black);
  --text-secondary: var(--gray-dark-1);
  --text-card: var(--gray-dark-3);
  --text-inverse-primary: var(--white);
  --text-inverse-secondary: var(--gray-light-1);
  --text-link: var(--blue-base);
  --text-error: var(--red-base);
  --text-disabled: var(--gray-base);
  --icon-primary: var(--gray-dark-1);
  --icon-secondary: var(--gray-base);
  --icon-info: var(--blue-base);
  --icon-warning: var(--yellow-dark-2);
  --icon-success: var(--green-dark-1);
  --icon-error: var(--red-base);
  --border-primary: var(--gray-base);
  --border-secondary: var(--gray-light-2);
  --border-inverse: var(--gray-dark-2);
  --border-success: var(--green-dark-1);
  --border-error: var(--red-base);
  --border-disabled: var(--gray-light-1);

  /* 5. Kiểu chữ */
  --font-sans: "Lexend", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "Source Code Pro", "SFMono-Regular", Consolas, monospace;
  --letter-spacing-tight: -0.02em;

  /* 6. Khoảng cách */
  --space-4: 4px;
  --space-6: 6px;
  --space-8: 8px;
  --space-10: 10px;
  --space-12: 12px;
  --space-16: 16px;
  --space-20: 20px;
  --space-24: 24px;
  --space-32: 32px;
  --space-40: 40px;
  --space-48: 48px;
  --space-64: 64px;

  /* 7. Bo góc */
  --radius-xs: 3px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* 8. Bóng đổ và chuyển động */
  --shadow-card: 0 1px 20px -1px rgba(0, 0, 0, 0.20), 0 1px 3px 0 rgba(0, 0, 0, 0.40);
  --shadow-modal: 0 8px 20px -8px rgba(0, 30, 43, 0.60);
  --shadow-surface: 0 2px 0 0 rgba(189, 204, 213, 0.15);
  --shadow-focus-primary: 0 0 0 3px var(--blue-light-2);
  --shadow-focus-danger: 0 0 0 3px var(--red-light-3);
  --shadow-focus-default: 0 0 0 3px var(--gray-light-2);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  /* 9. Bố cục */
  --sidebar-width: 214px;
  --sidebar-width-collapsed: 72px;
  --header-height: 68px;
}
```

---

## 13. Tài liệu tham khảo

- Tiêu chuẩn khả năng tiếp cận nội dung web W3C WCAG 2.1 mức AA.
