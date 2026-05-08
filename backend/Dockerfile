# --- Build Stage ---
FROM python:3.12-slim as builder

WORKDIR /app

# Ngăn Python tạo file .pyc và dùng buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Cài đặt công cụ build cần thiết cho các thư viện như psycopg2 hoặc ujson
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies vào folder riêng để copy sang stage sau
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final Stage ---
FROM python:3.12-slim

WORKDIR /app

# Cài đặt thư viện runtime cần thiết (như libpq cho Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy các thư viện đã cài đặt từ builder
COPY --from=builder /install /usr/local

# Copy mã nguồn backend
COPY . .

# Railway và các nền tảng Repository Deploy thường dùng cổng 8080 hoặc do họ chỉ định
ENV PORT 8080
EXPOSE 8080

# Chạy ứng dụng (Railway sẽ tự động ghi đè $PORT nếu cần)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
