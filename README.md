# E-Commerce Expert Assistant

A microservices-based chatbot that serves as a smart e-commerce assistant, capable of answering questions about both product details and order information.

## Features

- **Product Search**: Find products based on user queries with semantic search
- **Order Lookup**: Retrieve order details by customer ID
- **RAG Integration**: Uses Retrieval-Augmented Generation for accurate responses
- **Microservices Architecture**: Modular design with separate services
- **Caching**: Implements TTL caching for frequently requested queries
- **Hybrid Search**: Combines semantic search with keyword fallback for reliability
- **Price Analysis**: Provides average price information for product searches

## Project Structure

```
ecommerce_challenge/
├── product_service/ - Handles product search and retrieval
│   ├── app.py - Main Flask application
│   ├── product_retriever.py - Product search implementation
│   ├── create_index.py - Simple FAISS index creation
│   ├── embeddings.py - Memory-efficient FAISS index creation
│   └── Dockerfile
├── order_service/ - Manages order information
│   ├── app.py - Order service API
│   ├── mock_api_client.py - Mock API for order data
│   └── Dockerfile
├── chat_service/ - Main interface for user interaction
│   ├── app.py - Chat service implementation
│   ├── rag_handler.py - Response generation
│   ├── templates/ - HTML templates
│   ├── static/ - CSS and JS files
│   └── Dockerfile
├── data/ - Contains product and order datasets
│   ├── Order_Data_Dataset.csv
│   └── Product_Information_Dataset.csv
├── tests/ - Unit tests for all services
└── docker-compose.yml - Docker configuration
```

## Setup and Installation

### Prerequisites
- Docker and Docker Compose
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

3. Access the UI at: http://localhost:8002

4. Create the FAISS index for improved product search:
```bash
docker-compose exec product-service python create_index.py
```

## API Endpoints

### Product Service (port 8000)
- `GET /health` - Health check
- `POST /search` - Search for products
- `GET /product/` - Get product by ASIN

### Order Service (port 8001)
- `GET /health` - Health check
- `GET /orders/` - Get orders for a customer
- `GET /orders/priority/` - Get orders by priority

### Chat Service (port 8002)
- `GET /health` - Health check
- `GET /` - Web UI
- `POST /chat` - Process chat messages

## Sample Queries

### Product Queries
- "What are the top rated guitar strings?"
- "Show me microphones under $30"
- "What's a good product for recording music?"

### Order Queries
- "Check my order with customer ID 37077"
- "What's the status of my order? My ID is 41066"
- "Show me my recent orders. Customer ID 53639"

## Implementation Details

### Product Service
The product service uses a hybrid search approach:
1. First attempts semantic search using FAISS
2. Falls back to keyword search if FAISS search fails
3. Implements caching for frequently requested queries

### Order Service
The order service provides:
1. Customer order lookup by ID
2. Order filtering by priority
3. Error handling for CSV parsing issues

### Chat Service
The chat service:
1. Classifies user intent (product vs. order queries)
2. Routes requests to appropriate microservices
3. Formats responses using templates
4. Provides price analysis for product searches

## Optimizations

- **Memory Efficiency**: Batch processing for FAISS index creation
- **Performance**: TTL caching for frequent queries
- **Reliability**: Hybrid search with fallback mechanisms
- **User Experience**: Detailed product information with price analysis

## Dependencies

Main dependencies include:
- Flask 3.0.2
- pandas 2.2.1
- langchain 0.1.16
- sentence-transformers 2.5.0
- faiss-cpu 1.8.0
- cachetools 5.3.2

## Future Improvements

- Implement user authentication
- Add product recommendation system
- Enhance search with filters (price, category, etc.)
- Implement full-text search for product descriptions
- Add conversational context tracking