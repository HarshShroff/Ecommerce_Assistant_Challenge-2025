FROM python:3.9-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for FAISS index if it doesn't exist
RUN mkdir -p /data/faiss_index

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_PATH=/data/Product_Information_Dataset.csv
ENV FAISS_INDEX_PATH=/data/faiss_index
ENV PORT=8080

EXPOSE 8080

# Reduce to 1 worker to minimize memory usage
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "1", "--timeout", "300"]
