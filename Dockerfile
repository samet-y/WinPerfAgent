FROM python:3.12-slim

# Ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Sistem güncellemeleri ve gerekli araçlar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Gereksinimler ve uygulama dosyaları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port ayarı
EXPOSE 5000

# Prod ortamda Flask yerine Gunicorn kullanılır
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
