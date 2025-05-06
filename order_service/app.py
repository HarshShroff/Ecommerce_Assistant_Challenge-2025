from flask import Flask, jsonify, request
import pandas as pd
import logging
import re
import os
from mock_api_client import get_order_details

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    orders_df_global = pd.read_csv('../data/Order_Data_Dataset.csv', on_bad_lines='skip')
    logger.info(f"Loaded {len(orders_df_global)} orders from global dataset")
except Exception as e:
    logger.error(f"Error loading order dataset: {e}")
    orders_df_global = pd.DataFrame()

@app.route('/health', methods=['GET'])
def health_check():
    """Performs a health check."""
    return jsonify({"status": "healthy"})

@app.route('/orders/<customer_id>', methods=['GET'])
def get_orders(customer_id):
    """Retrieves orders for a given customer ID."""
    try:
        if not re.match(r'^\d+$', customer_id):
            return jsonify({"error": "Invalid customer ID format"}), 400
            
        customer_id_int = int(customer_id)
        logger.info(f"Retrieving orders for customer ID: {customer_id_int}")
        
        orders = get_order_details(customer_id_int)
        
        if orders.empty:
            return jsonify({"error": f"No orders found for customer ID {customer_id_int}"}), 404
            
        orders = orders.sort_values(by='Order_Date', ascending=False)
        
        return jsonify({
            'customer_id': customer_id_int,
            'orders': orders.to_dict(orient='records')
        })
    except Exception as e:
        logger.error(f"Error retrieving orders: {e}")
        return jsonify({"error": "Failed to retrieve order information"}), 500

@app.route('/orders/priority/<priority>', methods=['GET'])
def get_priority_orders(priority):
    """Retrieves orders for a given priority level."""
    valid_priorities = ['Low', 'Medium', 'High', 'Critical']
    if priority.capitalize() not in valid_priorities:
        return jsonify({'error': 'Invalid priority level'}), 400
        
    try:
        logger.info(f"Retrieving orders with priority: {priority}")
        filtered = orders_df_global[orders_df_global['Order_Priority'] == priority.capitalize()]
        
        filtered = filtered.sort_values(by='Order_Date', ascending=False)
        
        if filtered.empty:
            return jsonify({"message": "No orders found with this priority"}), 404
            
        return jsonify(filtered.head(5).to_dict(orient='records'))
    except Exception as e:
        logger.error(f"Error retrieving priority orders: {e}")
        return jsonify({"error": "Failed to retrieve priority orders"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
