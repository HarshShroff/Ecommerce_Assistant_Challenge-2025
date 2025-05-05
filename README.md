# E-Commerce Expert Assistant

A microservices-based chatbot that serves as a smart e-commerce assistant, capable of answering questions about both product details and order information.

## Features

- **Product Search**: Find products based on user queries with semantic search
- **Order Lookup**: Retrieve order details by customer ID
- **RAG Integration**: Uses Retrieval-Augmented Generation for accurate responses
- **Microservices Architecture**: Modular design with separate services

## Project Structure

```
ecommerce_challenge/
├── product_service/ - Handles product search and retrieval
├── order_service/ - Manages order information
├── chat_service/ - Main interface for user interaction
├── data/ - Contains product and order datasets
├── tests/ - Unit tests for all services
```

## Setup and Installation

### Prerequisites
- Python 3.9+
- Fly.io account

### Setting up Fly.io

1. **Install the Fly.io CLI**:

   **macOS**:
   ```bash
   # Using Homebrew
   brew install flyctl
   
   # Or using curl
   curl -L https://fly.io/install.sh | sh
   ```

   **Linux**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

   **Windows**:
   ```powershell
   pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```
   
   If `pwsh` is not found, you can use `powershell` instead.

2. **Login to Fly.io**:
   ```bash
   # Login to existing account
   fly auth login
   
   # Or sign up for a new account
   fly auth signup
   ```

3. **Create Fly.io Volumes**:
   ```bash
   # Create volume for product data
   fly volumes create product_data --size 1 --app ecommerce-product-service

   # Create volume for order data
   fly volumes create order_data --size 1 --app ecommerce-order-service
   ```

4. **Copy Data to Volumes**:
   ```bash
   # Copy product data
   fly ssh sftp shell -a ecommerce-product-service
   # Then use put command to upload Product_Information_Dataset.csv to /data/

   # Copy order data
   fly ssh sftp shell -a ecommerce-order-service
   # Then use put command to upload Order_Data_Dataset.csv to /data/
   ```

## Deployment on Fly.io

1. **Deploy Services**:
   ```bash
   # Deploy product service
   cd product_service
   fly launch --image flyio/hellofly:latest
   # Follow the prompts to configure your app
   
   # Deploy order service
   cd ../order_service
   fly launch --image flyio/hellofly:latest
   
   # Deploy chat service
   cd ../chat_service
   fly launch --image flyio/hellofly:latest
   ```

2. **Update Environment Variables**:
   ```bash
   # For chat service, set URLs of other services
   fly secrets set PRODUCT_SERVICE_URL=https://ecommerce-product-service.fly.dev \
                   ORDER_SERVICE_URL=https://ecommerce-order-service.fly.dev \
                   -a ecommerce-chat-service
   ```

3. **Access the UI**:
   Visit `https://ecommerce-chat-service.fly.dev` to interact with the chatbot.

## Setting up VS Code Remote Development with Fly.io

1. **Install VS Code Remote SSH Extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Remote - SSH" and install it

2. **Configure SSH Access to Fly App**:
   ```bash
   # Create SSH keys if you don't have them
   ssh-keygen -t ed25519 -C "your_email@example.com"
   
   # Add your SSH key to Fly.io
   fly ssh establish
   ```

3. **Connect to Your Fly.io App**:
   - Open VS Code
   - Press Ctrl+Shift+P (or Cmd+Shift+P on macOS)
   - Type "Remote-SSH: Connect to Host" and select it
   - Enter the connection string: `fly-v2-app@ecommerce-product-service.internal`
   - Select the platform (Linux)
   - Enter your SSH key passphrase if prompted

4. **Start Developing**:
   - VS Code will connect to your Fly.io app
   - You can now edit files, run commands, and debug directly on the remote machine

## API Endpoints

### Product Service
- `GET /health` - Health check
- `POST /search` - Search for products
- `GET /product/` - Get product by ASIN

### Order Service
- `GET /health` - Health check
- `GET /orders/` - Get orders for a customer
- `GET /orders/priority/` - Get orders by priority

### Chat Service
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

## Testing

Run the tests with:
```bash
python -m pytest tests/
```

## Implementation Process

1. **Data Analysis**: Analyzed product and order datasets to understand structure
2. **Architecture Design**: Designed microservices architecture
3. **RAG Implementation**: Implemented semantic search with FAISS
4. **API Development**: Created RESTful APIs for each service
5. **UI Development**: Built a simple web interface
6. **Testing**: Added comprehensive test suite
7. **Deployment**: Configured Fly.io for easy deployment

## Troubleshooting

- If you encounter issues with Fly.io deployment, check the logs with:
  ```bash
  fly logs -a 
  ```

- For SSH connection issues, verify your SSH keys are properly set up:
  ```bash
  fly ssh issue --agent
  ```

- To restart an app after configuration changes:
  ```bash
  fly apps restart 
  ```

## Time Tracking

The project was completed according to the following timeline:
- Project Setup: 1.5 hours
- Data Analysis: 4 hours
- Architecture Design: 2.5 hours
- FAISS Index Creation: 1.2 hours
- Product Service Implementation: 5 hours
- Order Service Implementation: 2.5 hours
- Chat Service Implementation: 7 hours
- UI Development: 4 hours
- Testing: 5 hours
- Fly.io Deployment: 3 hours
- Documentation: 1.5 hours
- Bonus Features: 6 hours