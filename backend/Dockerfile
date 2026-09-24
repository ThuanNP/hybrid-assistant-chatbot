# ==============================================================================
# Tầng 1: Xây dựng môi trường ảo và cài đặt thư viện phụ thuộc
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /srv/backend/requirements.txt
COPY backend/requirements-rag.txt /srv/backend/requirements-rag.txt

RUN python -m venv /srv/.venv && \
    /srv/.venv/bin/pip install --no-cache-dir --upgrade pip && \
    /srv/.venv/bin/pip install --no-cache-dir -r /srv/backend/requirements.txt && \
    /srv/.venv/bin/pip install --no-cache-dir -r /srv/backend/requirements-rag.txt

# ==============================================================================
# Tầng 2: Môi trường chạy thực thi (runtime)
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /srv/backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/srv/.venv/bin:$PATH" \
    HF_HOME=/home/ungdung/.cache/huggingface

# Cài đặt thư viện hệ thống cần thiết cho Docling (OpenCV / PyTorch runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Tạo người dùng không phải root tên ungdung với UID 10001 và thư mục cache Hugging Face
RUN groupadd -g 10001 ungdung && \
    useradd -u 10001 -g ungdung -m -s /bin/sh ungdung && \
    mkdir -p /home/ungdung/.cache/huggingface && \
    chown -R ungdung:ungdung /home/ungdung/.cache

# Chép môi trường ảo từ tầng builder
COPY --from=builder --chown=ungdung:ungdung /srv/.venv /srv/.venv

# Chép mã nguồn backend, thư mục cấu hình và prompts từ gốc repo
COPY --chown=ungdung:ungdung backend/ /srv/backend/
COPY --chown=ungdung:ungdung config/ /srv/config/
COPY --chown=ungdung:ungdung prompts/ /srv/prompts/

# Chuyển sang quyền sở hữu người dùng ungdung
USER ungdung

# Cổng dịch vụ FastAPI
EXPOSE 8000

# Kiểm tra tình trạng sức khỏe qua urllib (ảnh slim không có curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).getcode() == 200 else 1)" || exit 1

# Khởi chạy ứng dụng với uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
