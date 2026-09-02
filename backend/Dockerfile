FROM python:3.11-slim

WORKDIR /app

# Install system dependencies: Tesseract OCR with English and Hindi language packs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the ML readiness-scoring model and bake the artefact into the image.
# This runs once at build time so the container starts with the model ready.
RUN python train_model.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
