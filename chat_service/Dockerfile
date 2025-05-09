FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PRODUCT_SERVICE_URL=${PRODUCT_SERVICE_URL}
ENV ORDER_SERVICE_URL=${ORDER_SERVICE_URL}

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "1"]
