# Etap 1: baza
FROM python:3.12-slim

# Zmienne środowiskowe dla Pythona (lepsze logi, brak .pyc)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Katalog roboczy w kontenerze
WORKDIR /app

# Zainstaluj Graphviz w systemie
RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

# Instalacja zależności systemowych (opcjonalnie: np. psycopg2, curl)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalacja zależności Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiowanie aplikacji
COPY . .

# Wystawienie portu
EXPOSE 8000

# Uruchamianie uvicorn w trybie produkcyjnym
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
