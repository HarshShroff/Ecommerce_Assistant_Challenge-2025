from flask import Flask, request, jsonify, render_template
import requests
import logging
import re
import os
import uuid
from rag_handler import ChatHandler
from session_manager import SessionManager, Session

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', str(uuid.uuid4()))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

chat_handler = ChatHandler()
session_manager = SessionManager(session_expiry_seconds=1800)

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8080')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://order-service:8080')

@app.route('/')
def index():
    """Renders the index.html template."""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Performs a health check."""
    return jsonify({"status": "healthy"})

@app.route('/chat', methods=['POST'])
def handle_chat():
    """Handles chat requests."""
    try:
        data = request.json
        if not data:
            logger.error("Chat request error: Missing request body")
            return jsonify({"error": "Missing request body"}), 400

        user_input = data.get('message', "").strip()
        if not user_input:
            logger.info("Chat request info: Empty message parameter")
            return jsonify({"error": "Empty message parameter"}), 400

        session_id_from_request = data.get('session_id')
        user_session = session_manager.get_session(session_id_from_request)
        
        logger.info(f"Session {user_session.session_id}: User query: '{user_input}'")
        user_session.add_to_history("user", user_input)

        expected_action = user_session.get_expected_input()
        logger.info(f"Session {user_session.session_id}: Current expected_action: '{expected_action}'")
        bot_response_data = None

        if expected_action == "customer_id_for_last_order":
            if re.fullmatch(r'\d{5}', user_input):
                logger.info(f"Session {user_session.session_id}: Received expected customer_id '{user_input}'.")
                bot_response_data = process_order_request(user_input, user_session)
            else:
                logger.info(f"Session {user_session.session_id}: Input '{user_input}' is not a 5-digit ID, still expecting customer_id.")
                bot_response_data = {"response": "That doesn't look like a 5-digit Customer ID. Please try again."}
        else:
            user_session.set_expected_input(None)
            if "high-priority" in user_input.lower() or "priority orders" in user_input.lower():
                logger.info(f"Session {user_session.session_id}: Detected high-priority order query.")
                bot_response_data = process_priority_order_request("High", user_session)
            elif any(keyword in user_input.lower() for keyword in ['order', 'purchase', 'ship', 'delivery', 'tracking', 'last order', 'recent order']):
                logger.info(f"Session {user_session.session_id}: Detected general order query.")
                bot_response_data = process_order_request(user_input, user_session)
            else:
                logger.info(f"Session {user_session.session_id}: Detected product query.")
                bot_response_data = process_product_request(user_input, user_session)
        
        if isinstance(bot_response_data, dict) and "response" in bot_response_data:
            user_session.add_to_history("bot", bot_response_data["response"])
            bot_response_data["session_id"] = user_session.session_id
            return jsonify(bot_response_data)
        else:
            logger.error(f"Session {user_session.session_id}: Handler returned unexpected data: {bot_response_data}")
            fallback_response = {"response": "I had a little trouble with that request.", "session_id": user_session.session_id}
            user_session.add_to_history("bot", fallback_response["response"])
            return jsonify(fallback_response), 500

    except Exception as e:
        logger.error(f"Critical error in /chat endpoint: {e}", exc_info=True)
        sid_for_error = data.get('session_id') if 'data' in locals() and data else str(uuid.uuid4())
        try:
            current_session_for_error = session_manager.get_session(sid_for_error)
            sid_for_error = current_session_for_error.session_id
        except Exception as session_e:
            logger.error(f"Could not get/create session_id during critical error handling: {session_e}")
            sid_for_error = "unavailable"

        return jsonify({"response": "I'm sorry, a critical error occurred on my end.", "session_id": sid_for_error}), 500


def process_product_request(query: str, user_session: Session):
    """Processes product requests."""
    logger.info(f"Session {user_session.session_id}: Calling product service for query: '{query}'")
    try:
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/search",
            json={'query': query, 'top_k': 5},
            timeout=10
        )
        response.raise_for_status()
        products = response.json()
        return {"response": chat_handler.generate_product_response(products, query)}
    except requests.exceptions.Timeout:
        logger.error(f"Session {user_session.session_id}: Product service request timed out for query '{query}'")
        return {"response": "Our product service is taking too long to respond. Please try again shortly."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Session {user_session.session_id}: Error calling product service for query '{query}': {e}")
        return {"response": "I'm having trouble searching for products right now. Please try again later."}
    except Exception as e:
        logger.error(f"Session {user_session.session_id}: Unexpected error in product query handler for '{query}': {e}", exc_info=True)
        return {"response": "I'm sorry, I encountered an error while searching for products."}


def process_order_request(query: str, user_session: Session):
    """Processes order requests."""
    customer_id_from_session = user_session.get_data("customer_id")
    customer_id_from_query_match = re.search(r'\b\d{5}\b', query)
    
    current_customer_id = None

    if customer_id_from_query_match:
        current_customer_id = customer_id_from_query_match.group()
        if current_customer_id != customer_id_from_session:
            user_session.set_data("customer_id", current_customer_id)
            logger.info(f"Session {user_session.session_id}: Customer ID '{current_customer_id}' updated from query.")
        user_session.set_expected_input(None)
    elif customer_id_from_session:
        current_customer_id = customer_id_from_session
        logger.info(f"Session {user_session.session_id}: Using customer ID '{current_customer_id}' from session.")
        user_session.set_expected_input(None)
    elif ("last order" in query.lower() or "recent order" in query.lower() or "my order" in query.lower()):
        logger.info(f"Session {user_session.session_id}: Asking for customer ID for 'last order' type query.")
        user_session.set_expected_input("customer_id_for_last_order")
        return {"response": "Sure, I can help with that! Could you please provide your Customer ID?"}
    else:
        logger.info(f"Session {user_session.session_id}: Customer ID needed for order query, asking user.")
        user_session.set_expected_input("customer_id_for_last_order")
        return {"response": "To look up order details, I'll need your 5-digit Customer ID, please."}

    if not current_customer_id:
         logger.error(f"Session {user_session.session_id}: Order processing reached without a customer ID.")
         return {"response": "I seem to have lost track of the Customer ID. Could you provide it again?"}

    logger.info(f"Session {user_session.session_id}: Calling order service for customer ID: {current_customer_id}")
    try:
        response = requests.get(
            f"{ORDER_SERVICE_URL}/orders/{current_customer_id}",
            timeout=10 
        )
        if response.status_code == 404:
            logger.info(f"Session {user_session.session_id}: No orders found for customer ID {current_customer_id} from service (404).")
            return {"response": f"I couldn't find any orders for customer ID {current_customer_id}."}
        
        response.raise_for_status()
        order_data = response.json()
        return {"response": chat_handler.generate_order_response(order_data, query)}
    except requests.exceptions.HTTPError as e:
        logger.error(f"Session {user_session.session_id}: HTTP error from order service for customer {current_customer_id}: {e}")
        return {"response": "I'm having trouble retrieving your order information right now due to a service error."}
    except requests.exceptions.Timeout:
        logger.error(f"Session {user_session.session_id}: Order service request timed out for customer {current_customer_id}")
        return {"response": "Our order service is currently busy. Please try again shortly."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Session {user_session.session_id}: Error calling order service for customer {current_customer_id}: {e}")
        return {"response": "I'm having trouble connecting to the order service right now."}
    except Exception as e:
        logger.error(f"Session {user_session.session_id}: Unexpected error in order query handler for customer {current_customer_id}: {e}", exc_info=True)
        return {"response": "I'm sorry, I encountered an error while retrieving your order information."}

def process_priority_order_request(priority_level: str, user_session: Session):
    """Processes priority order requests."""
    logger.info(f"Session {user_session.session_id}: Calling order service for {priority_level} priority orders.")
    try:
        response = requests.get(
            f"{ORDER_SERVICE_URL}/orders/priority/{priority_level}",
            timeout=10
        )
        response.raise_for_status()
        orders = response.json()
        return {"response": chat_handler.generate_priority_orders_response(orders, priority_level)}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
             logger.info(f"Session {user_session.session_id}: No {priority_level} priority orders found (404).")
             return {"response": f"I couldn't find any {priority_level.lower()} priority orders at the moment."}
        logger.error(f"Session {user_session.session_id}: HTTP error from order service (priority) for {priority_level}: {e}")
        return {"response": f"I'm having trouble retrieving {priority_level} priority orders due to a service error."}
    except requests.exceptions.Timeout:
        logger.error(f"Session {user_session.session_id}: Order service (priority) request timed out for {priority_level}")
        return {"response": f"Our order service is taking too long to respond for {priority_level} priority orders."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Session {user_session.session_id}: Error calling order service (priority) for {priority_level}: {e}")
        return {"response": f"I'm having trouble retrieving {priority_level} priority orders right now."}
    except Exception as e:
        logger.error(f"Session {user_session.session_id}: Unexpected error in priority order handler for {priority_level}: {e}", exc_info=True)
        return {"response": f"I'm sorry, I encountered an error retrieving {priority_level} priority orders."}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
