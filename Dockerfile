FROM python:3.11-slim

# Install system dependencies (Tesseract for OCR and Poppler for PDF extraction)
RUN apt-get update && \
    apt-get install -y tesseract-ocr poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies
COPY packages/api/requirements.txt /app/packages/api/
RUN pip install --no-cache-dir -r packages/api/requirements.txt

# Copy everything else
COPY . /app

# The port is dynamically injected by Render
EXPOSE 80

# Start FastAPI from the new location
CMD ["sh", "-c", "uvicorn packages.api.main:app --host 0.0.0.0 --port ${PORT:-80}"]
