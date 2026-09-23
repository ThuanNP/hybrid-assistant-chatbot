# ==============================================================================
# Tầng 1: Xây dựng ứng dụng Angular (builder)
# Sử dụng Node.js 22 LTS (Alpine) đáp ứng yêu cầu phiên bản của Angular 22
# ==============================================================================
FROM node:22-alpine AS builder

WORKDIR /app

# Chép package.json và package-lock.json trước để tận dụng bộ nhớ đệm lớp Docker
COPY package.json package-lock.json ./

# Cài đặt sạch toàn bộ gói phụ thuộc
RUN npm ci

# Chép toàn bộ mã nguồn ứng dụng frontend
COPY . .

# Xây dựng ứng dụng cho môi trường sản xuất
RUN npx ng build --configuration production

# ==============================================================================
# Tầng 2: Môi trường chạy thực thi bằng Nginx không đặc quyền (runner)
# Sử dụng nginxinc/nginx-unprivileged:alpine (chạy bằng user nginx, cổng 8080)
# ==============================================================================
FROM nginxinc/nginx-unprivileged:alpine AS runner

# Chép tệp cấu hình Nginx tối ưu hoá cho Angular SPA và reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Chép sản phẩm đóng gói từ tầng builder
COPY --from=builder /app/dist/hybrid-assistant-chatbot-frontend/browser /usr/share/nginx/html

# Mở cổng 8080 (cổng mặc định của nginx-unprivileged)
EXPOSE 8080

# Kiểm tra sức khoẻ định kỳ bằng wget (có sẵn trong image alpine)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/ > /dev/null || exit 1

# Khởi chạy Nginx ở chế độ foreground
CMD ["nginx", "-g", "daemon off;"]
