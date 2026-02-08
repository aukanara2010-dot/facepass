FROM python:3.11-slim

WORKDIR /code

# 1. Системные зависимости (ставим один раз)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Обновляем инструменты сборки
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 3. Сначала копируем ТОЛЬКО requirements.txt и ставим зависимости
# Это позволит Docker закешировать библиотеки и не переустанавливать их при изменении кода
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.26.3
RUN pip install --no-cache-dir -r requirements.txt

# 4. И только теперь копируем весь остальной код FacePass
COPY . .

# 5. Безопасность
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /code
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]