# The study-card site on Render, with Tesseract so scanned and photographed pages can be read (OCR).
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-teaching.txt .
RUN pip install --no-cache-dir -r requirements-teaching.txt
COPY learn ./learn

# Render sets PORT; 10000 is its default.
ENV PORT=10000
CMD ["sh", "-c", "uvicorn learn.teaching_web:app --host 0.0.0.0 --port ${PORT}"]
