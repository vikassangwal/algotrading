FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (.dockerignore keeps .env, db, caches out)
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
