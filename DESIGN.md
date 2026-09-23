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
| Logo, biểu tượng, tên viết tắt của EVN, EVNHCMC hay đơn vị điện lực cụ thể | Khối nhận diện trung tính tại mục 2 |
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

1. **Biểu tượng:** ô vuông 28px, bo góc `radius-md` (8px), nền chuyển sắc `navy-start` sang
   `navy-end`, bên trong là biểu tượng bong bóng trò chuyện nét mảnh màu trắng.
2. **Chữ nhận diện:** `Trợ lý nội bộ`, Lexend SemiBold 16px, màu `black` (`#001E2B`).

| Tiêu chí | Quy định |
| --- | --- |
| Vùng an toàn | Tối thiểu 8px quanh khối |
| Nền đặt | Trắng, `canvas` hoặc dải xanh thẫm (chữ chuyển sang trắng) |
| Điều cấm | Không ghép thêm tên, logo hay màu nhận diện của tổ chức thật |

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
|                |  | Trò chuyện                        (Q) (Bell) (Apps) (A) |  |
| [Khối nhận     |  +---------------------------------------------------------+  |
|  diện]   [<>]  |  | Trang chủ > Trò chuyện          [09 - Tháng 9] [ ... ]  |  |
| -------------  |  | [KPI 1]      [KPI 2]      [KPI 3 (o)]   [KPI 4 (o)]     |  |
| DANH MỤC       |  | +-- Khối trò chuyện ---------+ +-- Lịch sử hội thoại -+ |  |
| [Trò chuyện]   |  | | Bong bóng tin nhắn         | | [DOC] Tiêu đề  [Huy] | |  |
|  Lịch sử       |  | | Huy hiệu đo lường mô hình  | | [DOC] Tiêu đề  [Huy] | |  |
| -------------  |  | | [Ô nhập câu hỏi ......(>)] | | [DOC] Tiêu đề  [Huy] | |  |
| VĂN PHÒNG      |  | +----------------------------+ +----------------------+ |  |
|  Soạn thảo     |  +---------------------------------------------------------+  |
|  Tra cứu       |                                                               |
| -------------  |                                                               |
| CÀI ĐẶT        |                                                               |
|  Mô hình, chi phí                                                              |
+----------------+---------------------------------------------------------------+
```

### 6.1. Sidebar

- Rộng 214px (đệm 12px, nội dung 190px), nền `canvas`, **không** có viền phải: tách khỏi thân
  trang bằng khoảng trống và viền của thẻ thân trang.
- Đầu sidebar: khối nhận diện cao 36px, bên phải là nút thu gọn (biểu tượng khung chia đôi).
- Nhóm menu phân cách bằng đường kẻ 1px `gray-light-2`, tiêu đề nhóm dùng `Overline` viết hoa.
- Mục menu: cao 40px, đệm `8px 6px`, khoảng cách biểu tượng và chữ 8px, biểu tượng 16px nét mảnh,
  chữ `Body 1` màu `gray-dark-1`.
- **Mục đang chọn:** nền trắng, viền 1px `gray-light-2`, bo 6px, bóng `--shadow-surface`,
  chữ và biểu tượng `blue-base`. Không tô nền xanh đặc.
- Hover: nền `gray-light-2`. Thu gọn còn 72px (chỉ biểu tượng); dưới 768px chuyển thành ngăn kéo.

### 6.2. Thanh đầu trang

- Nằm trong thẻ thân trang, cao 68px, đệm ngang 15px, ngăn với nội dung bằng đường kẻ `gray-light-2`.
- Trái: tiêu đề trang cỡ `H3`, màu `black`.
- Phải: nhóm nút biểu tượng vuông 32px, viền 1px `gray-light-2`, bo 6px, cách nhau 10px
  (tìm kiếm, thông báo, ứng dụng); nút đang kích hoạt có biểu tượng `blue-base`. Cuối nhóm là
  avatar tròn 36px, ngăn bằng đường kẻ dọc.
- Chấm thông báo: tròn 8px màu `danger`.

### 6.3. Dải định vị và bộ lọc kỳ

- Breadcrumb `Body 2`: mục đầu có biểu tượng trang chủ; mục trung gian màu `gray-dark-1`;
  mục có liên kết màu `blue-base`; phân tách bằng mũi tên `>` màu `gray-base`.
- Bên phải: nút chọn kỳ dạng viền (`09 - Tháng 9`) và nút ba chấm dọc, cùng kiểu nút biểu tượng.

### 6.4. Hàng thẻ chỉ số (KPI)

- Bốn thẻ cùng cỡ, khoảng cách 15px, nền trắng, viền `gray-light-2`, bo 12px, đệm 20px.
- Dòng nhãn: biểu tượng 16px `blue-base` + nhãn `Body 2` màu `gray-dark-1`.
- Dòng giá trị: `H2` màu `black`, dạng `Nhãn: Giá trị`.
- Góc phải trên: chấm đỏ nhấp nháy (pulsing dot) khi có mục mới, **hoặc** vòng tiến độ 72px
  (nét 6px, cung `success`, nền cung `gray-light-2`, số phần trăm `Body 2` ở giữa).
- Nội dung đề xuất cho trợ lý: số lượt hỏi trong ngày, số hội thoại đang mở, tỷ lệ phục vụ
  bằng mô hình local (vòng tiến độ), độ trễ trung vị. Mọi con số do công cụ tính, không do model.

### 6.5. Khối nội dung

- Thẻ trắng, viền `gray-light-2`, bo 12px, đệm 15px; tiêu đề `Subtitle`.
- Góc phải tiêu đề: nút biểu tượng vuông 32px (lọc, sắp xếp, sửa, mở rộng).
- Nội dung cuộn trong khối, không cuộn toàn trang; thanh cuộn mảnh 4px, bo `radius-xs`.

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

Phần này ánh xạ ngôn ngữ thiết kế ở trên vào giao diện trò chuyện.

### 8.1. Bong bóng trò chuyện

| Vai trò | Nền | Chữ | Căn | Bo góc |
| --- | --- | --- | --- | --- |
| Người dùng | `blue-base` | Trắng, `Body 2` | Phải, tối đa 70% chiều rộng | `12px 12px 3px 12px` |
| Trợ lý | Trắng, viền `gray-light-2`, `--shadow-surface` | `black`, `Body 2` | Trái, tối đa 80% | `12px 12px 12px 3px` |
| Thông báo hệ thống | Theo banner mục 8.4 | Theo banner | Giữa | 6px |

- Avatar trợ lý 28px dùng biểu tượng của khối nhận diện trung tính; avatar người dùng
  dùng chữ viết tắt.
- Khoảng cách giữa hai tin nhắn 10px, giữa hai lượt hỏi đáp 20px.
- Đang phát theo dòng (SSE): con trỏ nhấp nháy màu `blue-base` ở cuối văn bản; trước khi có token
  đầu tiên hiển thị `spinner` kèm chữ `Đang soạn câu trả lời...`.

### 8.2. Huy hiệu đo lường mô hình

Theo quy tắc kỹ thuật số 3 trong `AGENTS.md`, dưới mỗi câu trả lời hiển thị một hàng huy hiệu:

- Tầng và bậc (`local · chính`, `đám mây`): huy hiệu `blue` nếu local, `lightgray` nếu đám mây.
- Tên model, token vào/ra, chi phí, độ trễ, tok/s: chữ `Code 1` 11–13px màu `gray-dark-1`,
  ngăn bằng dấu `·`.
- Nút sao chép nội dung và sao chép `ma_yeu_cau` dạng nút biểu tượng `xsmall`.

### 8.3. Ô nhập câu hỏi

- Thẻ trắng, viền 1px `gray-base`, bo 12px, đệm 12px; khi focus viền `blue-base` kèm
  `--shadow-focus-primary`.
- Vùng văn bản tự giãn tối đa 6 dòng, `Body 2`; placeholder `Nhập câu hỏi nghiệp vụ...` màu `gray-base`.
- Nút gửi: `btn primary` cỡ `small`, hình tròn 32px, biểu tượng mũi tên; trong lúc phát chuyển thành
  nút dừng `default`.
- Dòng chú thích `Disclaimer` bên dưới: `Trợ lý có thể sai. Hãy kiểm tra lại số liệu quan trọng.`

### 8.4. Banner trạng thái

Banner bo 6px, viền 1px, biểu tượng trái 16px, có thể có nút đóng:

| Loại | Nền | Viền | Chữ | Biểu tượng | Ví dụ |
| --- | --- | --- | --- | --- | --- |
| Thông tin | `#E1F7FF` | `#C3E7FE` | `#083C90` | `#016BF8` | Đang dùng mô hình local |
| Cảnh báo | `#FEF7D8` | `#FFEC9E` | `#944F01` | `#FFC010` | Dữ liệu nhạy cảm chỉ xử lý local |
| Thành công | `#E3FCF7` | `#C0FAE6` | `#00684A` | `#00A35C` | Đã lưu hội thoại |
| Lỗi | `#FFEAE5` | `#FFCDC7` | `#970606` | `#DB3030` | Dịch vụ tạm ngưng, kèm `ma_yeu_cau` |

### 8.5. Gợi ý tác vụ nhanh

Màn chào hiển thị lưới 2–3 cột các ô `feature_apps`, mỗi ô là một câu hỏi mẫu:

- `Tra cứu quy trình cấp điện mới` (biểu tượng hồ sơ)
- `Soạn công văn trả lời khách hàng` (biểu tượng bút)
- `Diễn giải biểu giá bán lẻ điện` (biểu tượng biểu đồ)
- `Tóm tắt văn bản quy định mới` (biểu tượng tài liệu)

Tiêu đề màn chào dùng `H3`: `Xin chào Anh/Chị, cần hỗ trợ việc gì hôm nay?`.

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
  `gradient-navy` biểu tượng trắng; bốn mục (biểu tượng 20px + nhãn 13px), mục chọn màu `blue-base`,
  còn lại `gray-dark-1`. Với trợ lý: `Trò chuyện`, `Lịch sử`, nút nổi `Hỏi mới`, `Tiện ích`, `Cài đặt`.

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
