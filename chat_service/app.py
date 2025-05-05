from flask import Flask, request, jsonify, render_template
import requests
import logging
import re
import os
from rag_handler import ChatHandler

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize chat handler
chat_handler = ChatHandler()

# Service URLs from environment variables with defaults
PRODUCT_SERVICE = os.environ.get(
    'PRODUCT_SERVICE_URL', 'https://ecommerce-product-service-green-haze-6364.fly.dev')
ORDER_SERVICE = os.environ.get(
    'ORDER_SERVICE_URL', 'https://ecommerce-order-service-morning-dawn-9468.fly.dev')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})


@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.json
        if not data:
            # Added logging
            logger.error("Invalid query: Missing request body")
            return jsonify({"error": "Missing request body"}), 400

        # Explicitly check for 'message' key and handle potential None
        message_content = data.get('message')
        if message_content is None:
            # Added logging
            logger.error("Invalid query: Missing 'message' parameter")
            return jsonify({"error": "Missing 'message' parameter"}), 400

        # Strip and check if empty
        user_input = message_content.strip()
        if not user_input:
            logger.info("Invalid query: Empty message parameter")
            return jsonify({"error": "Empty message parameter"}), 400

        logger.info(f"Received chat query: {user_input}")

        # Intent classification
        if any(keyword in user_input.lower() for keyword in ['order', 'purchase', 'ship', 'delivery', 'tracking']):
            return handle_order_query(user_input)
        return handle_product_query(user_input)
    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        return jsonify({"response": "I'm sorry, I encountered an error processing your request. Please try again."})


def handle_product_query(query):
    try:
        logger.info(f"Handling product query: {query}")
        response = requests.post(
            f"{PRODUCT_SERVICE}/search",
            json={'query': query, 'top_k': 5},
            timeout=5
        )

        if response.status_code != 200:
            logger.warning(
                f"Product service returned status {response.status_code}")
            return jsonify({
                "response": "I'm having trouble searching for products right now. Please try again later."
            })

        products = response.json()
        return jsonify({
            "response": chat_handler.generate_product_response(products, query)
        })
    except requests.exceptions.Timeout:
        logger.error("Product service request timed out")
        return jsonify({
            "response": "Our product service is currently busy. Please try again shortly."
        })
    except Exception as e:
        logger.error(f"Error in product query handler: {e}")
        return jsonify({
            "response": "I'm sorry, I encountered an error while searching for products. Please try again."
        })


def handle_order_query(query):
    # Extract customer ID using regex pattern
    customer_id_match = re.search(r'\b\d{5}\b', query)

    if not customer_id_match:
        return jsonify({
            "response": "Please provide your 5-digit Customer ID to check your orders."
        })

    customer_id = customer_id_match.group()
    logger.info(f"Handling order query for customer ID: {customer_id}")

    try:
        response = requests.get(
            f"{ORDER_SERVICE}/orders/{customer_id}",
            timeout=5
        )

        if response.status_code == 404:
            return jsonify({
                "response": f"I couldn't find any orders for customer ID {customer_id}."
            })

        if response.status_code != 200:
            logger.warning(
                f"Order service returned status {response.status_code}")
            return jsonify({
                "response": "I'm having trouble retrieving your order information right now. Please try again later."
            })

        order_data = response.json()
        return jsonify({
            "response": chat_handler.generate_order_response(order_data, query)
        })
    except requests.exceptions.Timeout:
        logger.error("Order service request timed out")
        return jsonify({
            "response": "Our order service is currently busy. Please try again shortly."
        })
    except Exception as e:
        logger.error(f"Error in order query handler: {e}")
        return jsonify({
            "response": "I'm sorry, I encountered an error while retrieving your order information. Please try again."
        })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
