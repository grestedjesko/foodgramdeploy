# Build stage - для компиляции зависимостей
FROM python:3.11-slim as builder

WORKDIR /app

# Устанавливаем только build-зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Runtime stage - финальный образ
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем только runtime-зависимости (без компиляторов)
RUN apt-get update && apt-get install -y \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копируем уже скомпилированные wheels из builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Устанавливаем из wheels (очень быстро)
RUN pip install --upgrade pip && \
    pip install --no-cache /wheels/*

# Копируем код приложения
COPY . .

RUN mkdir -p /app/static /app/media

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/').read()" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "foodgram.wsgi:application"]