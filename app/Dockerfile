FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Systemowe zależności
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip i instalacja zależności Python w jednej warstwie
# Instalacja zależności w jednej warstwie
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y redis || true \
    && rm -rf /usr/local/lib/python3.12/site-packages/redis* \
    && pip install redis==6.4.0 --no-cache-dir --force-reinstall


# Skopiowanie kodu
COPY . .

# Wystawienie portu FastAPI
EXPOSE 8000

# Domyślna komenda (można nadpisać w docker-compose dla Celery)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
