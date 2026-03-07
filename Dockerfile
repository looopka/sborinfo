FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY run.py .

# Папки для данных и временных файлов
RUN mkdir -p /app/data /app/temp

CMD ["python", "run.py"]
