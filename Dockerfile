FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY run.py .

# Папки для данных и временных файлов
RUN mkdir -p /app/data /app/temp

CMD ["python", "run.py"]
