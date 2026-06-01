FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg poppler-utils tesseract-ocr tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps /app/apps
COPY migrations /app/migrations
COPY Sources /app/Sources

EXPOSE 8000
CMD ["uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

