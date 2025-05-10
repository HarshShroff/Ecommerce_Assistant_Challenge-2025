# E-Commerce Expert Assistant

A microservices-based chatbot designed to serve as a smart e-commerce assistant, capable of answering questions about product details and order information.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
  - [Prerequisites](#prerequisites)
  - [Running with Docker](#running-with-docker)
- [API Endpoints](#api-endpoints)
  - [Product Service (port 8000)](#product-service-port-8000)
  - [Order Service (port 8001)](#order-service-port-8001)
  - [Chat Service (port 8002)](#chat-service-port-8002)
- [Sample Queries](#sample-queries)
  - [Product Queries](#product-queries)
  - [Order Queries](#order-queries)
- [Implementation Details](#implementation-details)
  - [Product Service](#product-service)
  - [Order Service](#order-service)
  - [Chat Service](#chat-service)
- [Optimizations](#optimizations)
- [Dependencies](#dependencies)
- [Future Improvements](#future-improvements)
- [Testing Instructions](#testing-instructions)

---

## Features

- **Product Search:** Semantic and keyword-based product search with price analysis.
- **Order Lookup:** Retrieve order details by customer ID, including filtering by priority and recency.
- **RAG Integration:** Utilizes Retrieval-Augmented Generation for accurate, context-aware responses.
- **Microservices Architecture:** Modular design with dedicated services for chat, product, and order management.
- **Caching:** Implements TTL-based caching to optimize response times for frequent queries.
- **Hybrid Search:** Combines semantic search with keyword fallback for robust product discovery.

---

## Project Structure

```
├── chat_service/
│   ├── app.py
│   ├── ...
├── data/
│   ├── Order_Data_Dataset.csv
│   ├── Product_Information_Dataset.csv
│   └── faiss_index/
│       ├── index.faiss
│       ├── index.pkl
│       └── metadata.json
├── mock_api/
│   ├── __init__.py
│   └── mock_api.py
├── order_service/
│   ├── app.py
│   ├── ...
├── product_service/
│   ├── app.py
│   ├── ...
├── tests/
│   ├── test_chat.py
│   ├── ...
├── docker-compose.yml
├── README.md
```

Each service resides in its own directory. The `data` directory contains datasets and search indices. The `tests` directory includes unit and integration tests.

---

## Setup and Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.9+

### Running with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ecommerce-challenge.git
   cd ecommerce-challenge
   ```

2. Build and start the services:
   ```bash
   docker-compose up --build
   ```

3. Access the web UI at [http://localhost:8002](http://localhost:8002).

4. Create the FAISS index for product search:
   ```bash
   docker-compose exec product-service python create_index.py
   ```

---

## API Endpoints

### Product Service (port 8000)

- `GET /health` - Health check
- `POST /search` - Search for products
- `GET /product/` - Retrieve product by ASIN

### Order Service (port 8001)

- `GET /health` - Health check
- `GET /orders/` - Retrieve orders for a customer
- `GET /orders/priority/` - Retrieve orders by priority

### Chat Service (port 8002)

- `GET /health` - Health check
- `GET /` - Web UI
- `POST /chat` - Process chat messages

---

## Sample Queries

### Product Queries

- **"What are the top rated guitar strings?"**
- **"Show me microphones under $30"**
- **"What's a good product for recording music?"**
- **"What are the top 5 highly-rated guitar products?"**
- **"Is the BOYA BYM1 Microphone good for a cello?"**

### Order Queries

- **"What are the details of my last order?"**
- **"Show me my recent orders."**
- **"Fetch 5 most recent high-priority orders."**

Sample chatbot responses are provided in the [Sample Queries](#sample-queries) section.

---

## Implementation Details

### Product Service

- Hybrid search: semantic search using FAISS, with keyword fallback.
- Caching for frequent queries.

### Order Service

- Customer order lookup by ID.
- Filtering by order priority.
- Robust error handling for CSV parsing.

### Chat Service

- Intent classification (product vs. order queries).
- Routing to appropriate microservices.
- Template-based response formatting.
- Price analysis for product searches.

---

## Optimizations

- **Memory Efficiency:** Batch processing for FAISS index creation.
- **Performance:** TTL caching for frequent queries.
- **Reliability:** Hybrid search with fallback mechanisms.
- **User Experience:** Detailed product information and price analysis.

---

## Dependencies

- Flask 3.0.2
- pandas 2.2.1
- langchain 0.1.16
- sentence-transformers 2.5.0
- faiss-cpu 1.8.0
- cachetools 5.3.2

---

## Future Improvements

- User authentication
- Product recommendation system
- Enhanced search filters (price, category, etc.)
- Full-text search for product descriptions
- Conversational context tracking

---

## Testing Instructions

1. Clone the repository:
   ```bash
   git clone https://github.com/HarshShroff/Ecommerce_Assistant_Challenge-2025.git
   cd ecommerce-challenge
   ```

2. Build and start the services:
   ```bash
   docker-compose up --build
   ```

3. Access the UI at [http://localhost:8002](http://localhost:8002).

4. Use the sample queries in the [Sample Queries](#sample-queries) section to interact with the chatbot.

5. To test API endpoints directly, use `curl` or Postman. For example:

   - Search for products:
     ```bash
     curl -X POST -H "Content-Type: application/json" -d '{"query": "guitar", "top_k": 5}' http://localhost:8000/search
     ```

   - Get order details for a customer:
     ```bash
     curl http://localhost:8001/orders/37077
     ```