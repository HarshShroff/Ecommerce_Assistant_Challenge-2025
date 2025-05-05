from flask import Flask, jsonify, request
import pandas as pd
import logging
import re
import os
from mock_api_client import get_order_details # Ensure this import is correct

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    orders_df_global = pd.read_csv('../data/Order_Data_Dataset.csv', on_bad_lines='skip')
    logger.info(f"Loaded {len(orders_df_global)} orders from global dataset")
except Exception as e:
    logger.error(f"FATAL: Error loading global order dataset in app.py: {e}")
    orders_df_global = pd.DataFrame() # Initialize empty DataFrame on error

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# CORRECTED ROUTE DEFINITION
@app.route('/orders/<customer_id>', methods=['GET'])
def get_orders(customer_id):
    try:
        # Validate customer ID format
        if not re.match(r'^\d+$', customer_id):
            logger.warning(f"Invalid customer ID format received: {customer_id}")
            return jsonify({"error": "Invalid customer ID format"}), 400

        customer_id_int = int(customer_id)
        logger.info(f"Retrieving orders for customer ID: {customer_id_int}")

        # Use the mock API client function to get order details
        orders = get_order_details(customer_id_int) # Pass integer ID

        # Explicitly check if the returned DataFrame is empty
        if orders.empty:
            logger.info(f"No orders found for customer ID: {customer_id_int}")
            # Return 404 if no orders found
            return jsonify({"error": f"No orders found for customer ID {customer_id_int}"}), 404

        # Sort by date (most recent first)
        orders = orders.sort_values(by='Order_Date', ascending=False)

        return jsonify({
            'customer_id': customer_id_int,
            'orders': orders.to_dict(orient='records')
        })
    except Exception as e:
        logger.error(f"Error retrieving orders for customer {customer_id}: {e}", exc_info=True) # Log traceback
        return jsonify({"error": "Failed to retrieve order information"}), 500

# CORRECTED ROUTE DEFINITION for priority
@app.route('/orders/priority/<priority>', methods=['GET'])
def get_priority_orders(priority):
    valid_priorities = ['Low', 'Medium', 'High', 'Critical']
    priority_capitalized = priority.capitalize() # Capitalize once

    if priority_capitalized not in valid_priorities:
        logger.warning(f"Invalid priority level requested: {priority}")
        return jsonify({'error': 'Invalid priority level'}), 400

    try:
        if orders_df_global.empty:
            logger.error("Global order DataFrame is empty, cannot filter by priority.")
            return jsonify({"error": "Order data not available"}), 500

        logger.info(f"Retrieving orders with priority: {priority_capitalized}")
        filtered = orders_df_global[orders_df_global['Order_Priority'] == priority_capitalized]

        # Sort by date (most recent first)
        filtered = filtered.sort_values(by='Order_Date', ascending=False)

        if filtered.empty:
            logger.info(f"No orders found with priority: {priority_capitalized}")
            # It's okay to return 200 with an empty list if no orders match the priority
            return jsonify([]) # Return empty list instead of 404

        return jsonify(filtered.head(5).to_dict(orient='records'))
    except Exception as e:
        logger.error(f"Error retrieving priority orders for {priority}: {e}", exc_info=True) # Log traceback
        return jsonify({"error": "Failed to retrieve priority orders"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
