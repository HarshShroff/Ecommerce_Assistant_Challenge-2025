FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PRODUCT_SERVICE_URL=https://ecommerce-product-service-green-haze-6364.fly.dev/
ENV ORDER_SERVICE_URL=https://ecommerce-order-service-morning-dawn-9468.fly.dev/

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "2"]
